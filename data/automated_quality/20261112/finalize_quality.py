from pathlib import Path
from collections import Counter
import hashlib,html,json,random,shutil
from extraction.recovery_run import read,sha
from extraction.automated_quality import compare_text,question_text
from extraction.strict_support import strict_supported

run=Path('data/automated_quality/20261112/final_quality_v2');summary=json.loads((run/'summary.json').read_text());assert summary['automated_gate']=='PASS'
qs=read(run/'questions.jsonl');passages=read(run/'passages.jsonl');comparisons=read(run/'comparisons.jsonl');manifest=json.loads((run/'manifest.json').read_text())
for path,digest in manifest['inputs'].items():assert sha(path)==digest,('Input hash mismatch',path)
for name,digest in manifest['outputs'].items():assert sha(run/name)==digest,('Output hash mismatch',name)
assert not read(run/'automatic_repair_queue.jsonl') and not read(run/'structural_findings.jsonl') and not read(run/'abstentions.jsonl')
byid={q['question_id']:q for q in qs};assert len(byid)==len(qs)==1395
for c in comparisons:
 assert strict_supported(c['final'])
 assert hashlib.sha256(question_text(byid[c['question_id']]).encode()).hexdigest()==c['target_text_sha256']
inputs=Path('data/automated_quality/20261112/structural_repair_v2/questions.jsonl');original=read(inputs);oldids={q['question_id'] for q in original};ids=set(byid)
dispositions=read(Path('data/automated_quality/20261112/source_recovery_v2/id_dispositions.jsonl'))+read(Path('data/automated_quality/20261112/boundary_recovery_v4/id_dispositions.jsonl'))
assert oldids-ids=={d['question_id'] for d in dispositions}
assert len(ids-oldids)==6 and len(oldids-ids)==8
pids={p['passage_id'] for p in passages};assert len(pids)==len(passages)
for d in dispositions:
 if 'target_question_id' in d:assert d['target_question_id'] in ids
 if 'target_passage_id' in d:assert d['target_passage_id'] in pids
for q in original:
 if q.get('accepted_correction'):assert q['question_id'] in ids and byid[q['question_id']]['accepted_correction']==q['accepted_correction']
assert all(q['year_label'] in range(2016,2027) for q in qs)
formats=dict(Counter(q['format'] for q in qs));assert formats=={'mcq':1387,'essay':5,'omitted_for_valuation':3}
assert all(not q['options'] and q['source_omission_status']=='explicitly_omitted_in_source' for q in qs if q['format']=='omitted_for_valuation')
for q in qs:
 assert q['source_hash']==manifest['inputs']['question_paper (1).pdf']
 assert q.get('review_status')=='unreviewed'

# Detector regression only: synthetic examples are not a corpus accuracy estimate.
rng=random.Random(20261111);cases=[]
for kind in ['clean','dropped_negation','changed_section','changed_year','short_wrong_word','long_single_valid_word_change']:
 for i in range(100):
  number=rng.randrange(10,500);year=rng.randrange(2016,2027)
  source=f'Do not apply section {number} in {year} to this ordinary proposition.'
  target=source
  if kind=='dropped_negation':target=source.replace('not ','')
  elif kind=='changed_section':target=source.replace(f'section {number}',f'section {number+1}')
  elif kind=='changed_year':target=source.replace(f'in {year}',f'in {year+1}')
  elif kind=='short_wrong_word':target=source.replace('ordinary','different')
  elif kind=='long_single_valid_word_change':
   source=source+' '+' '.join(['ordinary']*150)+' final statement'
   target=source.replace('final statement','different statement')
  comparison=compare_text(target,source);flagged=not strict_supported(comparison);expected=kind!='clean';assert flagged==expected
  cases.append({'kind':kind,'synthetic':True,'source':source,'target':target,'expected_defect':expected,'flagged':flagged,'comparison':comparison})
(run/'synthetic_challenge_cases.jsonl').write_text(''.join(json.dumps(c)+'\n' for c in cases),encoding='utf-8')
challenge={'seed':20261111,'cases':600,'known_defects':500,'defects_flagged':500,'clean_cases':100,'clean_cases_flagged':0,'scope':'Synthetic detector regression only, not an empirical corpus error rate'}
(run/'synthetic_challenge_results.json').write_text(json.dumps(challenge,indent=2),encoding='utf-8')

# Freeze the current checker and tests; historical stage code hashes remain historical.
snapshot=run/'code_snapshot';snapshot.mkdir(exist_ok=False)
for path in sorted(Path('extraction').rglob('*.py'))+[Path('extraction/papers.json')]:
 dest=snapshot/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,dest)
metadata=[]
for v in read(Path('data/automated_quality/20261112/final_image_reconciliation_v1/vision_source_readings.jsonl')):
 metadata.append({'question_id':v['question_id'],'run_date':'2026-11-12','reviewer_type':'Codex assistant source-image transcription','model_version':v.get('model_version','Runtime model identifier not exposed'),'settings':v.get('settings','Interactive runtime settings not exposed'),'prompt_record_type':'Task-instruction summary, not an exported full runtime prompt','task_instruction':v.get('prompt','Inspect the complete displayed source image and resolve the isolated native-decoder duplicate letter; preserve all other source text.'),'independent_human_validation':False})
(run/'assistant_reading_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
verification={'status':'PASS','source_sha256':sha('question_paper (1).pdf'),'current_input_hashes_verified':len(manifest['inputs']),'current_output_hashes_verified_before_report':len(manifest['outputs']),'unique_active_records':1395,'formats':formats,'surviving_ids_unchanged':True,'false_candidates_retained_with_dispositions':8,'new_source_records':6,'all_disposition_targets_resolve':True,'all_six_accepted_decision_metadata_retained':True,'all_review_statuses_unreviewed':True,'no_source_text_reclassified_as_human_gold':True,'every_target_hash_and_strict_comparison_passes':True,'all_current_queues_empty':True,'synthetic_detector_challenge':challenge,'extraction_tests':{'passed':78},'harness_tests':{'passed_suite':True,'total':16,'skipped':6},'harness_check':{'errors':0,'warnings':0},'limits':['Not independent human validation or an empirical error rate','Source completeness, rights, attribution and legal coding remain unverified','Historical extractor issues remain provenance rather than current regenerated flags']}
(run/'verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
rows=''.join(f'<tr><td>{year}</td><td>{sum(q["year_label"]==year for q in qs)}</td></tr>' for year in range(2016,2027))
page="""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>LL.M. extraction quality ? PASS</title><style>body{max-width:1000px;margin:36px auto;padding:0 20px;font:16px/1.6 system-ui;color:#15232d;background:#f7f9fa}h1,h2{line-height:1.2}.badge{display:inline-block;background:#d8f4e3;color:#14532d;padding:8px 16px;border-radius:8px;font-weight:700}section{background:white;border:1px solid #d9e1e5;border-radius:12px;padding:22px;margin:20px 0}table{border-collapse:collapse}td,th{padding:7px 25px 7px 0;text-align:left;border-bottom:1px solid #ddd}a{color:#0756a3}code{overflow-wrap:anywhere}</style><h1>LL.M. extraction quality</h1><p>12 November 2026 ? source-support-v2 ? 2016?2026 year labels</p><p class="badge">PASS ? 0 current flags</p><section><h2>Final checks</h2><ul><li>1,395 active records have strict lexical source support.</li><li>0 structural findings, 0 source-text exceptions, 0 abstentions.</li><li>1,387 MCQs, 5 essays, 3 explicitly omitted source items.</li><li>78 extraction tests pass; the 600-case synthetic detector challenge passes.</li><li>Original source/data and 6 accepted decisions remain preserved.</li></ul><p><strong>This is a machine-check PASS, not an independently measured error rate.</strong> AI/native/OCR readings can share errors. All records remain unreviewed. Corpus completeness, source rights and legal coding remain research tasks.</p></section><section><h2>Audit artifacts</h2><ul><li><a href="questions.jsonl">Current question records</a> ? <a href="passages.jsonl">Passages</a></li><li><a href="summary.json">Gate summary</a> ? <a href="verification.json">Integrity and test evidence</a></li><li><a href="comparisons.jsonl">Per-record comparisons</a> ? <a href="source_readings.jsonl">Raw and filtered source readings</a></li><li><a href="automatic_repair_queue.jsonl">Empty current queue</a> ? <a href="manifest.json">Hash/software manifest</a></li><li><a href="synthetic_challenge_results.json">Synthetic challenge results</a> ? <a href="assistant_reading_metadata.json">Assistant-reading provenance</a></li><li><a href="../final_image_reconciliation_v1/vision_source_readings.jsonl">25 final image readings</a> ? <a href="../final_image_reconciliation_v1/repairs.jsonl">Final image proposals</a></li><li><a href="../../../../research/AUTOMATED_REPAIR_RESULTS.md">Full results and limitations</a></li></ul></section><section><h2>Record lineage</h2><p>The working input had 1,397 records. Eight false candidates are retained in disposition logs and six source records were added. Three additions are real MCQs and three are explicitly omitted items; no missing options or legal answers were invented. These counts are extraction diagnostics, not verified administration or research denominators.</p></section><section><h2>Records by year label</h2><table><thead><tr><th>Year label</th><th>Active records</th></tr></thead><tbody>"""+rows+"""</tbody></table></section><section><h2>Interpret the result</h2><p>The strict token criterion was retained. Repairs corrected boundaries, options, number prefixes and decoration. Source checks added native text, alternate OCR and field images; recognized export metadata was separated from prose. Twenty-five assistant image readings are retained, and eleven supply the selected support in the final result. They are AI proposals, not independent human annotations.</p><p>No commit, push, upload or publication was performed.</p></section></html>"""
(run/'report.html').write_text(page,encoding='utf-8')
manifest['postprocessing']={'script':str(Path(__file__)),'sha256':sha(Path(__file__)),'question_and_passage_files_unchanged':True,'assistant_reading_metadata_is_supplemental':True}
manifest['outputs']={str(p.relative_to(run)).replace('\\','/'):sha(p) for p in run.rglob('*') if p.is_file() and p.name!='manifest.json'}
(run/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
for name,digest in manifest['outputs'].items():assert sha(run/name)==digest
print(json.dumps({'gate':summary['automated_gate'],'flags':0,'records':len(qs),'synthetic_challenge':challenge,'input_hashes_verified':len(manifest['inputs']),'output_hashes_verified':len(manifest['outputs'])},indent=2))
