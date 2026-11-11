import json,hashlib,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from extraction.pipeline import parse_paper,VERSION
from extraction.run import body_page,validate
root=Path('data/corpus_review/20261110'); out=root/'reparse_v0.1.2_corrected';out.mkdir(exist_ok=False)
baseline=Path('data/extraction/runs/20261110T043421397159Z')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={p.name:sha(p) for p in baseline.iterdir() if p.is_file()}
config=json.loads((baseline/'papers.json').read_text());source=Path('question_paper (1).pdf'); assert sha(source)==config['source_sha256']
read=lambda name:[json.loads(s) for s in (baseline/name).read_text(encoding='utf8').splitlines()]
pages=read('pages.jsonl'); old=read('questions.jsonl'); qs=[];passages=[];unresolved=[]
for paper in config['papers']:
 selected=[x for p in pages if (x:=body_page(p,paper)) is not None]
 a,b,c=parse_paper(selected,paper,config['source_sha256'])
 if paper.get('passage_format'):
  for q in a:
   if q['format']=='mcq' and not q['passage_id']: q['issues'].append('passage_link_unresolved')
 qs+=a;passages+=b;unresolved+=c
validate(pages,qs,passages,read('answer_keys.jsonl'),config,config['source_sha256'])
for name,rows in [('questions',qs),('passages',passages),('unresolved_blocks',unresolved)]:
 (out/(name+'.jsonl')).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf8')
oldmap={q['question_id']:q for q in old};newmap={q['question_id']:q for q in qs}
changes=[]
for key in oldmap.keys()&newmap.keys():
 a={k:v for k,v in oldmap[key].items() if k!='parser_version'};b={k:v for k,v in newmap[key].items() if k!='parser_version'}
 if a!=b: changes.append({'question_id':key,'year_label':b['year_label'],'changed_fields':[k for k in a if a[k]!=b[k]]})
summary={'status':'unreviewed_reparse_of_frozen_page_evidence','baseline':str(baseline),'parser_version':VERSION,'source_sha256':sha(source),'parser_sha256':sha(Path('extraction/pipeline.py')),'baseline_file_hashes':before,'old_question_count':len(old),'new_question_count':len(qs),'added_ids':sorted(newmap.keys()-oldmap.keys()),'removed_ids':sorted(oldmap.keys()-newmap.keys()),'changed_records':changes,'in_scope_counts':{str(y):sum(q['year_label']==y for q in qs) for y in range(2016,2027)},'validation_passed':True,'ai_labels_promoted':False}
assert before=={p.name:sha(p) for p in baseline.iterdir() if p.is_file()}
(out/'comparison.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
(out/'artifact_hashes.json').write_text(json.dumps({p.name:sha(p) for p in out.iterdir() if p.is_file()},indent=2))
print(json.dumps({k:v for k,v in summary.items() if k not in ['baseline_file_hashes','changed_records']},indent=2));print('Changed existing records:',len(changes))
