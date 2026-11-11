import sys,json,collections,hashlib,functools,importlib.metadata
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from wordfreq import zipf_frequency
from extraction.quality import clean_records,write_new_run,scan_text,normalize_text
r=Path('data/text_quality/20261111');src=Path('data/corpus_review/20261110/reconciled_v0.1.2')
read=lambda p:[json.loads(l) for l in p.read_text(encoding='utf8').splitlines()]
known=functools.lru_cache(None)(lambda s:zipf_frequency(s,'en',wordlist='large')>0)
qs,changes,flags=clean_records(read(src/'questions.jsonl'),known)
for i,f in enumerate(flags):f['flag_id']=f'flag-{i+1:05d}'
passages=read(src/'passages.jsonl');scope_papers={q['paper_id'] for q in qs if 'text_proposal' in q};pflags=[]
for p in passages:
 if p['paper_id'] not in scope_papers:continue
 text,_=normalize_text(p['raw_text'])
 for f in scan_text(text,known):pflags.append({**f,'record_id':p['passage_id'],'field':'raw_text','pdf_pages':sorted({e['pdf_page'] for e in p['evidence']}),'context':text[max(0,f['start']-65):f['end']+65]})
summary={'in_scope_questions_scanned':sum('text_proposal' in q for q in qs),'total_records_preserved':len(qs),'fields_with_formatting_changes':len(changes),'flags':len(flags),'flagged_questions':len({f['record_id'] for f in flags}),'flags_by_reason':dict(collections.Counter(f['reason'] for f in flags)),'unique_oov_tokens':len({f['text'].lower() for f in flags if f['reason']=='out_of_lexicon'}),'pages_in_flagged_questions':len({p for f in flags for p in f['pdf_pages']}),'passage_flags':len(pflags),'lexicon':'wordfreq 3.1.1 English large; zipf > 0','accuracy_status':'NOT_ESTABLISHED'}
write_new_run(r/'screening',{'questions.jsonl':qs,'changes.jsonl':changes,'flags.jsonl':flags,'passage_flags.jsonl':pflags,'summary.json':summary})
(r/'screening'/'manifest.json').write_text(json.dumps({'inputs':{str(src/n):hashlib.sha256((src/n).read_bytes()).hexdigest() for n in ['questions.jsonl','passages.jsonl']},'code_sha256':hashlib.sha256(Path('extraction/quality.py').read_bytes()).hexdigest(),'packages':{n:importlib.metadata.version(n) for n in ['wordfreq','ftfy','regex']},'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (r/'screening').iterdir()}},indent=2))
print(json.dumps(summary,indent=2))
print('OOV examples:',ascii(collections.Counter(f['text'] for f in flags if f['reason']=='out_of_lexicon').most_common(60)))
