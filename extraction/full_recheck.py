"""Recheck every current target against retained source readings; no stale scores."""
import argparse
from collections import Counter,defaultdict
import importlib.metadata
import json
from pathlib import Path
import re
import platform
import subprocess
import pypdfium2 as pdfium
import pdfplumber
from .run import word_lines
from .recovery_run import read,sha
from .automated_quality import compare_text,question_text,region_text,structural_checks
from .strict_support import strict_supported
from .source_recheck import best_check
from .native_support import native_region
from .recheck_merge import contains_regions
from .source_content import strip_export_metadata
from .quality import write_new_run
from .field_consensus import field_source_support


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);ap.add_argument('--vision-readings',type=Path);args=ap.parse_args()
    root=Path('data/automated_quality');qs=read(args.run/'questions.jsonl');passages=read(args.run/'passages.jsonl');config=json.loads(Path('extraction/papers.json').read_text());source=Path('question_paper (1).pdf')
    if sha(source)!=config['source_sha256']:raise ValueError('Source mismatch')
    registry=defaultdict(list);used=[];evidence=[];vision={}
    if args.vision_readings:
        used.append(args.vision_readings)
        for v in read(args.vision_readings):
            if v['source_hash']!=config['source_sha256'] or not v.get('image_paths'):raise ValueError('Vision reading missing matching source evidence')
            for path in v['image_paths']:
                if sha(path)!=v['image_sha256'][path]:raise ValueError('Vision image hash mismatch')
                used.append(Path(path))
            vision[v['question_id']]=v
    for folder in [root/'20261112/highres_recheck_v2/ocr',root/'20261112/current_highres_v1/ocr',root/'20261112/metadata_frames_v1']:
        for path in folder.glob('*-psm*.json'):
            if not re.fullmatch(r'q[0-9]+-p[0-9]+-psm[36]\.json',path.name):continue
            value=json.loads(path.read_text(encoding='utf-8'));registry[(value['question_id'],str(folder),value['ocr_psm'])].append((path,value))
    original=read(root/'20261112/structural_repair_v2/questions.jsonl');positions={q['question_id']:i for i,q in enumerate(original)}
    fieldpath=root/'20261112/embedded_fields_v2/fields.jsonl'
    fieldgroups=defaultdict(dict)
    if fieldpath.exists():
        used.append(fieldpath)
        for field in read(fieldpath):fieldgroups[field['question_id']][field['field']]=field
    spatialpdf=pdfplumber.open(str(source))
    pdf=pdfium.PdfDocument(str(source));nativepages={};ocrpages={};comparisons=[];exceptions=[]
    for q in qs:
        checks=[]
        def add(method,text,paths):
            filtered=strip_export_metadata(text) if q['year_label'] in [2016,2017] else text
            check=compare_text(question_text(q),filtered)
            evidence.append({'question_id':q['question_id'],'method':method,'paths':paths,'raw_source_text':text,'comparison_source_text':filtered,'comparison':check})
            checks.append({'method':method,'comparison':check,'evidence_index':len(evidence)-1})
        for n in q['pdf_pages']:
            if n not in nativepages:
                p=pdf[n-1];nativepages[n]=(p,p.get_textpage())
            if n not in ocrpages:
                path=root/'20261111/run_v1/page_ocr'/f'p{n:04d}.json';used.append(path);ocrpages[n]=json.loads(path.read_text(encoding='utf-8'))
        add('pdfium_bounded_native_text',native_region(q,nativepages),[str(source)])
        add('retained_180dpi_page_region',region_text(q,ocrpages),[str(root/'20261111/run_v1/page_ocr'/f'p{n:04d}.json') for n in sorted(q['pdf_pages'])])
        for folder in [root/'20261112/highres_recheck_v2/ocr',root/'20261112/current_highres_v1/ocr',root/'20261112/metadata_frames_v1']:
            for psm in [3,6]:
                pairs=registry.get((q['question_id'],str(folder),psm),[])
                if not contains_regions(q,[value for _,value in pairs]):continue
                used.extend(path for path,_ in pairs)
                add(str(folder)+f':psm{psm}','\n'.join(value['text'] for path,value in sorted(pairs,key=lambda pair:pair[1]['pdf_page'])),[str(path) for path,value in pairs])
        if q['question_id'] in positions:
            paths=[root/'20261111/run_v1/crop_ocr'/f'q{positions[q["question_id"]]:04d}-p{n:04d}.json' for n in sorted(q['pdf_pages'])]
            parts=[json.loads(p.read_text(encoding='utf-8')) for p in paths if p.exists()]
            # Old crops record crop_top but not crop_bottom; derive it from TSV words
            # is unsafe. Reuse only if source anchors match the original record.
            prior=original[positions[q['question_id']]]
            if len(parts)==len(paths) and prior['evidence']==q['evidence']:
                used.extend(paths);add('retained_240dpi_same_anchors','\n'.join(p['text'] for p in parts),[str(p) for p in paths])
        if q['question_id'] in fieldgroups:
            group=fieldgroups[q['question_id']]
            if set(group)=={'stem','option_A','option_B','option_C','option_D'}:
                supported=field_source_support(q,group)
                if supported:
                    add('individually_supported_source_fields',supported['source_text'],[f['reading']['path'] for f in supported['fields']])
                for mode in [0,1]:
                    parts=[];paths=[]
                    for field in ['stem','option_A','option_B','option_C','option_D']:
                        f=group[field];r=sorted(f['readings'],key=lambda r:r['psm'])[mode]
                        if r['returncode']:raise ValueError('Source field OCR failure')
                        parts.append(('' if field=='stem' else str('ABCD'.index(field[-1])+1)+'. ')+r['text'])
                        paths.extend([r['path'],f['raw_image']]);used.extend(Path(p) for p in [r['path'],f['raw_image']])
                    add(f'embedded_source_fields_reading_{mode}','\n'.join(parts),paths)
        if not any(strict_supported(c['comparison']) for c in checks) and q['year_label']!=2017:
            for tolerance in [.5,1,2]:
                parts=[]
                for n in q['pdf_pages']:
                    page=spatialpdf.pages[n-1];boxes=[e['bbox'] for e in q['evidence'] if e['pdf_page']==n]
                    top=max(0,min(b[1] for b in boxes)-2);bottom=min(page.height,max(b[3] for b in boxes)+2)
                    words=page.crop((0,top,page.width,bottom)).extract_words(x_tolerance=tolerance)
                    parts.extend(l['text'] for l in word_lines(words))
                add(f'pdfplumber_native_geometry_x_tolerance_{tolerance}','\n'.join(parts),[str(source)])
                if strict_supported(checks[-1]['comparison']):break
        if q['question_id'] in vision:
            v=vision[q['question_id']]
            add('assistant_source_image_transcription_unreviewed',v['source_text'],v['image_paths'])
        final=best_check([c['comparison'] for c in checks]);winning=next(c for c in checks if c['comparison']==final)
        row={'question_id':q['question_id'],'year_label':q['year_label'],'pdf_pages':q['pdf_pages'],'target_text_sha256':__import__('hashlib').sha256(question_text(q).encode()).hexdigest(),'final':final,'selected_source':winning,'readings':checks}
        comparisons.append(row)
        if not strict_supported(final):exceptions.append({'kind':'source_text_disagreement',**row})
    for p,tp in nativepages.values():tp.close();p.close()
    pdf.close();spatialpdf.close();structural=structural_checks(qs,passages,config);abstentions=read(args.run/'abstentions.jsonl') if (args.run/'abstentions.jsonl').exists() else []
    summary={'questions':len(qs),'strictly_supported':len(qs)-len(exceptions),'source_text_exceptions':len(exceptions),'exceptions_by_year':dict(Counter(q['year_label'] for q in exceptions)),'structural_findings':dict(Counter(f['kind'] for f in structural)),'abstentions':len(abstentions),'automated_gate':'NEEDS_AUTOMATED_REPAIR' if exceptions or structural or abstentions else 'PASS','measurement':'strict_lexical_source_support_not_empirical_accuracy','native_decoder':importlib.metadata.version('pypdfium2'),'assistant_image_source_readings':len(vision),'independent_human_validation':False,'gate_version':'source-support-v2','selected_support_methods':dict(Counter(c['selected_source']['method'] for c in comparisons))}
    inputs=[source,args.run/'questions.jsonl',args.run/'passages.jsonl',args.run/'manifest.json',Path('extraction/papers.json')]+sorted(Path('extraction').glob('*.py'))+used
    write_new_run(args.output,{'questions.jsonl':qs,'passages.jsonl':passages,'structural_findings.jsonl':structural,'abstentions.jsonl':abstentions,'source_readings.jsonl':evidence,'comparisons.jsonl':comparisons,'automatic_repair_queue.jsonl':exceptions+structural+abstentions,'summary.json':summary,'manifest.json':{'inputs':{str(p):sha(p) for p in inputs},'software':{'python':platform.python_version(),'pypdf':importlib.metadata.version('pypdf'),'pdfplumber':importlib.metadata.version('pdfplumber'),'pypdfium2':importlib.metadata.version('pypdfium2'),'tesseract':subprocess.run([r'C:\Program Files\Tesseract-OCR\tesseract.exe','--version'],capture_output=True,text=True,timeout=15).stdout.splitlines()[0]}}})
    m=json.loads((args.output/'manifest.json').read_text());m['outputs']={p.name:sha(p) for p in args.output.iterdir() if p.name!='manifest.json'};(args.output/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
