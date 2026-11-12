"""High-resolution alternate OCR corroboration without changing corpus text."""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor,as_completed
import hashlib
import json
from pathlib import Path
import pypdfium2 as pdfium
from .run import ocr_page
from .automated_quality import question_text,compare_text
from .strict_support import strict_supported
from .recovery_run import read,sha


def best_check(checks):
    return max(checks,key=lambda c:(strict_supported(c),c.get('ordered_token_agreement') or 0))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--dpi',type=int,default=400)
    ap.add_argument('--workers',type=int,default=6)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    source=Path('question_paper (1).pdf');config=json.loads(Path('extraction/papers.json').read_text())
    if sha(source)!=config['source_sha256']:raise ValueError('Source hash mismatch')
    qs=read(args.run/'questions.jsonl');old=read(args.run/'comparisons.jsonl');byid={q['question_id']:q for q in qs}
    selected=[c for c in old if not strict_supported(c['final'])]
    wanted={n for c in selected for n in byid[c['question_id']]['pdf_pages']}
    remaining=Counter(n for c in selected for n in byid[c['question_id']]['pdf_pages'])
    images={};pdf=pdfium.PdfDocument(str(source))
    folder=args.output/'ocr';folder.mkdir()
    tasks={};outputs={};errors=[]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        index={q['question_id']:i for i,q in enumerate(qs)}
        for c in selected:
            q=byid[c['question_id']];i=index[q['question_id']]
            for n in sorted(q['pdf_pages']):
                boxes=[e['bbox'] for e in q['evidence'] if e['pdf_page']==n]
                if not boxes:continue
                if n not in images:
                    p=pdf[n-1];images[n]=(p.render(scale=args.dpi/72).to_pil().convert('RGB'),p.get_height());p.close()
                image,height=images[n]
                top=max(0,min(b[1] for b in boxes)-4);bottom=min(height,max(b[3] for b in boxes)+4)
                crop=image.crop((0,int(top*args.dpi/72),image.width,int(bottom*args.dpi/72)))
                path=folder/f'q{i:04d}-p{n:04d}.png';crop.save(path)
                for psm in [3,6]:
                    cache=folder/f'q{i:04d}-p{n:04d}-psm{psm}.json'
                    f=pool.submit(ocr_page,n,path,r'C:\Program Files\Tesseract-OCR\tesseract.exe',args.dpi,{'pdf_page':n,'crop_top':top,'crop_bottom':bottom,'question_id':q['question_id']},cache,psm)
                    tasks[f]=(q['question_id'],psm,n)
                remaining[n]-=1
                if remaining[n]==0: images.pop(n,None)
        print(f'Queued {len(tasks)} crop OCR jobs for {len(selected)} questions',flush=True)
        images.clear();pdf.close()
        for k,f in enumerate(as_completed(tasks),1):
            key=tasks[f]
            try:outputs[key]=f.result()
            except Exception as exc:errors.append({'key':key,'error':str(exc)})
            if k%40==0 or k==len(tasks):print(f'OCR {k}/{len(tasks)}',flush=True)
    comparisons=[];supported=0
    for c in old:
        q=byid[c['question_id']];checks=[]
        for psm in [3,6]:
            parts=[outputs.get((q['question_id'],psm,n)) for n in sorted(q['pdf_pages'])]
            if any(p is None or p.get('method')=='unresolved' for p in parts):continue
            text='\n'.join(p['text'] for p in parts)
            checks.append({'psm':psm,'dpi':args.dpi,'comparison':compare_text(question_text(q),text)})
        if checks:
            c={**c,'alternate_passes':checks,'final':best_check([c['final']]+[r['comparison'] for r in checks])}
        comparisons.append(c);supported+=strict_supported(c['final'])
    structural=read(args.run/'structural_findings.jsonl');abstentions=read(args.run/'abstentions.jsonl') if (args.run/'abstentions.jsonl').exists() else []
    queue=[{'kind':'source_ocr_disagreement',**c} for c in comparisons if not strict_supported(c['final'])]
    summary={'questions':len(qs),'new_ocr_questions':len(selected),'strictly_supported':supported,'ocr_exceptions':len(queue),'dpi':args.dpi,'psm':[3,6],'ocr_failures':errors,'automated_gate':'NEEDS_AUTOMATED_REPAIR' if queue or structural or abstentions or errors else 'PASS','corpus_text_changed':False}
    for name,value in [('comparisons.jsonl',comparisons),('automatic_repair_queue.jsonl',queue+structural+abstentions)]:
        (args.output/name).write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in value),encoding='utf-8')
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    inputs=[source,args.run/'questions.jsonl',args.run/'comparisons.jsonl',args.run/'manifest.json',Path(__file__),Path('extraction/run.py')]
    manifest={'inputs':{str(p):sha(p) for p in inputs},'outputs':{str(p.relative_to(args.output)):sha(p) for p in args.output.rglob('*') if p.is_file()},'settings':{'dpi':args.dpi,'psm':[3,6],'workers':args.workers}}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
