"""Run auditable source recovery against frozen page evidence."""
import argparse
from collections import Counter
import copy
from difflib import SequenceMatcher
import hashlib
import html
import json
from pathlib import Path
import re
from .recovery import letter_parts,transfer_cleaning,metadata_options,answer_delimited_blocks,flat
from .run import body_page
from .automated_quality import structural_checks,compare_text,question_text,region_text,tokens
from .strict_support import strict_supported
from .quality import write_new_run


def read(path):return [json.loads(s) for s in Path(path).read_text(encoding='utf-8-sig').splitlines() if s.strip()]
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def anchor(line):return (line['pdf_page'],line['line_id'])
def ev(lines):return [{k:l[k] for k in ['pdf_page','line_id','bbox']} for l in lines]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    root=Path('data/automated_quality')
    source=root/'20261112/structural_repair_v2/questions.jsonl'
    pagepath=Path('data/extraction/runs/20261110T043421397159Z/pages.jsonl')
    passagepath=Path('data/corpus_review/20261110/reconciled_v0.1.2/passages.jsonl')
    ocrroot=root/'20261111/run_v1'
    inputs=[source,pagepath,passagepath,Path('extraction/papers.json'),ocrroot/'comparisons.jsonl',ocrroot/'manifest.json',Path(__file__),Path('extraction/recovery.py'),Path('extraction/automated_quality.py')]
    rows=read(source);result=copy.deepcopy(rows);passages=read(passagepath)
    config=json.loads(Path('extraction/papers.json').read_text())
    pages={p['pdf_page']:p for p in read(pagepath)}
    ocrpages={};used=[]
    def ocr(n):
        if n not in ocrpages:
            p=ocrroot/'page_ocr'/f'p{n:04d}.json';used.append(p);ocrpages[n]=json.loads(p.read_text(encoding='utf-8'))
        return ocrpages[n]
    logs=[];abstentions=[];dispositions=[];inactive=set();changed=set()
    def change(q, updates, rule, evidence=None):
        if q.get('accepted_correction'):return
        updates={k:v for k,v in updates.items() if q.get(k)!=v}
        if not updates:return
        logs.append({'question_id':q['question_id'],'rule':rule,'before':{k:copy.deepcopy(q.get(k)) for k in updates},'after':copy.deepcopy(updates),'source_evidence':evidence or q['evidence'],'status':'machine_proposal_unreviewed'})
        q.update(updates);changed.add(q['question_id'])
    # Line-start markers distinguish primary options from inline initials/subsections.
    for q in result:
        if q.get('accepted_correction') or [o['label'] for o in q['options']]==list('ABCD'):continue
        if q['year_label']!=2017:
            proposal=letter_parts(q['raw_text'])
            if not proposal:continue
            transferred=transfer_cleaning(*proposal,q)
            if not transferred:
                abstentions.append({'question_id':q['question_id'],'reason':'prior_cleaning_transfer_ambiguous'});continue
            stem,options,_=transferred
            change(q,{'stem':stem,'options':options},'primary_line_start_options_prior_cleaning_preserved')
        else:
            lines=[]
            for n in q['pdf_pages']:
                for l in ocr(n)['lines']:
                    lines.append({**l,'pdf_page':n})
            candidates=metadata_options(lines,q['printed_question_number'])
            if len(candidates)!=1:continue
            options,evidence=candidates[0]
            # Match prior cleaned answers by text, independently of broken labels.
            assigned=set();preserved=[];valid=True
            for new in options:
                scores=sorted([(SequenceMatcher(None,tokens(old['text']),tokens(new['text']),autojunk=False).ratio(),i) for i,old in enumerate(q['options'])],reverse=True)
                score,index=scores[0] if scores else (0,None)
                if score>=.65 and index not in assigned and (len(scores)<2 or score-scores[1][0]>.12):
                    new['text']=q['options'][index]['text'];assigned.add(index);preserved.append(index)
            # Every existing answer must survive a unique match. Otherwise abstain.
            if len(assigned)!=len(q['options']):continue
            change(q,{'options':options},'explicit_numeric_source_ocr_labels_with_prior_cleaned_answers',ev(evidence))
    # Unlabelled passages: explicit answer terminators delimit question bodies.
    for paper in config['papers']:
        year=paper['year_label']
        if year not in [2020,2021]:continue
        lines=[]
        for lo,hi in paper['body_ranges']:
            for n in range(lo,hi+1):
                page=body_page(pages[n],paper)
                lines.extend({**l,'pdf_page':n} for l in page['lines'])
        blocks=answer_delimited_blocks(lines,120)
        if blocks is None:
            abstentions.append({'year_label':year,'reason':'source_answer_delimiters_or_literal_number_sequence_incomplete'});continue
        active_passage=None
        byanchor={}
        for q in result:
            if q['year_label']==year:
                byanchor.setdefault(anchor(q['evidence'][0]),[]).append(q)
        for block in blocks:
            gap=block['preceding_passage']
            if gap:
                if len(tokens(' '.join(l['text'] for l in gap)))<30:
                    abstentions.append({'year_label':year,'number':block['number'],'reason':'short_nonempty_source_gap','source_evidence':ev(gap)})
                    active_passage=None
                else:
                    first=gap[0];pid=f"{config['source_sha256']}:p{first['pdf_page']:04d}:{first['line_id']}:passage"
                    active_passage=pid
                    passages.append({'passage_id':pid,'paper_id':paper['paper_id'],'printed_label':None,'raw_text':'\n'.join(l['text'] for l in gap),'evidence':ev(gap),'review_status':'unreviewed','boundary_rule':'between_explicit_answer_terminator_and_literal_question_start'})
            qlines=block['lines'];a=anchor(qlines[0])
            selected=byanchor.get(a,[])
            if not selected:
                spananchors={anchor(l) for l in qlines}
                selected=[q for q in result if q['year_label']==year and anchor(q['evidence'][0]) in spananchors]
            if len(selected)!=1:
                abstentions.append({'year_label':year,'number':block['number'],'reason':'ambiguous_question_source_anchor'});continue
            q=selected[0]
            proposal=letter_parts('\n'.join(l['text'] for l in qlines))
            updates={'printed_question_number':str(block['number']),'passage_id':active_passage,'evidence':ev(qlines),'pdf_pages':sorted({l['pdf_page'] for l in qlines})}
            if proposal:
                transferred=transfer_cleaning(*proposal,q)
                if transferred:updates.update(stem=transferred[0],options=transferred[1])
            change(q,updates,'explicit_answer_delimited_question_and_passage',ev(qlines))
        # False paragraph candidates are retained in originals and disposition log.
        gapanchors={anchor(l) for b in blocks for l in b['preceding_passage']}
        for q in result:
            if q['year_label']==year and anchor(q['evidence'][0]) in gapanchors:
                target=next(p['passage_id'] for p in passages if p['paper_id']==paper['paper_id'] and anchor(q['evidence'][0]) in {anchor(e) for e in p['evidence']})
                inactive.add(q['question_id']);dispositions.append({'question_id':q['question_id'],'disposition':'numbered_passage_paragraph_not_exam_question','target_passage_id':target,'original_record':next(r for r in rows if r['question_id']==q['question_id']),'status':'machine_proposal_unreviewed'})
    # Initial Roman I passage in 2022 lies outside the old heading-x threshold.
    paper=next(p for p in config['papers'] if p['year_label']==2022)
    first=next(q for q in result if q['year_label']==2022 and q['printed_question_number']=='1')
    n=first['pdf_pages'][0];a=anchor(first['evidence'][0]);gap=[]
    for l in body_page(pages[n],paper)['lines']:
        if (n,l['line_id'])==a:break
        gap.append({**l,'pdf_page':n})
    gap=[l for l in gap if not (l['bbox'][1]<125 and re.search(r'\bPG\b',l['text']))]
    if gap and len(tokens(' '.join(l['text'] for l in gap)))>=30:
        pid=f"{config['source_sha256']}:p{n:04d}:{gap[0]['line_id']}:passage"
        passages.append({'passage_id':pid,'paper_id':paper['paper_id'],'printed_label':None,'raw_text':'\n'.join(l['text'] for l in gap),'evidence':ev(gap),'review_status':'unreviewed','boundary_rule':'initial_source_text_before_first_question_and_next_explicit_passage'})
        first_existing=min((e['pdf_page'],e['bbox'][1]) for p in passages if p['paper_id']==paper['paper_id'] and p['passage_id']!=pid for e in p['evidence'])
        for q in result:
            if q['year_label']==2022 and not q.get('passage_id') and (q['evidence'][0]['pdf_page'],q['evidence'][0]['bbox'][1])<first_existing:
                change(q,{'passage_id':pid},'source_initial_passage_before_first_question',ev(gap))
    active=[q for q in result if q['question_id'] not in inactive]
    structural=structural_checks(active,passages,config)
    oldcomp={c['question_id']:c for c in read(ocrroot/'comparisons.jsonl')}
    positions={q['question_id']:i for i,q in enumerate(rows)}
    original={q['question_id']:q for q in rows}
    comparisons=[]
    for q in active:
        old=copy.deepcopy(oldcomp[q['question_id']])
        if q['question_id'] in changed:
            for n in q['pdf_pages']:ocr(n)
            first=compare_text(question_text(q),region_text(q,ocrpages))
            second=None
            # Frozen crop geometry is reusable only for unchanged source regions.
            if q['evidence']==original[q['question_id']]['evidence']:
                paths=[ocrroot/'crop_ocr'/f'q{positions[q["question_id"]]:04d}-p{n:04d}.json' for n in sorted(q['pdf_pages'])]
                if all(p.exists() for p in paths):
                    used.extend(paths);second=compare_text(question_text(q),'\n'.join(json.loads(p.read_text(encoding='utf-8'))['text'] for p in paths))
            final=max([first]+([second] if second else []),key=lambda c:(strict_supported(c),c['ordered_token_agreement'] or 0))
            old.update(initial=first,second_pass=second,final=final,pdf_pages=q['pdf_pages'],repair_recheck='retained_source_ocr_against_current_target')
        comparisons.append(old)
    queue=[{'kind':'source_ocr_disagreement',**c} for c in comparisons if not strict_supported(c['final'])]
    summary={'records':len(active),'original_records_retained':len(rows),'changed_records':len(changed),'inactive_false_candidates':len(inactive),'repairs_by_rule':dict(Counter(l['rule'] for l in logs)),'structural_findings':dict(Counter(f['kind'] for f in structural)),'ocr_exceptions':len(queue),'strictly_supported':len(comparisons)-len(queue),'abstentions':len(abstentions),'automated_gate':'NEEDS_AUTOMATED_REPAIR' if queue or structural or abstentions else 'PASS','status':'machine_proposals_unreviewed'}
    files={'questions.jsonl':active,'passages.jsonl':passages,'original_records.jsonl':rows,'repairs.jsonl':logs,'id_dispositions.jsonl':dispositions,'abstentions.jsonl':abstentions,'structural_findings.jsonl':structural,'comparisons.jsonl':comparisons,'automatic_repair_queue.jsonl':queue+structural+abstentions,'summary.json':summary,'manifest.json':{'inputs':{str(p):sha(p) for p in inputs+used}}}
    write_new_run(args.output,files)
    page='<!doctype html><meta charset="utf-8"><title>Source recovery</title><style>body{max-width:1100px;margin:30px auto;font:16px system-ui}pre{white-space:pre-wrap}</style><h1>Source recovery proposals</h1><p>Machine proposals, not human validation. Originals, dispositions, abstentions and unresolved flags are retained.</p><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre>'
    for log in logs:page+='<details><summary>'+html.escape(log['question_id']+' | '+log['rule'])+'</summary><pre>'+html.escape(json.dumps(log,ensure_ascii=False,indent=2))+'</pre></details>'
    (args.output/'report.html').write_text(page,encoding='utf-8')
    manifest=json.loads((args.output/'manifest.json').read_text());manifest['outputs']={p.name:sha(p) for p in args.output.iterdir() if p.name!='manifest.json'}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
