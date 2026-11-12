"""OCR the original 2017 stem/option image objects, retaining field boundaries."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
import os
from pathlib import Path
import subprocess
import pdfplumber
from pypdf import PdfReader
from PIL import Image,ImageOps
from .field_consensus import decode_field_image
from .recovery_run import read,sha


def worker(path,psm,out):
    proc=subprocess.run([r'C:\Program Files\Tesseract-OCR\tesseract.exe',str(path),'stdout','-l','eng','--dpi','400','--psm',str(psm)],capture_output=True,timeout=120,env={**os.environ,'OMP_THREAD_LIMIT':'1'})
    text=proc.stdout.decode('utf-8',errors='replace')
    out.write_text(text,encoding='utf-8');out.with_suffix('.stderr.txt').write_bytes(proc.stderr)
    return {'psm':psm,'text':text,'path':str(out),'returncode':proc.returncode}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    source=Path('question_paper (1).pdf');config=json.loads(Path('extraction/papers.json').read_text())
    if sha(source)!=config['source_sha256']:raise ValueError('Source mismatch')
    original=Path('data/automated_quality/20261112/structural_repair_v2/questions.jsonl');qs=sorted([q for q in read(original) if q['year_label']==2017],key=lambda q:int(q['printed_question_number']))
    pdf=PdfReader(str(source));native=pdfplumber.open(str(source));jobs={};items=[];excluded=[]
    with ThreadPoolExecutor(max_workers=6) as pool:
        for i,q in enumerate(qs):
            start=q['evidence'][0];following=qs[i+1]['evidence'][0] if i+1<len(qs) else None;images=[]
            for n in range(start['pdf_page'],(following['pdf_page'] if following else 432)+1):
                p=native.pages[n-1];top=start['bbox'][1]-2 if n==start['pdf_page'] else 0;bottom=following['bbox'][1]-2 if following and n==following['pdf_page'] else p.height
                images.extend((n,im) for im in p.images if im['srcsize'][0]==755 and im['srcsize'][1]>=20 and top<=(im['top']+im['bottom'])/2<bottom)
            images.sort(key=lambda pair:(pair[0],pair[1]['top']))
            if len(images)!=5:
                if int(q['printed_question_number']) not in [50,100] or len(images)!=8:raise ValueError('Unexpected embedded field count')
                excluded.extend({'question_id':q['question_id'],'reason':'post_question_section_instructions','pdf_page':n,'name':im['name'],'bbox':[im['x0'],im['top'],im['x1'],im['bottom']]} for n,im in images[5:]);images=images[:5]
            for field,(n,meta) in zip(['stem','option_A','option_B','option_C','option_D'],images):
                stream=pdf.pages[n-1]['/Resources']['/XObject']['/'+meta['name']]
                im=decode_field_image(stream);name=f'q{int(q["printed_question_number"]):03d}-{field}'
                raw=args.output/(name+'-raw.png');im.save(raw)
                if field!='stem':im=im.crop((38,0,im.width,im.height))
                modepair=[7,13] if im.height<=40 else [6,3]
                prepared=ImageOps.expand(im.convert('L').resize((im.width*4,im.height*4),Image.Resampling.LANCZOS),border=12,fill='white');imagepath=args.output/(name+'-ocr.png');prepared.save(imagepath)
                item={'question_id':q['question_id'],'printed_question_number':q['printed_question_number'],'field':field,'source_pdf_page':n,'source_image_name':meta['name'],'bbox':[meta['x0'],meta['top'],meta['x1'],meta['bottom']],'raw_image':str(raw),'prepared_image':str(imagepath),'option_gutter_pixels_excluded':0 if field=='stem' else 38,'readings':[]};items.append(item)
                for psm in modepair:
                    out=args.output/(name+f'-psm{psm}.txt');f=pool.submit(worker,imagepath,psm,out);jobs[f]=item
        native.close();print(f'Queued {len(jobs)} field OCR jobs',flush=True)
        for i,f in enumerate(as_completed(jobs),1):
            jobs[f]['readings'].append(f.result())
            if i%50==0:print(f'Field OCR {i}/{len(jobs)}',flush=True)
    (args.output/'fields.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in items),encoding='utf-8')
    (args.output/'excluded_images.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in excluded),encoding='utf-8')
    inputs=[source,original,Path(__file__),Path('extraction/field_consensus.py')]
    manifest={'inputs':{str(p):sha(p) for p in inputs},'settings':{'native_image_objects':True,'upscale':4,'workers':6,'engine':'Tesseract eng','field_layout_modes':'7/13 for single-line images; 6/3 for multiline images'},'outputs':{p.name:sha(p) for p in args.output.iterdir() if p.is_file()}}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');print('Embedded field OCR complete',flush=True)

if __name__=='__main__':main()
