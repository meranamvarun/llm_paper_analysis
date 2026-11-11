"""Strict machine-support gate: retain even small lexical gaps as exceptions."""
import argparse
from collections import Counter
import hashlib
import html
import importlib.metadata
import json
from pathlib import Path
import subprocess


def strict_supported(comparison):
    return (comparison.get('status')=='SUPPORTED'
            and comparison.get('ordered_token_agreement')==1
            and not comparison.get('missing_numbers')
            and not comparison.get('negation_disagreements'))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    read=lambda p:[json.loads(line) for line in p.read_text(encoding='utf-8').splitlines() if line.strip()]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    rows=read(args.run/'comparisons.jsonl')
    structural=read(args.run/'structural_findings.jsonl')
    previous=json.loads((args.run/'summary.json').read_text())
    queue=[]
    for row in rows:
        if strict_supported(row['final']):
            continue
        check=row['final']
        queue.append({'kind':'source_ocr_disagreement','question_id':row['question_id'],
                      'year_label':row['year_label'],'pdf_pages':row['pdf_pages'],
                      'priority':'critical_tokens' if check['missing_numbers'] or check['negation_disagreements'] else 'lexical_gap',
                      'final':check,'initial':row['initial'],'second_pass':row['second_pass'],
                      'next_action':'automated_source_reconciliation_no_silent_rewrite'})
    errors=[f for f in structural if f.get('severity','error')=='error']
    summary={**previous,'triage_gate':previous['automated_gate'],
             'automated_gate':'NEEDS_AUTOMATED_REPAIR' if errors or queue else 'PASS',
             'strictly_supported_questions':len(rows)-len(queue),
             'ocr_exception_questions':len(queue),'structural_error_findings':len(errors),
             'structural_warning_findings':len(structural)-len(errors),
             'strict_rule':'All target lexical tokens ordered in machine OCR, no numeric/negation discrepancy; not empirical accuracy',
             'manual_extraction_benchmark_required':False,
             'required_workflow':'automatic_repair_queue_then_recheck',
             'strict_queue_priorities':dict(Counter(q['priority'] for q in queue))}
    write=lambda name,value:(args.output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    write('summary.json',summary)
    (args.output/'automatic_repair_queue.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in queue+structural),encoding='utf-8')
    cards=[]
    for item in queue+structural:
        cards.append('<details><summary>'+html.escape(item['kind']+' | '+str(item.get('year_label',''))+' | '+str(item.get('question_id',item.get('record_id',item.get('paper_id','')))))+'</summary><pre>'+html.escape(json.dumps(item,ensure_ascii=False,indent=2))+'</pre></details>')
    page='<!doctype html><meta charset="utf-8"><title>Automated extraction quality</title><style>body{max-width:1100px;margin:30px auto;font:16px/1.5 system-ui;padding:15px}pre{white-space:pre-wrap;overflow-wrap:anywhere}details{border-top:1px solid #ccc;padding:10px}summary{cursor:pointer}</style><h1>Automated extraction quality</h1><p>All configured body pages and in-scope questions were checked by software. No manual benchmark is required for continuation. The queue records computational disagreements and structural defects; it does not automatically rewrite source text.</p><pre>'+html.escape(json.dumps(summary,ensure_ascii=False,indent=2))+'</pre><h2>Machine repair queue</h2>'+''.join(cards)
    (args.output/'report.html').write_text(page,encoding='utf-8')
    engine=Path(r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    model=engine.parent/'tessdata/eng.traineddata'
    version=subprocess.run([str(engine),'--version'],capture_output=True,text=True,timeout=15).stdout.splitlines()[0]
    write('manifest.json',{'inputs':{str(args.run/n):sha(args.run/n) for n in ['comparisons.jsonl','structural_findings.jsonl','summary.json','manifest.json']},
                           'code_hashes':{str(p):sha(p) for p in [Path(__file__),Path(__file__).with_name('run.py')]},
                           'software':{'tesseract':version,'english_traineddata_sha256':sha(model),
                                       'pypdfium2':importlib.metadata.version('pypdfium2')},
                           'outputs':{p.name:sha(p) for p in args.output.iterdir() if p.is_file()}})
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
