"""Conservative, source-supported option-boundary proposals."""
import argparse
import copy
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import re
from .automated_quality import structural_checks, compare_text, question_text, region_text
from .strict_support import strict_supported
from .quality import write_new_run

VERSION = '0.1.0'

def normalized(text):
    return ' '.join(text.casefold().split())

def repair_records(rows):
    result = copy.deepcopy(rows)
    logs = []
    for q in result:
        if not 2016 <= q['year_label'] <= 2026 or q.get('review_status') in {'accepted','reviewed','human_reviewed'}:
            continue
        original = q['options']
        if [o['label'] for o in original] == list('ABCD'):
            continue
        options, joined = [], []
        for item in original:
            prior = options[-1]['text'].strip() if options else ''
            # Only a whole referential prefix may introduce nested labels.
            reference = re.fullmatch(r'(?:both|neither|either)(?:\s+\([A-D]\)\s+(?:and|or|nor))*', prior, re.I)
            marker = item.get('raw_label','')
            if reference and re.fullmatch(r'\([A-D]\)',marker):
                options[-1]['text'] = (prior+' '+marker+' '+item['text']).strip()
                joined.append(len(options)-1)
            else:
                options.append(copy.deepcopy(item))
        if not joined or [o['label'] for o in options] != list('ABCD') or any(not o['text'].strip() for o in options):
            continue
        if any(normalized(options[i]['text']) not in normalized(q.get('raw_text','')) for i in set(joined)):
            continue
        q['options'] = options
        logs.append({'question_id':q['question_id'],'pdf_pages':q['pdf_pages'], 'field':'options',
                     'before':copy.deepcopy(original),'after':copy.deepcopy(options),
                     'rule':'literal_source_supported_nested_option_references', 'version':VERSION,
                     'status':'machine_proposal_unreviewed'})
    return result, logs

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--questions',type=Path,required=True)
    ap.add_argument('--passages',type=Path,required=True)
    ap.add_argument('--ocr-run',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    read=lambda p:[json.loads(l) for l in p.read_text(encoding='utf-8-sig').splitlines() if l.strip()]
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    inputs=[args.questions,args.passages,Path('extraction/papers.json'),args.ocr_run/'comparisons.jsonl',args.ocr_run/'manifest.json',Path(__file__),Path('extraction/automated_quality.py'),Path('extraction/strict_support.py')]
    rows=read(args.questions); passages=read(args.passages)
    repaired,logs=repair_records(rows)
    config=json.loads(inputs[2].read_text())
    scoped=lambda rr:[q for q in rr if 2016<=q['year_label']<=2026]
    before=structural_checks(scoped(rows),passages,config)
    after=structural_checks(scoped(repaired),passages,config)
    comparisons=read(args.ocr_run/'comparisons.jsonl')
    changed={l['question_id'] for l in logs}
    pages={}
    evidence=[]
    positions={q['question_id']:i for i,q in enumerate(scoped(rows))}
    for q in repaired:
        if q['question_id'] not in changed: continue
        for n in q['pdf_pages']:
            p=args.ocr_run/'page_ocr'/f'p{n:04d}.json'
            if n not in pages:
                pages[n]=json.loads(p.read_text(encoding='utf-8')); evidence.append(p)
        check=compare_text(question_text(q),region_text(q,pages))
        old=next(r for r in comparisons if r['question_id']==q['question_id'])
        crop_paths=[args.ocr_run/'crop_ocr'/f'q{positions[q["question_id"]]:04d}-p{n:04d}.json' for n in sorted(q['pdf_pages'])]
        second=None
        if all(p.exists() for p in crop_paths):
            evidence.extend(crop_paths)
            second=compare_text(question_text(q),'\n'.join(json.loads(p.read_text(encoding='utf-8'))['text'] for p in crop_paths))
        final=max([check]+([second] if second else []),key=lambda c:(c['status']=='SUPPORTED',c['ordered_token_agreement'] or 0))
        old.update(initial=check,final=final,repair_recheck='retained_ocr_recompared_with_changed_target',second_pass=second)
    queue=[r for r in comparisons if not strict_supported(r['final'])]
    summary={'version':VERSION,'records':len(rows),'in_scope':len(scoped(rows)),
             'changed_questions':len(logs),'structural_before':dict(Counter(f['kind'] for f in before)),
             'structural_after':dict(Counter(f['kind'] for f in after)),
             'ocr_exceptions':len(queue),'strictly_supported':len(comparisons)-len(queue),
             'automated_gate':'NEEDS_AUTOMATED_REPAIR' if queue or any(f.get('severity','error')=='error' for f in after) else 'PASS',
             'status':'machine_proposals_not_human_validation'}
    files={'questions.jsonl':repaired,'repairs.jsonl':logs,'structural_findings.jsonl':after,
           'comparisons.jsonl':comparisons,'automatic_repair_queue.jsonl':queue+after,'summary.json':summary,
           'manifest.json':{'inputs':{str(p):sha(p) for p in inputs+evidence},'version':VERSION}}
    write_new_run(args.output,files)
    page='<!doctype html><meta charset="utf-8"><title>Structural repair proposals</title><style>body{max-width:1000px;margin:30px auto;font:16px system-ui}pre{white-space:pre-wrap}</style><h1>Structural repair proposals</h1><p>Machine proposals; no human validation. Source PDF and input records are preserved. Unresolved exceptions remain in the repair queue.</p><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre>'
    for log in logs:
        page+='<details><summary>'+html.escape(log['question_id'])+'</summary><pre>'+html.escape(json.dumps(log,ensure_ascii=False,indent=2))+'</pre></details>'
    (args.output/'report.html').write_text(page,encoding='utf-8')
    manifest=json.loads((args.output/'manifest.json').read_text())
    manifest['outputs']={p.name:sha(p) for p in args.output.iterdir() if p.name!='manifest.json'}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
