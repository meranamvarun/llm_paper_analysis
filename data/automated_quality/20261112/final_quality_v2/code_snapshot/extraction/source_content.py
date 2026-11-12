"""Exclude explicit export boilerplate, retaining source strings separately."""
import re
import copy

META=re.compile(r'^(?:(?:Single )?Line Question Option\s*:|Question (?:Number|Id|Label|Numbers|Type)\s*:|Sub Question No\s*:|Correct\s*:\s*[0-9]|Options\s*:|Ans\b|Linked Answer Question\s*:|Direction\s*:|Sub questions\b|Questions\s*:\s*No\b)',re.I)

def strip_export_metadata(text):
    return '\n'.join(line for line in text.splitlines() if not META.match(line.strip())).strip()


def clean_source_formatting(question,pages):
    updates={};stem=question['stem']
    match=re.match(r'^((?:[0-9]\s+){1,2}[0-9])([.)])',stem)
    if match and re.sub(r'\s','',match[1])==question['printed_question_number']:
        stem=re.sub(r'\s','',match[1])+stem[match.end(1):]
    fields=[stem]+[o['text'] for o in question['options']]
    footers=[]
    for e in question['evidence']:
        page=pages[e['pdf_page']]
        line=next((l for l in page['lines'] if l['line_id']==e['line_id']),None)
        if not line:continue
        header=line['bbox'][1]<125
        if not header and line['bbox'][1]<page['height']*.88:continue
        text=' '.join(line['text'].split())
        residue=re.sub(r'PG|rho|[0-9]+|\u03c1|af|[MAB*#]|\s+','',text,flags=re.I)
        if header:
            if re.fullmatch(r'(?:af|ae|an|a|b|os|ys|PG|M)(?:\s+(?:af|ae|an|a|b|os|ys|PG|M))*',text,re.I) and (line['bbox'][0]<80 or 'PG' in text):
                footers.append(text)
            continue
        if residue:continue
        if 'PG' not in text and not re.search(r'[\u03c1*#MAB]|af|rho',text,re.I) and line['bbox'][0]<page['width']*.35:continue
        footers.append(text)
    for footer in reversed(footers):
        for i,value in enumerate(fields):
            normalized=' '.join(value.split())
            if normalized.endswith(' '+footer):fields[i]=normalized[:-len(footer)].strip()
            elif len(footer.split())>1 and normalized.count(' '+footer+' ')==1:fields[i]=normalized.replace(' '+footer+' ',' ',1)
    if fields[0]!=question['stem']:updates['stem']=fields[0]
    opts=copy.deepcopy(question['options'])
    for o,value in zip(opts,fields[1:]):o['text']=value
    if opts!=question['options']:updates['options']=opts
    return updates
