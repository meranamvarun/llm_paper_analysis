"""Source-boundary recovery helpers. All outputs are unreviewed proposals."""
import copy
from difflib import SequenceMatcher
import re

MARKER = r'(\(\s*[A-Da-d]\s*\)|[A-Da-d][.)])'
LETTER_HEAD = re.compile(r'(?m)^[ \t]*'+MARKER+r'[ \t]+')

class SourceSpan:
    def __init__(self,a,b,label):self.a,self.b,self.label=a,b,label
    def start(self):return self.a
    def end(self):return self.b
    def __getitem__(self,key):return self.label

def flat(text): return ' '.join(text.split())
def label(match):return re.search('[A-Da-d]',match[1]).group().upper()

def letter_parts(text, allow_bare=False):
    text=re.split(r'(?mi)^CORRECT\s+(?:OPTION|ANSWER)\b',text)[0]
    head=re.compile(r'(?m)^[ \t]*(\(\s*[A-Da-d]\s*\)|[A-Da-d][.)]|[A-D])[ \t]+') if allow_bare else LETTER_HEAD
    matches=list(head.finditer(text));labels=[label(m) for m in matches]
    starts=[i for i in range(len(matches)) if labels[i:]==list('ABCD')]
    if len(starts)==1:chosen=matches[starts[0]:]
    else:
        starts=[i for i in range(len(matches)) if labels[i:] in [list('AC'),list('A')]]
        if len(starts)!=1:return None
        chosen=[];heads=matches[starts[0]:]
        for first in heads:
            end=text.find('\n',first.end())
            if end<0:end=len(text)
            inline=list(re.finditer(r'(?<!\S)'+MARKER+r'\s+',text[first.end():end]))
            expected=list('BCD') if len(heads)==1 else ['B' if label(first)=='A' else 'D']
            if [label(m) for m in inline]!=expected:return None
            chosen.append(first)
            chosen.extend(SourceSpan(first.end()+m.start(),first.end()+m.end(),m[1]) for m in inline)
    options=[{'label':l,'raw_label':m[1],'text':text[m.end():chosen[i+1].start() if i<3 else len(text)].strip()} for i,(l,m) in enumerate(zip('ABCD',chosen))]
    if len(options)!=4 or any(not o['text'] for o in options):return None
    return text[:chosen[0].start()].strip(),options

def transfer_cleaning(stem,options,q):
    """Carry unique prior field edits; abstain when an edit cannot be located."""
    segments=[flat(stem)]+[flat(o['text']) for o in options]
    old=[q.get('original_stem',q['stem'])]+[o['text'] for o in q.get('original_options',q['options'])]
    cleaned=[q['stem']]+[o['text'] for o in q['options']]
    if len(old)!=len(cleaned):
        # Boundary repairs do not change lexical content; compare a joined stream.
        old=[flat(' '.join(old))];cleaned=[flat(' '.join(cleaned))]
    changes=[]
    for before,after in zip(old,cleaned):
        before,after=flat(before),flat(after)
        if before==after: continue
        if segments.count(before)==1:
            n=segments.index(before);segments[n]=after;changes.append({'before':before,'after':after});continue
        if segments.count(after)==1:
            changes.append({'before':before,'after':after,'already_satisfied':True});continue
        edits=[op for op in SequenceMatcher(None,before,after,autojunk=False).get_opcodes() if op[0]!='equal']
        i,j=edits[0][1],edits[-1][2]
        k,l=edits[0][3],edits[-1][4]
        applied=False
        scores=sorted([(SequenceMatcher(None,before,value,autojunk=False).ratio(),n) for n,value in enumerate(segments)],reverse=True)
        narrowed=[scores[0][1]] if scores[0][0]>.5 and (len(scores)<2 or scores[0][0]-scores[1][0]>.1) else list(range(len(segments)))
        for context in [16,8,4,0]:
            a=max(0,i-context);b=min(len(before),j+context)
            needle=before[a:b];replacement=before[a:i]+after[k:l]+before[j:b]
            hits=[(n,segments[n].count(needle)) for n in narrowed]
            if needle and sum(count for _,count in hits)==1:
                n=next(n for n,count in hits if count)
                segments[n]=segments[n].replace(needle,replacement,1)
                changes.append({'before':needle,'after':replacement});applied=True;break
            # Source header filtering may already have performed this deletion.
            if replacement and sum(segments[n].count(replacement) for n in narrowed)==1 and after[k:l]=='':
                changes.append({'before':needle,'after':replacement,'already_satisfied':True});applied=True;break
        if not applied:return None
    result=copy.deepcopy(options)
    for o,value in zip(result,segments[1:]):o['text']=value
    return segments[0],result,changes

def metadata_options(lines, number):
    starts=[]
    for i,line in enumerate(lines):
        m=re.match(r'^Question Number\s*:\s*(\d+)\b',line['text'],re.I)
        if m:starts.append((i,int(m[1])))
    spans=[]
    for i,(a,n) in enumerate(starts):
        if n!=int(number):continue
        b=starts[i+1][0] if i+1<len(starts) else len(lines)
        text='\n'.join(l['text'] for l in lines[a:b])
        heading=re.search(r'(?mi)^Options\s*:\s*$',text)
        if not heading:continue
        body=text[heading.end():]
        markers=list(re.finditer(r'(?m)^([1-4])[.)]\s+',body))
        if [m[1] for m in markers]!=list('1234'):continue
        options=[]
        for j,m in enumerate(markers):
            value=body[m.end():markers[j+1].start() if j<3 else len(body)].strip()
            # Visible correctness icons are metadata, not part of an answer.
            value=re.sub(r'^[*\u00ae\u00a5\u2713\u2714\u2717\u2718\u00d7\u221a ]+','',value)
            options.append({'label':'ABCD'[j],'raw_label':m.group().strip(),'text':value})
        spans.append((options,lines[a:b]))
    return spans


def answer_delimited_blocks(lines, expected):
    starts=[]
    next_number=1
    # Numbers are read literally. The expected sequence selects candidates,
    # but supplies no missing number or text when the source is incomplete.
    for i,line in enumerate(lines):
        match=re.match(r'^([0-9]+)[.)]\s*',line['text'])
        if match and int(match[1])==next_number:
            starts.append(i);next_number+=1
    if len(starts)!=expected:return None
    blocks=[]
    previous_end=0
    for i,start in enumerate(starts):
        stop=starts[i+1] if i+1<len(starts) else len(lines)
        ends=[j for j in range(start,stop) if re.match(r'^CORRECT\s+(?:OPTION|ANSWER)\b',lines[j]['text'],re.I)]
        if len(ends)!=1:return None
        end=ends[0]+1
        blocks.append({'number':i+1,'lines':lines[start:end],'preceding_passage':lines[previous_end:start]})
        previous_end=end
    return blocks


def numbered_source_blocks(lines, expected, blocks=1):
    selected=[];number=1;group=0;margin=None
    for i,line in enumerate(lines):
        m=re.match(r'^((?:\d\s*){1,3})(?:[.)]\s*|\s+(?=[A-Za-z]))',line['text'])
        if not m:continue
        n=int(re.sub(r'\s','',m[1]))
        if margin is not None and line['bbox'][0]>margin+15:continue
        if n==1 and number==expected+1 and group<blocks-1:
            group+=1;number=1;margin=None
        if n!=number:continue
        if margin is None:margin=line['bbox'][0]
        selected.append({'number':n,'start':i,'block':group});number+=1
    if len(selected)!=expected*blocks:return None
    for i,item in enumerate(selected):item['stop']=selected[i+1]['start'] if i+1<len(selected) else len(lines)
    return selected


def numeric_parts(text):
    heading=re.search(r'(?mi)^(?:Options\s*:|Ans\b[^\n]*)',text)
    if not heading:return None
    body=text[heading.end():]
    body=re.split(r'(?mi)^(?:Question (?:Number|Id|Label)|Linked Answer Question|Direction:|Sub Question No|Page [0-9])',body)[0]
    matches=list(re.finditer(r'(?m)^([1-4])(?:[.,)%]\s*|\s+)',body))
    if [m[1] for m in matches]!=list('1234'):return None
    options=[]
    for i,m in enumerate(matches):
        value=body[m.end():matches[i+1].start() if i<3 else len(body)].strip()
        value=re.sub(r'^[*\u00ae\u00a5\u2713\u2714\u2717\u2718\u00d7\u221a ]+','',value)
        if not value:return None
        options.append({'label':'ABCD'[i],'raw_label':m.group().strip(),'text':value})
    return options
