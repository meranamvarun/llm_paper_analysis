from pathlib import Path
import copy,json,collections
from extraction.recovery_run import read,sha
from extraction.field_consensus import consensus
from extraction.automated_quality import tokens,structural_checks
from extraction.quality import write_new_run
run=Path('data/automated_quality/20261112/source_formatting_v2');fieldrun=Path('data/automated_quality/20261112/embedded_fields_v2');rows=read(run/'questions.jsonl');result=copy.deepcopy(rows);fields=read(fieldrun/'fields.jsonl');byid={q['question_id']:q for q in result};logs=[];disagreements=[]
protected={r['question_id'] for r in read(Path('data/automated_quality/20261112/structural_zero_v2/repairs.jsonl'))}
for f in fields:
 q=byid[f['question_id']];readings=f['readings']
 if len(readings)<2 or any(r['returncode'] for r in readings):raise ValueError('Field OCR incomplete')
 ordered=sorted(readings,key=lambda r:r['psm']);groups=collections.defaultdict(list)
 for reading in ordered:
  groups[tuple(tokens(reading['text']))].append(reading)
 candidates=[v for k,v in groups.items() if k and len(v)>=2]
 value=max(candidates,key=lambda g:len(g))[0]['text'] if candidates else None
 if value is None or '\ufffd' in value:
  disagreements.append({'question_id':q['question_id'],'field':f['field'],'readings':readings,'source_image':f['raw_image']});continue
 value=' '.join(value.split())
 field=f['field'];before=q['stem'] if field=='stem' else q['options']['ABCD'.index(field[-1])]['text']
 if tokens(before)==tokens(value):continue
 if field!='stem' and q['question_id'] in protected:
  disagreements.append({'question_id':q['question_id'],'field':field,'reason':'prior_source_image_reading_retained','readings':readings,'source_image':f['raw_image']});continue
 logs.append({'question_id':q['question_id'],'field':field,'before':before,'after':value,'rule':'nonempty_two_layout_source_field_lexical_consensus','source_image':f['raw_image'],'source_image_sha256':sha(f['raw_image']),'source_pdf_page':f['source_pdf_page'],'source_image_name':f['source_image_name'],'source_bbox':f['bbox'],'readings':readings,'status':'machine_source_image_proposal_unreviewed'})
 if field=='stem':q['stem']=value
 else:q['options']['ABCD'.index(field[-1])]['text']=value
config=json.loads(Path('extraction/papers.json').read_text());passages=read(run/'passages.jsonl');findings=structural_checks(result,passages,config);assert not findings
out=Path('data/automated_quality/20261112/field_consensus_v2');inputs=[run/'questions.jsonl',run/'manifest.json',fieldrun/'fields.jsonl',fieldrun/'manifest.json',Path(__file__),Path('extraction/field_consensus.py')]
write_new_run(out,{'questions.jsonl':result,'passages.jsonl':passages,'repairs.jsonl':logs,'field_reading_disagreements.jsonl':disagreements,'structural_findings.jsonl':findings,'abstentions.jsonl':[],'summary.json':{'field_repairs':len(logs),'changed_questions':len({l['question_id'] for l in logs}),'field_reading_disagreements':len(disagreements),'gate':'FRESH_CORPUS_RECHECK_REQUIRED'},'manifest.json':{'inputs':{str(p):sha(p) for p in inputs}}})
m=json.loads((out/'manifest.json').read_text());m['outputs']={p.name:sha(p) for p in out.iterdir() if p.name!='manifest.json'};(out/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8');print(json.dumps(json.loads((out/'summary.json').read_text()),indent=2))
