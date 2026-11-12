"""Bounded native PDF text as additional strict machine corroboration."""
import argparse
import copy
import importlib.metadata
import json
from pathlib import Path
import pypdfium2 as pdfium
from .recovery_run import read,sha
from .automated_quality import question_text,compare_text
from .strict_support import strict_supported
from .source_recheck import best_check
from .quality import write_new_run


def native_region(question,pages):
    parts=[]
    for n in sorted(question['pdf_pages']):
        page,tp=pages[n];boxes=[e['bbox'] for e in question['evidence'] if e['pdf_page']==n]
        if not boxes:raise ValueError('Missing source region')
        top=max(0,min(b[1] for b in boxes)-2);bottom=min(page.get_height(),max(b[3] for b in boxes)+2)
        parts.append(tp.get_text_bounded(0,page.get_height()-bottom,page.get_width(),page.get_height()-top))
    return '\n'.join(parts)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    source=Path('question_paper (1).pdf');config=json.loads(Path('extraction/papers.json').read_text())
    if sha(source)!=config['source_sha256']:raise ValueError('Source hash mismatch')
    qs=read(args.run/'questions.jsonl');byid={q['question_id']:q for q in qs};comparisons=read(args.run/'comparisons.jsonl');pdf=pdfium.PdfDocument(str(source));pages={};evidence=[]
    for c in comparisons:
        if strict_supported(c['final']):continue
        q=byid[c['question_id']]
        for n in q['pdf_pages']:
            if n not in pages:
                p=pdf[n-1];pages[n]=(p,p.get_textpage())
        text=native_region(q,pages);check=compare_text(question_text(q),text)
        evidence.append({'question_id':q['question_id'],'pdf_pages':q['pdf_pages'],'source_evidence':q['evidence'],'source_text':text,'comparison':check,'method':'pdfium_bounded_native_text'})
        c['native_source']=check;c['final']=best_check([c['final'],check])
    for p,tp in pages.values():tp.close();p.close()
    pdf.close()
    structural=read(args.run/'structural_findings.jsonl');abstentions=read(args.run/'abstentions.jsonl');queue=[{'kind':'source_text_disagreement',**c} for c in comparisons if not strict_supported(c['final'])]
    summary={'questions':len(qs),'native_regions_checked':len(evidence),'strictly_supported':len(qs)-len(queue),'source_text_exceptions':len(queue),'structural_findings':len(structural),'abstentions':len(abstentions),'automated_gate':'NEEDS_AUTOMATED_REPAIR' if queue or structural or abstentions else 'PASS','corpus_text_changed':False,'measurement':'strict_lexical_source_support_not_empirical_accuracy'}
    inputs=[source,args.run/'questions.jsonl',args.run/'comparisons.jsonl',args.run/'manifest.json',Path(__file__),Path('extraction/automated_quality.py')]
    write_new_run(args.output,{'questions.jsonl':qs,'passages.jsonl':read(args.run/'passages.jsonl'),'structural_findings.jsonl':structural,'abstentions.jsonl':abstentions,'native_evidence.jsonl':evidence,'comparisons.jsonl':comparisons,'automatic_repair_queue.jsonl':queue+structural+abstentions,'summary.json':summary,'manifest.json':{'inputs':{str(p):sha(p) for p in inputs},'pypdfium2_version':importlib.metadata.version('pypdfium2')}})
    m=json.loads((args.output/'manifest.json').read_text());m['outputs']={p.name:sha(p) for p in args.output.iterdir() if p.name!='manifest.json'};(args.output/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
