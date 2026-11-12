"""OCR complete metadata-question frames, including previously lost options."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
from pathlib import Path
import pypdfium2 as pdfium
from .recovery_run import read,sha
from .run import ocr_page


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    path=Path('data/automated_quality/20261112/boundary_recovery_v3/questions.jsonl');qs=read(path)
    selected=[q for q in qs if q['format']=='mcq' and [o['label'] for o in q['options']]!=list('ABCD')]
    original=read(Path('data/automated_quality/20261112/structural_repair_v2/questions.jsonl'))
    pdf=pdfium.PdfDocument('question_paper (1).pdf');jobs={};evidence=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for index,q in enumerate(selected):
            group=sorted([r for r in original if r['year_label']==q['year_label']],key=lambda r:(r['evidence'][0]['pdf_page'],r['evidence'][0]['bbox'][1]))
            pos=next(i for i,r in enumerate(group) if r['question_id']==q['question_id'])
            source=group[pos];start=source['evidence'][0];following=group[pos+1]['evidence'][0] if pos+1<len(group) else None
            if not source['raw_text'].startswith(('Question Number','Q.')):raise ValueError('Metadata frame missing')
            endpage=following['pdf_page'] if following else max(q['pdf_pages'])
            for n in range(start['pdf_page'],endpage+1):
                p=pdf[n-1];height=p.get_height();image=p.render(scale=500/72).to_pil().convert('RGB');p.close()
                top=max(0,start['bbox'][1]-4) if n==start['pdf_page'] else 0
                bottom=max(0,following['bbox'][1]-2) if following and n==following['pdf_page'] else height
                if bottom<=top:continue
                crop=image.crop((0,int(top*500/72),image.width,int(bottom*500/72)))
                imagepath=args.output/f'q{index:03d}-p{n:04d}.png';crop.save(imagepath)
                frame={'question_id':q['question_id'],'year_label':q['year_label'],'number':q['printed_question_number'],'pdf_page':n,'crop_top':top,'crop_bottom':bottom,'start_anchor':start,'following_anchor':following}
                evidence.append(frame)
                for psm in [3,6]:
                    cache=imagepath.with_name(imagepath.stem+f'-psm{psm}.json')
                    f=pool.submit(ocr_page,n,imagepath,r'C:\Program Files\Tesseract-OCR\tesseract.exe',500,frame,cache,psm);jobs[f]=(q['question_id'],psm,n)
        pdf.close();print(f'Queued {len(jobs)} metadata OCR jobs',flush=True)
        for i,f in enumerate(as_completed(jobs),1):
            f.result()
            if i%10==0:print(f'Metadata OCR {i}/{len(jobs)}',flush=True)
    (args.output/'frames.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in evidence),encoding='utf-8')
    (args.output/'manifest.json').write_text(json.dumps({'inputs':{str(path):sha(path),'question_paper (1).pdf':sha('question_paper (1).pdf'),str(Path(__file__)):sha(Path(__file__))},'settings':{'dpi':500,'psm':[3,6]},'outputs':{p.name:sha(p) for p in args.output.iterdir() if p.is_file()}},indent=2),encoding='utf-8')

if __name__=='__main__':main()
