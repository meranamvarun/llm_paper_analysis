import sys,json,hashlib,collections,copy,functools,importlib.metadata
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from extraction.quality import apply_source_reviews,scan_text
from extraction.benchmark import score_reference
from wordfreq import zipf_frequency
import wordfreq
r=Path('data/text_quality/20261111');out=r/'cleaned_proposed_v2';out.mkdir(exist_ok=False)
read=lambda p:[json.loads(l) for l in p.read_text(encoding='utf-8-sig').splitlines() if l.strip()]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rows=read(r/'screening/questions.jsonl');flags=read(r/'screening/flags.jsonl')+read(r/'ascii_supplement/flags.jsonl')+read(r/'symbol_supplement/flags.jsonl');reviews=[];inputs={}
for root in [r,r/'ascii_supplement',r/'symbol_supplement']:
 for folder in sorted(root.glob('luna_*')):
  p=folder/'review.jsonl';inputs[str(p)]=sha(p)
  for d in read(p):
   d['review_ledger']=str(p);paths=[]
   mapping=json.loads((folder/'crop_mapping.json').read_text(encoding='utf8'))['mapping']
   entry=next(m for m in mapping if d['flag_id'] in m['flag_ids'])
   mapped_image=Path(entry['sheet_path'])
   if not mapped_image.exists():raise ValueError('Missing mapped evidence image')
   paths.append({'path':str(mapped_image),'sha256':sha(mapped_image)})
   d['original_claimed_image_paths']=d.get('image_paths',[])
   d['image_paths']=[str(mapped_image)]
   d['image_reference_basis']='parent-generated exact line crop mapping; model claims preserved separately'
   d['image_evidence']=paths
   reviews.append(d)
assert len(reviews)==len(flags)==1603
reviewmap={d['flag_id']:d for d in reviews};parent_overrides=read(r/'parent_qa/overrides.jsonl')
for override in parent_overrides:
 before=copy.deepcopy(reviewmap[override['flag_id']]);reviewmap[override['flag_id']]={**before,**override,'superseded_review':before}
reviews=list(reviewmap.values())
fullfields=read(r/'parent_qa/field_transcriptions.jsonl');covered={(t['record_id'],t['field']) for t in fullfields}
apply_flags=[f for f in flags if (f['record_id'],f['field']) not in covered]
apply_ids={f['flag_id'] for f in apply_flags};apply_reviews=[d for d in reviews if d['flag_id'] in apply_ids]
for i,t in enumerate(fullfields,1):
 q=next(q for q in rows if q['question_id']==t['record_id'])
 original=q['text_proposal']['stem'] if t['field']=='stem' else q['text_proposal']['options'][int(t['field'].split('[')[1].split(']')[0])]['text']
 assert original==t['before']
 flag={'flag_id':f'field-transcription-{i}','record_id':t['record_id'],'field':t['field'],'start':0,'end':len(original),'text':original,'year_label':q['year_label'],'pdf_pages':q['pdf_pages'],'reason':'source_field_retranscription'}
 image=Path(t['image_paths'][0]);assert image.exists()
 decision={'flag_id':flag['flag_id'],'disposition':'source_supported_change','replacement':t['after'],'source_checked':True,'image_paths':t['image_paths'],'image_evidence':[{'path':str(image),'sha256':sha(image)}],'rationale':t['rationale'],'uncertainties':t.get('uncertainties'),'actor_type':'luna_with_parent_ai_qa'}
 apply_flags.append(flag);apply_reviews.append(decision)
 for d in reviews:
  f=next(f for f in flags if f['flag_id']==d['flag_id'])
  if (f['record_id'],f['field'])==(t['record_id'],t['field']):d['application_status']='covered_by_full_field_retranscription'
cleaned,log=apply_source_reviews(rows,apply_flags,apply_reviews)

# Keep six user-accepted records and all original fields intact in canonical proposal view.
assert all({k:v for k,v in q.items() if k!='text_proposal'}=={k:v for k,v in b.items() if k!='text_proposal'} for q,b in zip(cleaned,rows))
assert all(q==b for q,b in zip(cleaned,rows) if not 2016<=q['year_label']<=2026)
actual=[l for l in log if l['before']!=l['after']]
changed_ids={l['record_id'] for l in actual};compact=[]
for q in cleaned:
 if 'text_proposal' not in q:continue
 p=q['text_proposal'];flat={k:v for k,v in q.items() if k!='text_proposal'}
 flat.update({'original_stem':q['stem'],'original_options':q['options'],'stem':p['stem'],'options':p['options'],'text_cleanup_version':'0.1.0','text_cleanup_status':'ai_proposal_pending_human_validation','text_changed':q['question_id'] in changed_ids})
 compact.append(flat)
known=functools.lru_cache(None)(lambda word:zipf_frequency(word,'en',wordlist='large')>0)
residual=[]
for q in compact:
 for field,text in [('stem',q['stem'])]+[(f'options[{i}].text',o['text']) for i,o in enumerate(q['options'])]:
  for f in scan_text(text,known):residual.append({**f,'record_id':q['question_id'],'field':field,'pdf_pages':q['pdf_pages'],'status':'residual_screen_not_automatically_error'})
by_reason=dict(collections.Counter(f['reason'] for f in flags));by_disposition=dict(collections.Counter(d['disposition'] for d in reviews))
summary={'date':'2026-11-11','requested_reviewer_model':'gpt-6-luna','runtime_model_snapshot':'unavailable','human_review_status':'unreviewed','in_scope_questions_scanned':len(compact),'source_records_preserved':len(cleaned),'reviewed_flag_occurrences':len(flags),'flagged_questions':len({f['record_id'] for f in flags}),'flags_by_reason':by_reason,'review_dispositions':by_disposition,'source_checked_by_luna_claimed':sum(bool(d.get('source_checked')) for d in reviews),'actual_span_changes':len(actual),'no_op_change_proposals':len(log)-len(actual),'questions_with_proposed_changes':len(changed_ids),'unresolved_flags':[d['flag_id'] for d in reviews if d['disposition']=='unresolved'],'parent_qa_rejections_or_uncertainties':len(parent_overrides),'whole_field_retranscriptions':len(fullfields),'source_wording_preserved_despite_dictionary_absence':True,'residual_screen_flags':len(residual),'residual_flags_by_reason':dict(collections.Counter(f['reason'] for f in residual)),'six_prior_acceptance_metadata_preserved':sum('accepted_correction' in q for q in cleaned)==6,'human_benchmark':{'sampled_pages':60,'strata':12,'population_body_pages':365,'human_reference_items':0,'cer':None,'wer':None,'gate':'NOT_ASSESSED','targets':{'cer_max':0.005,'wer_max':0.01,'question_precision_min':0.99,'question_recall_min':0.99,'option_accuracy_min':0.99,'critical_token_errors_max':0}},'accuracy_status':'NOT_ESTABLISHED'}
for name,data in [('questions.jsonl',cleaned),('cleaned_questions.jsonl',compact),('flags.jsonl',flags),('luna_reviews_with_parent_qa.jsonl',reviews),('changes.jsonl',log),('residual_flags.jsonl',residual),('field_transcriptions.jsonl',fullfields)]:
 (out/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in data),encoding='utf8')
(out/'quality_scorecard.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
(out/'benchmark_result.json').write_text(json.dumps(score_reference([],[]),indent=2),encoding='utf8')
for p in [r/'screening/questions.jsonl',r/'screening/flags.jsonl',r/'ascii_supplement/flags.jsonl',r/'parent_qa/overrides.jsonl',r/'parent_qa/field_transcriptions.jsonl',r/'symbol_supplement/flags.jsonl',Path('question_paper (1).pdf')]:inputs[str(p)]=sha(p)
lexicon=Path(wordfreq.__file__).parent/'data/large_en.msgpack.gz';inputs[str(lexicon)]=sha(lexicon)
manifest={'inputs':inputs,'outputs':{p.name:sha(p) for p in out.iterdir()},'code_hashes':{str(p):sha(p) for p in [Path(__file__),Path('extraction/quality.py'),Path('extraction/benchmark.py')]},'status':'AI_PROPOSALS_NOT_HUMAN_GOLD'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
print(json.dumps(summary,indent=2))
