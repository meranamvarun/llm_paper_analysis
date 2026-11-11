import json,hashlib,html,base64,io
from pathlib import Path
import pypdfium2 as pdfium
root=Path('data/corpus_review/20261110'); src=root/'reconciled_v0.1.2';out=root/'human_validation_v012';out.mkdir(exist_ok=False)
read=lambda p:[json.loads(x) for x in p.read_text(encoding='utf8').splitlines()]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
logs=read(src/'reconciliation.jsonl');disps={d['old_id']:d for d in read(src/'id_dispositions.jsonl')}
records={q.get('question_id',q.get('passage_id')):q for n in ['questions','passages'] for q in read(src/(n+'.jsonl'))}
items=[]
for log in logs:
 if log['kind']!='record_reconciliation':continue
 a,b=log['before'],log['after']; key=(a or b)['question_id']; targets=[records[t] for t in disps.get(key,{}).get('proposed_target_ids',[])]
 pages=sorted({e['pdf_page'] for q in [a,b]+targets if q for e in q['evidence']})
 items.append({'item_id':f'validation-{len(items)+1:02d}','record_id':key,'year_label':(a or b)['year_label'],'pdf_pages':pages,'before':a,'after':b,'proposed_merge_targets':targets,'decision':None,'reviewer':None,'review_date':None,'rationale':None,'transcription_checked':False,'segmentation_checked':False,'passage_link_checked':False})
source=Path('question_paper (1).pdf');pdf=pdfium.PdfDocument(str(source));images={};image_hashes={}
for n in sorted({n for item in items for n in item['pdf_pages']}):
 page=pdf[n-1];im=page.render(scale=1.35).to_pil().convert('RGB');buf=io.BytesIO();im.save(buf,format='JPEG',quality=85);raw=buf.getvalue();images[n]=base64.b64encode(raw).decode();image_hashes[str(n)]=hashlib.sha256(raw).hexdigest();page.close()
pdf.close()
esc=html.escape
cards=[]
for item in items:
 idx=item['item_id'];a=item['before'];b=item['after']
 fields=[k for k in set(a or {})|set(b or {}) if (a or {}).get(k)!=(b or {}).get(k) and k!='parser_version']
 snaps=''
 for title,q in [('Previous parser record',a),('Reconciled proposal',b)]+[('Proposed merge target',q) for q in item['proposed_merge_targets']]:
  snaps+=f'<details open><summary>{title}</summary><pre>{esc(json.dumps(q,ensure_ascii=False,indent=2))}</pre></details>'
 pics=''.join(f'<details><summary>Show full source PDF page {n}</summary><img alt="Source PDF page {n}" src="data:image/jpeg;base64,{images[n]}"></details>' for n in item['pdf_pages'])
 cards.append(f'''<article id="{idx}" data-id="{idx}"><h2>{idx}: {item['year_label']}, PDF pages {', '.join(map(str,item['pdf_pages']))}</h2><p>Record: <code>{esc(item['record_id'])}</code></p><p>Changed fields: {esc(', '.join(sorted(fields)))}</p>{pics}{snaps}<fieldset><legend>Human validation (blank until reviewed)</legend><label>Decision <select name="decision"><option value="">Unreviewed</option><option>accept</option><option>reject</option><option>unresolved</option></select></label><label>Reviewer <input name="reviewer"></label><label>Review date <input type="date" name="review_date"></label><p><label><input type="checkbox" name="transcription_checked"> Transcription checked</label> <label><input type="checkbox" name="segmentation_checked"> Segmentation checked</label> <label><input type="checkbox" name="passage_link_checked"> Passage link checked</label></p><label>Rationale, corrections or uncertainty<textarea name="rationale" rows="3"></textarea></label></fieldset></article>''')
script='''<script>
const items=ITEM_DATA;
document.getElementById('download').onclick=()=>{const decisions=items.map(item=>{const el=document.getElementById(item.item_id);const result={item_id:item.item_id,record_id:item.record_id,decision:null,reviewer:null,review_date:null,rationale:null};for(const name of ['decision','reviewer','review_date','rationale'])result[name]=el.querySelector('[name="'+name+'"]').value||null;for(const name of ['transcription_checked','segmentation_checked','passage_link_checked'])result[name]=el.querySelector('[name="'+name+'"]').checked;return result;});const blob=new Blob([decisions.map(x=>JSON.stringify(x)).join('\\n')+'\\n'],{type:'application/x-ndjson'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download='human_validation_v012_decisions.jsonl';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
</script>'''.replace('ITEM_DATA',json.dumps([{'item_id':i['item_id'],'record_id':i['record_id']} for i in items]).replace('<','\\u003c'))
page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Human extraction validation: parser v0.1.2</title><style>body{max-width:1100px;margin:30px auto;padding:15px;font:16px/1.5 system-ui}article{border-top:3px solid #456;padding:20px 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f5f7;padding:12px;font-size:13px}img{width:100%;height:auto}input,select,textarea,button{font:inherit;padding:6px}textarea{display:block;width:95%}label{display:inline-block;margin:6px}summary{cursor:pointer;font-weight:bold}code{overflow-wrap:anywhere}.bar{position:sticky;top:0;background:white;padding:12px;border:1px solid #aaa}</style><h1>Human extraction validation: parser v0.1.2</h1><p>Prepared 10 November 2026. Compare each before/after record and proposed merge target with the full source pages. Check numbering, stems, options, segmentation, evidence and passage associations. The first source page is not necessarily the printed page; printed page remains unknown unless checked.</p><p>This deliberately selected change packet is not an independent validation sample and cannot estimate corpus accuracy. All new changes remain AI proposals. Previously accepted decisions are preserved in the reconciled records; record only the scope actually checked here. Legal correctness is outside this packet. Source material is local; rights remain unconfirmed.</p><p>Expand source-page panels to inspect images. Enter decisions and use Download decisions before closing; entries are not automatically saved. Downloading creates a separate log and does not apply corrections.</p><div class="bar"><button id="download">Download decisions (.jsonl)</button> <span>COUNT review items</span></div>'''.replace('COUNT',str(len(items)))+''.join(cards)+script+'</html>'
(out/'review.html').write_text(page,encoding='utf8');(out/'items.jsonl').write_text(''.join(json.dumps(i,ensure_ascii=False)+'\n' for i in items),encoding='utf8')
manifest={'source_sha256':sha(source),'inputs':{str(p):sha(p) for p in [src/'reconciliation.jsonl',src/'questions.jsonl',src/'passages.jsonl',src/'id_dispositions.jsonl']},'embedded_page_image_sha256':image_hashes,'outputs':{p.name:sha(p) for p in out.iterdir() if p.is_file()},'items':len(items),'source_pages':len(images),'status':'targeted_changes_pending_human_validation'}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
assert len(items)==len({i['item_id'] for i in items})
assert all(i['decision'] is None for i in items)
assert page.count('<article ')==len(items) and page.count('<img ')==sum(len(i['pdf_pages']) for i in items)
assert all(sha(out/n)==v for n,v in manifest['outputs'].items())
print(json.dumps({'path':str(out/'review.html'),'items':len(items),'source_pages':len(images),'megabytes':round((out/'review.html').stat().st_size/1e6,1),'checks':'passed'}))
