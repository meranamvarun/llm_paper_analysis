from pathlib import Path
import copy,json
from extraction.recovery_run import read,sha
from extraction.source_content import clean_source_formatting
from extraction.quality import write_new_run
from extraction.automated_quality import structural_checks
run=Path('data/automated_quality/20261112/field_consensus_v1');rows=read(run/'questions.jsonl');result=copy.deepcopy(rows)
pagepath=Path('data/extraction/runs/20261110T043421397159Z/pages.jsonl');pages={p['pdf_page']:p for p in read(pagepath)};logs=[]
for q in result:
 updates=clean_source_formatting(q,pages)
 if updates:
  logs.append({'question_id':q['question_id'],'rule':'source_anchored_footer_removal_and_literal_number_spacing','before':{k:copy.deepcopy(q[k]) for k in updates},'after':updates,'status':'machine_proposal_unreviewed','source_evidence':q['evidence']});q.update(updates)
passages=read(run/'passages.jsonl');config=json.loads(Path('extraction/papers.json').read_text());findings=structural_checks(result,passages,config);assert not findings
out=Path('data/automated_quality/20261112/source_formatting_v2')
inputs=[run/'questions.jsonl',run/'manifest.json',pagepath,Path('extraction/source_content.py'),Path(__file__)]
write_new_run(out,{'questions.jsonl':result,'passages.jsonl':passages,'repairs.jsonl':logs,'structural_findings.jsonl':findings,'abstentions.jsonl':[],'summary.json':{'changed_records':len(logs),'structural_findings':0,'gate':'FRESH_TEXT_RECHECK_REQUIRED'},'manifest.json':{'inputs':{str(p):sha(p) for p in inputs}}})
m=json.loads((out/'manifest.json').read_text());m['outputs']={p.name:sha(p) for p in out.iterdir() if p.name!='manifest.json'};(out/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8');print('Formatting repairs',len(logs))
