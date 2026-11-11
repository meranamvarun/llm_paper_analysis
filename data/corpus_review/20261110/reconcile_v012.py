import json,hashlib
from pathlib import Path
r=Path('data/corpus_review/20261110'); frozen=r/'reparse_v0.1.1_corrected'; new=r/'reparse_v0.1.2_corrected'; accepted=r/'accepted_derived_v1';out=r/'reconciled_v0.1.2';out.mkdir(exist_ok=False)
read=lambda p:[json.loads(l) for l in p.read_text(encoding='utf8').splitlines()]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inputs=[p for d in [frozen,new,accepted] for p in d.iterdir() if p.is_file()]+[Path('question_paper (1).pdf')]
hashes={str(p):sha(p) for p in inputs}
old=read(frozen/'questions.jsonl');qs=read(new/'questions.jsonl');ps=read(new/'passages.jsonl');acc=read(accepted/'questions.jsonl')
overrides={q['question_id']:q for q in acc if 'accepted_correction' in q};assert len(overrides)==6
assert overrides.keys() <= {q['question_id'] for q in qs}
logs=[]
for i,q in enumerate(qs):
 if q['question_id'] in overrides:
  logs.append({'kind':'accepted_record_retained_verbatim','parser_proposal':q,'retained':overrides[q['question_id']]});qs[i]=overrides[q['question_id']]
# Compare full semantic changes, retaining snapshots, not just a count.
newmap={q['question_id']:q for q in qs};oldmap={q['question_id']:q for q in old}
strip=lambda q:{k:v for k,v in q.items() if k!='parser_version'}
for key in oldmap.keys()|newmap.keys():
 a=oldmap.get(key);b=newmap.get(key)
 if a is None or b is None or strip(a)!=strip(b):logs.append({'kind':'record_reconciliation','before':a,'after':b,'status':'ai_proposal_except_explicit_accepted_scope'})
dispositions=[]
for key in oldmap.keys()-newmap.keys():
 a=oldmap[key];anchors={(e['pdf_page'],e['line_id']) for e in a['evidence']}
 targets=[]
 for b in qs+ps:
  ev={(e['pdf_page'],e['line_id']) for e in b['evidence']}
  if anchors <= ev:targets.append(b.get('question_id',b.get('passage_id')))
 dispositions.append({'old_id':key,'before':a,'proposed_target_ids':targets,'status':'ai_merge_proposal_pending_human_review' if targets else 'unresolved_disposition'})
assert all(d['proposed_target_ids'] for d in dispositions)
config=json.loads(Path('extraction/papers.json').read_text());diagnostics=[]
for paper in config['papers']:
 g=[q for q in qs if q['paper_id']==paper['paper_id'] and q['format']=='mcq'];seen={}
 for q in g:seen.setdefault((q['section_id'],q['printed_question_number']),[]).append(q['question_id'])
 expected=paper.get('expected_mcqs');numbers={int(q['printed_question_number']) for q in g}
 diagnostics.append({'paper_id':paper['paper_id'],'year_label':paper['year_label'],'mcq_proposals':len(g),'expected_mcqs':expected,'missing_numbers':sorted(set(range(1,expected+1))-numbers) if expected else None,'out_of_range_numbers':sorted(numbers-set(range(1,expected+1))) if expected else None,'duplicate_groups':[v for v in seen.values() if len(v)>1],'option_anomaly_ids':[q['question_id'] for q in g if [o['label'] for o in q['options']]!=list('ABCD')],'missing_passage_ids':[q['question_id'] for q in g if paper.get('passage_format') and not q['passage_id']],'status':'unreviewed_current_derived_diagnostics'})
for name,rows in [('questions',qs),('passages',ps),('reconciliation',logs),('id_dispositions',dispositions),('id_aliases',read(accepted/'id_aliases.jsonl')),('unresolved_blocks',read(new/'unresolved_blocks.jsonl'))]:
 (out/(name+'.jsonl')).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf8')
(out/'diagnostics.json').write_text(json.dumps(diagnostics,indent=2),encoding='utf8')
assert all(newmap[k]==v for k,v in overrides.items());assert len(newmap)==len(qs)
assert all(q['review_status']=='unreviewed' for q in qs)
assert all(q['passage_id'] is None or q['passage_id'] in {p['passage_id'] for p in ps} for q in qs)
assert all(sha(Path(p))==v for p,v in hashes.items())
summary={'total_proposals':len(qs),'in_scope_proposals':sum(2016<=q['year_label']<=2026 for q in qs),'accepted_records_preserved_verbatim':6,'removed_ids_since_v011':len(dispositions),'reconciliation_entries':len(logs),'frozen_inputs_unchanged':True,'passage_references_resolve':True,'independent_human_validation':False}
(out/'verification.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
(out/'manifest.json').write_text(json.dumps({'inputs':hashes,'outputs':{p.name:sha(p) for p in out.iterdir()},'script_sha256':sha(Path(__file__)),'parser_sha256':sha(Path('extraction/pipeline.py'))},indent=2),encoding='utf8')
print(json.dumps(summary));print('Dispositions:',[(d['old_id'].split(':')[1:3],d['proposed_target_ids'][0].split(':')[1:3]) for d in dispositions])
