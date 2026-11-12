from pathlib import Path
import json,re,collections
from extraction.recovery_run import read,sha
from extraction.image_repairs import apply_proposals
from extraction.quality import write_new_run
from extraction.automated_quality import structural_checks,compare_text,question_text,region_text

run=Path('data/automated_quality/20261112/boundary_recovery_v4');folder=Path('data/automated_quality/20261112/metadata_frames_v1')
rows=read(run/'questions.jsonl')
texts={
(2016,25):['1972','1966','1979','1976'],
(2016,31):['2010','2012','2013','2006'],
(2017,8):['No person shall be prosecuted for the same offence more than once','No person shall be prosecuted and punished for the same offence more than once','No person shall be punished for the same offence more than once','No person shall be prosecuted or punished for different offence again.'],
(2017,13):['Articles 124, 124-A to C, 127, 128, 217, 222, 224, 224-A, 231 (as amended / inserted)','Articles 124, 124-A to C (as amended / inserted)','Articles 124, 124-A to C, 217, 213 (as amended / inserted)','Articles 124, 124-A to C, 217, 222, 224, 224-A, 231 (as amended / inserted)'],
(2017,17):['Article 5','Article 9','Article 10','Article 11'],
(2017,18):['Bachpan Bachao Andolan v. Union of India, (2017 SC)','M.C. Mehta v. Union of India, (2017 SC)','Sheela Barse v. Union of India, (1987 SC)','Bandhua Mukti Morcha v. Union of India, (1984 SC)'],
(2017,24):['Australian Constitution','UK Constitution','US Constitution','Constitution of Ireland'],
(2017,36):['Council of States','House of People','Council of States and agreed to by the House of People','both the Houses of Parliament and agreed to by the majority of State Legislatures'],
(2017,38):['Not more than 250','Not more than 245','Not more than 238','Not more than 228'],
(2017,39):['20','25','30','35'],
(2017,43):['Article 141','Article 143','article 145','article 147'],
(2017,44):['166','167','168','169'],
(2017,54):['Friedman','Stone','Austin','Hart'],
(2017,62):['Historical school','Analytical school','Sociological school','Natural Law school'],
(2017,85):['Which is in contravention of some moral injunction, if accomplished in fact, should be considered valid.','Which is in contravention of some legal injunction, if accomplished in fact, should be considered valid.','Which in contravention of precedents','An act done in contravention of Law'],
(2017,89):['Gettell','Austin','Holland','Salmond'],
(2017,94):['Machiavelli','Bodin','Hobbes','Bentham'],
(2017,99):['Keeton','Salmond','Duguit','Allen'],
(2017,102):['Section 304','Section 304-A','Section 304-B','Section 305'],
(2017,103):['P. Rathinam v. Union of India','Bachan Singh v. Union of India','Gian Kaur v. State of Punjab','Ansari v. Union of India'],
(2017,110):['Section 431','Section 431-A','Section 433','Section 433-A'],
(2017,115):['coercion','undue influence','fraud','misrepresentation'],
(2017,117):['void','voidable','valid','both void and voidable'],
(2017,121):['C is not bound to repay the amount to A or B.','C is bound to repay the amount to A.','C is bound to repay the amount to both A and B.','C is bound to repay the amount to B.'],
(2017,122):['either A or B or C to pay him 3,000 rupees.','either A or B to pay him 3,000 rupees.','either B or C to pay him 3,000 rupees.','all to pay him 3,000 rupees simultaneously.'],
(2017,123):['5','15','17','18'],
(2017,126):['Kamal Nath Committee','M.C. Mehta Committee','Khanna Committee','Tiwari Committee'],
(2017,130):['Converting a public park into a nursing home','Reservation of seats in medical colleges','Throwing the hospital waste into the river','Medical negligence in the hospital'],
(2017,146):['1945','1946','2005','2006'],
(2017,147):['Brogan v. United Kingdom','Lengens v. Austria','Ireland v. United Kingdom','Lawless v. Ireland'],
(2017,149):['34 member States','44 member States','54 member States','60 member States'],
}
frames=read(folder/'frames.jsonl');proposals=[]
for q in rows:
 key=(q['year_label'],int(q['printed_question_number']))
 if key not in texts:continue
 matches=[f for f in frames if f['question_id']==q['question_id']]
 if not matches:continue
 imagepaths=[];evidence=[]
 for f in matches:
  candidates=[]
  for p in folder.glob('q*-psm6.json'):
   if '.ocr-' in p.name:continue
   d=json.loads(p.read_text(encoding='utf-8'))
   if d['question_id']==q['question_id'] and d['pdf_page']==f['pdf_page']:
    imagepaths.append(str(p.with_name(re.sub(r'-psm6\.json$','.png',p.name))));break
  evidence.append({'pdf_page':f['pdf_page'],'line_id':f"source-frame:q{key[1]}:p{f['pdf_page']}",'bbox':[0,f['crop_top'],595,f['crop_bottom']]})
 options=[{'label':label,'raw_label':str(i+1)+'.','text':value} for i,(label,value) in enumerate(zip('ABCD',texts[key]))]
 updates={'options':options,'pdf_pages':sorted({f['pdf_page'] for f in matches}),'evidence':evidence}
 proposals.append({'question_id':q['question_id'],'before':{k:q[k] for k in updates},'after':updates,'image_paths':imagepaths,'image_sha256':{p:sha(p) for p in imagepaths},'reviewer_type':'assistant_source_image_reading','status':'assistant_image_proposal_unreviewed','model_version':'runtime identifier not exposed','run_date':'2026-11-12','prompt':'Transcribe the four printed answer options literally from the source images; retain source typos and option order; exclude correctness icons; do not infer an answer.','settings':'interactive runtime settings not exposed','independent_human_validation':False})
assert len(proposals)==31
result,logs=apply_proposals(rows,proposals)
config=json.loads(Path('extraction/papers.json').read_text());passages=read(run/'passages.jsonl');findings=structural_checks(result,passages,config)
summary={'questions':len(result),'source_image_option_repairs':len(logs),'structural_findings':dict(collections.Counter(f['kind'] for f in findings)),'structural_gate':'PASS' if not findings else 'NEEDS_REPAIR','overall_gate':'TEXT_RECHECK_REQUIRED','independent_human_validation':False}
out=Path('data/automated_quality/20261112/structural_zero_v2')
changed={p['question_id'] for p in proposals};ocrpages={};comp=[];used=[]
oldcomp={c['question_id']:c for c in read(run/'comparisons.jsonl')}
for q in result:
 c=oldcomp[q['question_id']]
 if q['question_id'] in changed:
  for n in q['pdf_pages']:
   if n not in ocrpages:
    p=Path(f'data/automated_quality/20261111/run_v1/page_ocr/p{n:04d}.json');used.append(p);ocrpages[n]=json.loads(p.read_text(encoding='utf-8'))
  check=compare_text(question_text(q),region_text(q,ocrpages));c={'question_id':q['question_id'],'year_label':q['year_label'],'pdf_pages':q['pdf_pages'],'initial':check,'final':check,'second_pass':None,'repair_recheck':'fresh_target_comparison_after_image_option_proposal'}
 comp.append(c)
write_new_run(out,{'questions.jsonl':result,'passages.jsonl':passages,'repairs.jsonl':logs,'original_records.jsonl':rows,'structural_findings.jsonl':findings,'abstentions.jsonl':[],'comparisons.jsonl':comp,'summary.json':summary,'manifest.json':{'inputs':{str(p):sha(p) for p in [run/'questions.jsonl',run/'passages.jsonl',run/'manifest.json',folder/'manifest.json',Path(__file__),Path('extraction/image_repairs.py')]+[Path(p) for l in logs for p in l['image_paths']]+used}}})
m=json.loads((out/'manifest.json').read_text());m['outputs']={p.name:sha(p) for p in out.iterdir() if p.name!='manifest.json'};(out/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
print(json.dumps(summary,indent=2))
