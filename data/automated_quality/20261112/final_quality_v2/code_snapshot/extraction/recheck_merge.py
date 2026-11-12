"""Reuse retained OCR only when its crops cover every current source anchor."""
import argparse
import copy
import json
import re
from pathlib import Path
from .recovery_run import read,sha
from .automated_quality import compare_text,question_text
from .source_recheck import best_check
from .strict_support import strict_supported
from .quality import write_new_run


def contains_regions(question, parts):
    bypage={p['pdf_page']:p for p in parts}
    for n in question['pdf_pages']:
        boxes=[e['bbox'] for e in question['evidence'] if e['pdf_page']==n]
        p=bypage.get(n)
        if not p or not boxes or p.get('crop_top',1e9)>min(b[1] for b in boxes) or p.get('crop_bottom',-1)<max(b[3] for b in boxes):return False
    return True


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',type=Path,required=True);ap.add_argument('--ocr-run',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    qs=read(args.run/'questions.jsonl');old={c['question_id']:c for c in read(args.run/'comparisons.jsonl')}
    registry={};used=[]
    folder=args.ocr_run/'ocr' if (args.ocr_run/'ocr').exists() else args.ocr_run
    for p in folder.glob('*-psm*.json'):
        if not re.fullmatch(r'q[0-9]+-p[0-9]+-psm[36]\.json',p.name):continue
        data=json.loads(p.read_text(encoding='utf-8'))
        registry.setdefault((data['question_id'],data['ocr_psm']),[]).append((p,data))
    comparisons=[]
    for q in qs:
        c=copy.deepcopy(old[q['question_id']]);checks=[]
        for psm in [3,6]:
            pairs=registry.get((q['question_id'],psm),[]);parts=[d for p,d in pairs]
            if not contains_regions(q,parts):continue
            used.extend(p for p,d in pairs)
            checks.append({'psm':psm,'comparison':compare_text(question_text(q),'\n'.join(p['text'] for p in sorted(parts,key=lambda p:p['pdf_page']))),'evidence':[str(p) for p,d in pairs]})
        if checks:c.update(reused_ocr=checks,final=best_check([c['final']]+[r['comparison'] for r in checks]))
        comparisons.append(c)
    structural=read(args.run/'structural_findings.jsonl');abstentions=read(args.run/'abstentions.jsonl')
    queue=[{'kind':'source_ocr_disagreement',**c} for c in comparisons if not strict_supported(c['final'])]
    summary={'questions':len(qs),'strictly_supported':len(qs)-len(queue),'ocr_exceptions':len(queue),'structural_findings':len(structural),'abstentions':len(abstentions),'automated_gate':'NEEDS_AUTOMATED_REPAIR' if queue or structural or abstentions else 'PASS'}
    inputs=[args.run/'questions.jsonl',args.run/'comparisons.jsonl',args.run/'manifest.json',args.ocr_run/'manifest.json',Path(__file__)]+used
    write_new_run(args.output,{'questions.jsonl':qs,'passages.jsonl':read(args.run/'passages.jsonl'),'structural_findings.jsonl':structural,'abstentions.jsonl':abstentions,'comparisons.jsonl':comparisons,'automatic_repair_queue.jsonl':queue+structural+abstentions,'summary.json':summary,'manifest.json':{'inputs':{str(p):sha(p) for p in inputs}}})
    manifest=json.loads((args.output/'manifest.json').read_text());manifest['outputs']={p.name:sha(p) for p in args.output.iterdir() if p.name!='manifest.json'};(args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
