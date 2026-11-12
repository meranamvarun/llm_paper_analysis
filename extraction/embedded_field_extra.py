"""Additional block-layout reading of the already preserved source field images."""
import argparse
from concurrent.futures import ThreadPoolExecutor,as_completed
import json
from pathlib import Path
from .recovery_run import read,sha
from .embedded_field_ocr import worker


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    source=Path('data/automated_quality/20261112/embedded_fields_v1');items=read(source/'fields.jsonl');jobs={}
    with ThreadPoolExecutor(max_workers=6) as pool:
        for item in items:
            if 6 in {r['psm'] for r in item['readings']}:continue
            path=Path(item['prepared_image']);out=args.output/(path.stem+'-psm6.txt');jobs[pool.submit(worker,path,6,out)]=item
        print(f'Queued {len(jobs)} extra field readings',flush=True)
        for i,f in enumerate(as_completed(jobs),1):
            jobs[f]['readings'].append(f.result())
            if i%50==0:print(f'Extra field OCR {i}/{len(jobs)}',flush=True)
    (args.output/'fields.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in items),encoding='utf-8')
    (args.output/'manifest.json').write_text(json.dumps({'inputs':{str(p):sha(p) for p in [source/'fields.jsonl',source/'manifest.json',Path(__file__)]},'outputs':{p.name:sha(p) for p in args.output.iterdir() if p.is_file()}},indent=2),encoding='utf-8')

if __name__=='__main__':main()
