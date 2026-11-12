from pathlib import Path
import copy,json
from extraction.recovery_run import read,sha,anchor,ev
from extraction.recovery import letter_parts,flat
from extraction.automated_quality import structural_checks
from extraction.quality import write_new_run
run=Path('data/automated_quality/20261112/field_consensus_v2');rows=read(run/'questions.jsonl');result=copy.deepcopy(rows);passages=read(run/'passages.jsonl');pagepath=Path('data/extraction/runs/20261110T043421397159Z/pages.jsonl');pages={p['pdf_page']:p for p in read(pagepath)};logs=[]
config=json.loads(Path('extraction/papers.json').read_text());paper=next(p for p in config['papers'] if p['year_label']==2022)
alllines=[{**l,'pdf_page':n} for lo,hi in paper['body_ranges'] for n in range(lo,hi+1) for l in pages[n]['lines']];order={anchor(l):i for i,l in enumerate(alllines)}
for number,label,n,lineid,nextnum in [(12,'III',195,'l0020',13),(42,'VIII',203,'l0015',43)]:
 q=next(q for q in result if q['year_label']==2022 and int(q['printed_question_number'])==number);following=next(q for q in result if q['year_label']==2022 and int(q['printed_question_number'])==nextnum)
 start=order[(n,lineid)];stop=order[anchor(following['evidence'][0])];body=alllines[start:stop];pid=f"{config['source_sha256']}:p{n:04d}:{lineid}:passage"
 image=Path(f'data/automated_quality/20261112/source_review/p{n:04d}.png')
 passages.append({'passage_id':pid,'paper_id':paper['paper_id'],'printed_label':label,'raw_text':'\n'.join(l['text'] for l in body),'evidence':ev(body),'review_status':'unreviewed','source_image_checked':str(image),'label_status':'assistant_image_proposal_unreviewed','boundary_rule':'explicit_printed_Roman_heading_before_next_literal_question_start'})
 before={k:copy.deepcopy(q[k]) for k in ['options','evidence','pdf_pages']}
 keep=[e for e in q['evidence'] if order.get(anchor(e),-1)<start];texts=[next(l['text'] for l in pages[e['pdf_page']]['lines'] if l['line_id']==e['line_id']) for e in keep];proposal=letter_parts('\n'.join(texts));assert proposal
 opts=copy.deepcopy(q['options']);opts[3]['text']=' '.join(proposal[1][3]['text'].split());q.update(options=opts,evidence=keep,pdf_pages=sorted({e['pdf_page'] for e in keep}))
 logs.append({'question_id':q['question_id'],'rule':'source_image_confirmed_passage_heading_split','before':before,'after':{k:q[k] for k in before},'new_passage_id':pid,'source_image':str(image),'source_image_sha256':sha(image),'status':'assistant_image_proposal_unreviewed'})
starts=sorted((order[anchor(p['evidence'][0])],p) for p in passages if p['paper_id']==paper['paper_id'] and anchor(p['evidence'][0]) in order)
for q in result:
 if q['year_label']!=2022:continue
 pos=order[anchor(q['evidence'][0])];prior=[p for i,p in starts if i<pos];pid=prior[-1]['passage_id'] if prior else None
 if q['passage_id']!=pid:
  logs.append({'question_id':q['question_id'],'rule':'latest_explicit_source_passage_before_question','before':{'passage_id':q['passage_id']},'after':{'passage_id':pid},'status':'machine_proposal_unreviewed'});q['passage_id']=pid
q=next(q for q in result if q['year_label']==2020 and q['printed_question_number']=='103');texts=[next(l['text'] for l in pages[e['pdf_page']]['lines'] if l['line_id']==e['line_id']) for e in q['evidence']];proposal=letter_parts('\n'.join(texts));assert proposal
stem=flat(proposal[0]);assert flat(q['stem']) in stem
logs.append({'question_id':q['question_id'],'rule':'source_image_confirmed_full_stem_recovery','before':{'stem':q['stem']},'after':{'stem':stem},'image_paths':['data/automated_quality/20261112/source_review/p0287.png','data/automated_quality/20261112/source_review/p0288.png'],'status':'assistant_image_proposal_unreviewed'});q['stem']=stem
findings=structural_checks(result,passages,config);assert not findings
out=Path('data/automated_quality/20261112/contextual_recovery_v1');inputs=[run/'questions.jsonl',run/'passages.jsonl',run/'manifest.json',pagepath,Path(__file__)]+[Path(f'data/automated_quality/20261112/source_review/p{n:04d}.png') for n in [195,203,287,288]]
write_new_run(out,{'questions.jsonl':result,'passages.jsonl':passages,'repairs.jsonl':logs,'structural_findings.jsonl':findings,'abstentions.jsonl':[],'summary.json':{'changes':len(logs),'new_source_passages':2,'restored_full_stems':1,'gate':'FRESH_TEXT_RECHECK_REQUIRED'},'manifest.json':{'inputs':{str(p):sha(p) for p in inputs}}})
m=json.loads((out/'manifest.json').read_text());m['outputs']={p.name:sha(p) for p in out.iterdir() if p.name!='manifest.json'};(out/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8');print('Contextual source repairs',len(logs))
