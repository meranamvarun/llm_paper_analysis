"""Recover literal question boundaries and retain all false-candidate lineage."""
import argparse
from collections import Counter
import copy
import html
import json
from pathlib import Path
import re
from .recovery import numbered_source_blocks,letter_parts,transfer_cleaning,flat
from .recovery_run import read,sha,anchor,ev
from .run import body_page
from .automated_quality import structural_checks,compare_text,region_text,question_text
from .strict_support import strict_supported
from .quality import write_new_run


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    run=Path('data/automated_quality/20261112/source_recovery_v2');ocrroot=Path('data/automated_quality/20261111/run_v1')
    pagepath=Path('data/extraction/runs/20261110T043421397159Z/pages.jsonl')
    cleaningpath=Path('data/text_quality/20261111/cleaned_proposed_v2/cleaned_questions.jsonl')
    cleaning_reference={q['question_id']:q for q in read(cleaningpath)}
    rows=read(run/'questions.jsonl');byid={q['question_id']:q for q in rows};passages=read(run/'passages.jsonl');result=copy.deepcopy(rows)
    config=json.loads(Path('extraction/papers.json').read_text());pages={p['pdf_page']:p for p in read(pagepath)}
    logs=[];dispositions=[];inactive=set();abstentions=[];changed=set();added=[]
    for paper in config['papers']:
        year=paper['year_label']
        if year not in [2022,2023,2024,2025,2026,2018]:continue
        lines=[]
        for lo,hi in paper['body_ranges']:
            for n in range(lo,hi+1):
                page=body_page(pages[n],paper)
                for l in page['lines']:
                    if re.fullmatch(r'(?:PG|af|[*#]+)',l['text'].strip(),re.I):continue
                    if l['bbox'][1]>page['height']*.88 and re.fullmatch(r'[\d\W_M]+',l['text']):continue
                    lines.append({**l,'pdf_page':n})
        expected=50 if year==2018 else 120
        blocks=numbered_source_blocks(lines,expected,blocks=3 if year==2018 else 1)
        if not blocks:
            abstentions.append({'year_label':year,'reason':'literal_source_numbering_incomplete'});continue
        order={anchor(l):i for i,l in enumerate(lines)}
        papass=[p for p in passages if p['paper_id']==paper['paper_id']]
        pastarts=sorted((order[anchor(p['evidence'][0])],p) for p in papass if anchor(p['evidence'][0]) in order)
        # Rebuild incomplete passage bodies only within source-anchored boundaries.
        for start,p in pastarts:
            stop=next((b['start'] for b in blocks if b['start']>start),len(lines))
            body=lines[start:stop]
            if body:p['raw_text']='\n'.join(l['text'] for l in body);p['evidence']=ev(body)
        paperqs=[q for q in result if q['year_label']==year]
        assigned=set()
        for b in blocks:
            start,stop=b['start'],b['stop']
            cut=next((i for i,p in pastarts if start<i<stop),stop)
            content=lines[start:cut];anchors={anchor(l) for l in content}
            inside=[q for q in paperqs if anchor(q['evidence'][0]) in anchors]
            exact=[q for q in inside if anchor(q['evidence'][0])==anchor(content[0])]
            q=exact[0] if len(exact)==1 else inside[0] if len(inside)==1 else None
            proposal=letter_parts('\n'.join(l['text'] for l in content),allow_bare=year==2018)
            if q is None:
                omitted=year==2018 and re.search(r'Omitted for Valuation',content[0]['text'],re.I)
                if inside or (not proposal and not omitted):
                    abstentions.append({'year_label':year,'number':b['number'],'reason':'ambiguous_new_boundary_or_options'});continue
                if omitted:proposal=(content[0]['text'],[])
                template=paperqs[0];q={k:copy.deepcopy(v) for k,v in template.items() if k not in {'accepted_correction','original_stem','original_options','text_changed','text_cleanup_status','text_cleanup_version'}}
                first=content[0];q.update(question_id=f"{config['source_sha256']}:p{first['pdf_page']:04d}:{first['line_id']}:question",raw_text='\n'.join(l['text'] for l in content),stem=proposal[0],options=proposal[1],review_status='unreviewed',issues=['source_boundary_recovery_proposal'],corrected_text=None,inline_answer_raw=None)
                if omitted:q.update(format='omitted_for_valuation',options=[],source_omission_status='explicitly_omitted_in_source')
                added.append(q);result.append(q)
                logs.append({'question_id':q['question_id'],'rule':'new_source_anchored_question','before':None,'after':copy.deepcopy(q),'status':'machine_proposal_unreviewed'})
            updates={'printed_question_number':str(b['number']),'evidence':ev(content),'pdf_pages':sorted({l['pdf_page'] for l in content})}
            if year==2018:
                first=lines[next(x['start'] for x in blocks if x['block']==b['block'])]
                updates['section_id']=f"source-numbering-block@p{first['pdf_page']:04d}:{first['line_id']}"
            priorpass=[p for i,p in pastarts if i<start]
            if paper.get('passage_format') and priorpass:updates['passage_id']=priorpass[-1]['passage_id']
            if proposal:
                transferred=transfer_cleaning(*proposal,cleaning_reference.get(q['question_id'],q))
                if transferred:updates.update(stem=transferred[0],options=transferred[1])
                else:abstentions.append({'question_id':q['question_id'],'reason':'prior_cleaning_transfer_failed_for_source_boundary'})
            else:
                if [o['label'] for o in q['options']]!=list('ABCD') and q['format']=='mcq':
                    abstentions.append({'question_id':q['question_id'],'reason':'source_primary_options_unresolved'})
            # Accepted snapshots remain frozen. New proposals may extend a literal
            # accepted stem and repair options never covered by an alias decision.
            if q.get('accepted_correction'):
                for k in list(updates):
                    if k not in {'stem','options','section_id'}:updates.pop(k)
                if 'stem' in updates:
                    if flat(updates['stem'])==flat(q['stem']):updates.pop('stem')
                    elif flat(q['stem']) not in flat(updates['stem']):
                        updates.pop('stem')
            updates={k:v for k,v in updates.items() if q.get(k)!=v}
            if updates:
                logs.append({'question_id':q['question_id'],'rule':'literal_source_boundaries_and_primary_options','before':{k:copy.deepcopy(q.get(k)) for k in updates},'after':copy.deepcopy(updates),'source_evidence':ev(content),'status':'machine_proposal_unreviewed'})
                q.update(updates);changed.add(q['question_id'])
            assigned.add(q['question_id'])
            for extra in inside:
                if extra['question_id']!=q['question_id']:
                    inactive.add(extra['question_id']);dispositions.append({'question_id':extra['question_id'],'disposition':'citation_fragment_within_source_question','target_question_id':q['question_id'],'original_record':byid[extra['question_id']],'status':'machine_proposal_unreviewed'})
        # Remaining candidates begin within a source-identified passage.
        for q in paperqs:
            if q['question_id'] in assigned or q['question_id'] in inactive:continue
            a=anchor(q['evidence'][0])
            targets=[p for p in papass if a in {anchor(e) for e in p['evidence']}]
            if len(targets)==1:
                inactive.add(q['question_id']);dispositions.append({'question_id':q['question_id'],'disposition':'numbered_fragment_within_source_passage','target_passage_id':targets[0]['passage_id'],'original_record':byid[q['question_id']],'status':'machine_proposal_unreviewed'})
            else:
                originalanchors={anchor(e) for e in q['evidence']}
                scores=[(len(originalanchors & {anchor(e) for e in p['evidence']}),p) for p in papass]
                scores.sort(key=lambda x:x[0],reverse=True)
                firsttext=pages[q['evidence'][0]['pdf_page']]['lines']
                sourcefirst=next((l['text'] for l in firsttext if l['line_id']==q['evidence'][0]['line_id']),'')
                if scores and scores[0][0]>0 and (len(scores)==1 or scores[0][0]>scores[1][0]) and re.fullmatch(r'[\d\W_MPG]+',sourcefirst):
                    inactive.add(q['question_id']);dispositions.append({'question_id':q['question_id'],'disposition':'page_footer_and_passage_continuation','target_passage_id':scores[0][1]['passage_id'],'original_record':byid[q['question_id']],'status':'machine_proposal_unreviewed'})
                else:abstentions.append({'question_id':q['question_id'],'reason':'unassigned_original_candidate'})
    active=[q for q in result if q['question_id'] not in inactive]
    findings=structural_checks(active,passages,config)
    oldcomp={c['question_id']:c for c in read(run/'comparisons.jsonl')};ocrpages={};used=[];comparisons=[]
    for q in active:
        previous=byid.get(q['question_id'])
        if previous and question_text(q)==question_text(previous) and q['evidence']==previous['evidence']:
            comparisons.append(oldcomp[q['question_id']]);continue
        for n in q['pdf_pages']:
            if n not in ocrpages:
                path=ocrroot/'page_ocr'/f'p{n:04d}.json';used.append(path);ocrpages[n]=json.loads(path.read_text(encoding='utf-8'))
        check=compare_text(question_text(q),region_text(q,ocrpages))
        comparisons.append({'question_id':q['question_id'],'year_label':q['year_label'],'pdf_pages':q['pdf_pages'],'initial':check,'final':check,'second_pass':None,'repair_recheck':'current_source_region_against_frozen_full_page_OCR'})
    queue=[{'kind':'source_ocr_disagreement',**c} for c in comparisons if not strict_supported(c['final'])]
    summary={'records':len(active),'added_source_questions':len(added),'inactive_false_candidates':len(inactive),'changed_records':len(changed),'structural_findings':dict(Counter(f['kind'] for f in findings)),'abstentions':len(abstentions),'ocr_exceptions':len(queue),'strictly_supported':len(active)-len(queue),'automated_gate':'NEEDS_AUTOMATED_REPAIR' if queue or findings or abstentions else 'PASS','status':'machine_proposals_unreviewed'}
    inputs=[cleaningpath,run/'questions.jsonl',run/'passages.jsonl',run/'manifest.json',pagepath,Path('extraction/papers.json'),Path(__file__),Path('extraction/recovery.py')]+used
    files={'questions.jsonl':active,'passages.jsonl':passages,'original_records.jsonl':rows,'accepted_records_snapshot.jsonl':[q for q in rows if q.get('accepted_correction')],'repairs.jsonl':logs,'id_dispositions.jsonl':dispositions,'abstentions.jsonl':abstentions,'structural_findings.jsonl':findings,'comparisons.jsonl':comparisons,'automatic_repair_queue.jsonl':queue+findings+abstentions,'summary.json':summary,'manifest.json':{'inputs':{str(p):sha(p) for p in inputs}}}
    write_new_run(args.output,files)
    page='<!doctype html><meta charset="utf-8"><title>Boundary recovery</title><style>body{max-width:1100px;margin:30px auto;font:16px system-ui}pre{white-space:pre-wrap}</style><h1>Boundary recovery proposals</h1><p>Original and accepted snapshots remain frozen. All new boundaries are machine proposals.</p><pre>'+html.escape(json.dumps(summary,indent=2))+'</pre>'
    for log in logs:page+='<details><summary>'+html.escape(log['question_id'])+'</summary><pre>'+html.escape(json.dumps(log,ensure_ascii=False,indent=2))+'</pre></details>'
    (args.output/'report.html').write_text(page,encoding='utf-8')
    manifest=json.loads((args.output/'manifest.json').read_text());manifest['outputs']={p.name:sha(p) for p in args.output.iterdir() if p.name!='manifest.json'};(args.output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
