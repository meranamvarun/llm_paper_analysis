"""Local automated quality checks and source OCR corroboration; no human gate."""
import argparse
import concurrent.futures
from collections import Counter, defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
import hashlib
import json
import re
import unicodedata
from pathlib import Path

from .run import ocr_page

VERSION = '0.1.0'
NEGATIONS = {'no','not','never','except','neither','nor','without','incorrect','false'}
TOKEN = re.compile(r"[^\W_]+(?:['\u2019][^\W_]+)*", re.UNICODE)


def tokens(text):
    text=unicodedata.normalize('NFKC',text)
    text=re.sub(r"(?<=\w)[\u2018\u2019\u201b\u201f\uff07](?=\w)","'",text)
    return [m.group().casefold() for m in TOKEN.finditer(text)]


def compare_text(target, source):
    wanted, observed = tokens(target), tokens(source)
    matches = sum(b.size for b in SequenceMatcher(None, wanted, observed, autojunk=False).get_matching_blocks())
    a, b = Counter(wanted), Counter(observed)
    missing = list((Counter(t for t in wanted if any(c.isdigit() for c in t)) - b).elements())
    negations = {t: {'target': a[t], 'ocr': b[t]} for t in sorted(NEGATIONS) if a[t] != b[t]}
    agreement = matches / len(wanted) if wanted else None
    status = ('EMPTY_TARGET' if not wanted else 'NO_OCR_EVIDENCE' if not observed else
              'SUPPORTED' if agreement >= .98 and not missing and not negations else 'OCR_DISAGREEMENT')
    return {'status': status, 'ordered_token_agreement': agreement, 'target_tokens': len(wanted),
            'ocr_tokens': len(observed), 'ordered_matching_tokens': matches,
            'missing_numbers': missing, 'negation_disagreements': negations,
            'measurement': 'lexical_support_against_machine_OCR_not_accuracy'}


def structural_checks(questions, passages, config):
    findings = []
    papers = {p['paper_id']: p for p in config['papers']}
    passage_ids = {p['passage_id'] for p in passages}
    ids, groups = Counter(q['question_id'] for q in questions), defaultdict(list)
    for key, count in ids.items():
        if count > 1:
            findings.append({'kind':'duplicate_id','record_id':key,'count':count,'severity':'error'})
    for q in questions:
        def flag(kind, **extra):
            findings.append({'kind':kind,'record_id':q['question_id'],'year_label':q['year_label'],
                             'pdf_pages':q.get('pdf_pages',[]),'severity':'error',**extra})
        paper = papers.get(q['paper_id'])
        if not paper:
            flag('unknown_paper')
            continue
        groups[q['paper_id']].append(q)
        if not q.get('stem','').strip():
            flag('empty_stem')
        if q['format'] == 'mcq' and [o['label'] for o in q['options']] != list('ABCD'):
            flag('option_structure', labels=[o['label'] for o in q['options']])
        if any(not o['text'].strip() for o in q['options']):
            flag('empty_option')
        if q.get('source_hash') != config['source_sha256']:
            flag('source_hash_mismatch')
        if q.get('passage_id') and q['passage_id'] not in passage_ids:
            flag('passage_reference')
        if paper.get('passage_format') and q['format']=='mcq' and not q.get('passage_id'):
            flag('passage_link_missing')
        if not q.get('evidence'):
            flag('source_evidence_missing')
        for e in q.get('evidence',[]):
            box = e.get('bbox',[])
            if (len(box)!=4 or box[2]<=box[0] or box[3]<=box[1]
                    or not any(lo<=e['pdf_page']<=hi for lo,hi in paper['body_ranges'])
                    or e['pdf_page'] not in q.get('pdf_pages',[])):
                flag('invalid_source_anchor', evidence=e)
    for paper_id, group in groups.items():
        paper = papers[paper_id]
        mcqs = [q for q in group if q['format']=='mcq']
        seen = defaultdict(list)
        for q in mcqs:
            seen[(q['section_id'],q['printed_question_number'])].append(q['question_id'])
        for (section, number), values in seen.items():
            if len(values)>1:
                findings.append({'kind':'duplicate_number','paper_id':paper_id,'year_label':paper['year_label'],
                                 'section_id':section,'number':number,'record_ids':values,
                                 'severity':'warning' if section=='unknown' else 'error',
                                 'note':'Unknown-section resets remain ambiguous' if section=='unknown' else None})
        expected = paper.get('expected_mcqs')
        if expected:
            numbers = {int(q['printed_question_number']) for q in mcqs}
            missing = sorted(set(range(1,expected+1))-numbers)
            outside = sorted(numbers-set(range(1,expected+1)))
            if missing:
                findings.append({'kind':'missing_number','paper_id':paper_id,'year_label':paper['year_label'],
                                 'numbers':missing,'severity':'error'})
            if outside:
                findings.append({'kind':'out_of_range_number','paper_id':paper_id,'year_label':paper['year_label'],
                                 'numbers':outside,'severity':'error'})
            if len(mcqs)!=expected:
                findings.append({'kind':'configured_count_mismatch','paper_id':paper_id,
                                 'year_label':paper['year_label'],'observed':len(mcqs),
                                 'expected':expected,'severity':'error'})
    return findings


def aggregate_gate(structural, comparisons):
    if not comparisons:
        return 'NOT_RUN'
    if any(f.get('severity','error')=='error' for f in structural) or any(c['status']!='SUPPORTED' for c in comparisons):
        return 'NEEDS_AUTOMATED_REPAIR'
    return 'PASS'


def question_text(q):
    return q['stem']+'\n'+'\n'.join(o.get('raw_label',o['label'])+' '+o['text'] for o in q['options'])


def region_text(q, pages):
    parts = []
    for n in sorted(q['pdf_pages']):
        page = pages.get(n,{})
        boxes = [e['bbox'] for e in q['evidence'] if e['pdf_page']==n]
        if not boxes:
            continue
        top, bottom = min(b[1] for b in boxes)-2, max(b[3] for b in boxes)+2
        words = [w for w in page.get('ocr_words',[]) if top <= (w['top']+w['bottom'])/2 <= bottom]
        # Keep OCR's own line order within its block; use geometry for page ordering.
        from .run import word_lines
        parts.extend(line['text'] for line in word_lines(words))
    return '\n'.join(parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--questions', type=Path, required=True)
    parser.add_argument('--passages', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=Path('extraction/papers.json'))
    parser.add_argument('--source', type=Path, default=Path('question_paper (1).pdf'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tesseract', default=r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if args.workers<1:
        parser.error('Positive workers required')
    args.output.mkdir(parents=True, exist_ok=False)
    read = lambda p: [json.loads(s) for s in p.read_text(encoding='utf-8-sig').splitlines() if s.strip()]
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    inputs = {str(p):sha(p) for p in [args.questions,args.passages,args.config,args.source,Path(__file__)]}
    config = json.loads(args.config.read_text(encoding='utf-8'))
    if sha(args.source)!=config['source_sha256']:
        raise ValueError('Source does not match configuration')
    questions = [q for q in read(args.questions) if 2016<=q['year_label']<=2026]
    passages = read(args.passages)
    structural = structural_checks(questions,passages,config)
    numbers = sorted({n for p in config['papers'] if 2016<=p['year_label']<=2026
                      for lo,hi in p['body_ranges'] for n in range(lo,hi+1)})
    page_folder = args.output/'page_ocr'
    page_folder.mkdir()
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(str(args.source))
    futures, pages = {}, {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for n in numbers:
            page = pdf[n-1]
            width,height = page.get_width(),page.get_height()
            image = page.render(scale=180/72).to_pil().convert('RGB')
            path = page_folder/f'p{n:04d}.png'
            image.save(path)
            page.close()
            futures[executor.submit(ocr_page,n,path,args.tesseract,180,
                        {'pdf_page':n,'width':width,'height':height},page_folder/f'p{n:04d}.json',6)] = n
        for future in concurrent.futures.as_completed(futures):
            n = futures[future]
            pages[n] = future.result()
            if len(pages)%20==0 or len(pages)==len(numbers):
                print(f'Source OCR {len(pages)}/{len(numbers)} pages',flush=True)
    comparisons = []
    for q in questions:
        text = region_text(q,pages)
        comparison = compare_text(question_text(q),text)
        comparisons.append({'question_id':q['question_id'],'year_label':q['year_label'],
                            'pdf_pages':q['pdf_pages'],'initial':comparison,'final':comparison,
                            'second_pass':None})
    # A tighter crop at higher resolution supplies another machine observation.
    crop_folder = args.output/'crop_ocr'
    crop_folder.mkdir()
    tasks = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        for i,(q,c) in enumerate(zip(questions,comparisons)):
            if c['initial']['status']=='SUPPORTED':
                continue
            for n in q['pdf_pages']:
                boxes = [e['bbox'] for e in q['evidence'] if e['pdf_page']==n]
                if not boxes:
                    continue
                page = pdf[n-1]
                image = page.render(scale=240/72).to_pil().convert('RGB')
                top=max(0,min(b[1] for b in boxes)-3)
                bottom=min(page.get_height(),max(b[3] for b in boxes)+3)
                crop=image.crop((0,int(top*240/72),image.width,int(bottom*240/72)))
                path=crop_folder/f'q{i:04d}-p{n:04d}.png'
                crop.save(path)
                page.close()
                future=executor.submit(ocr_page,n,path,args.tesseract,240,
                          {'pdf_page':n,'crop_top':top},path.with_suffix('.json'),6)
                tasks[future]=(i,n)
        cropped=defaultdict(list)
        for count,future in enumerate(concurrent.futures.as_completed(tasks),1):
            i,n=tasks[future]
            result=future.result()
            cropped[i].append((n,result['text']))
            if count%40==0 or count==len(tasks):
                print(f'Targeted crop OCR {count}/{len(tasks)} regions',flush=True)
    pdf.close()
    for i,parts in cropped.items():
        text='\n'.join(t for _,t in sorted(parts))
        second=compare_text(question_text(questions[i]),text)
        comparisons[i]['second_pass']=second
        first=comparisons[i]['initial']
        # Preserve both disagreements; final is the best machine support, not truth.
        comparisons[i]['final']=max([first,second],key=lambda c:(c['status']=='SUPPORTED',c['ordered_token_agreement'] or 0))
    finals=[c['final'] for c in comparisons]
    represented={n for q in questions for n in q['pdf_pages']}
    summary={'version':VERSION,'date':datetime.now(timezone.utc).isoformat(),'workflow':'automated_no_human_requirement',
             'questions_checked':len(questions),'source_body_pages_ocr':len(numbers),
             'body_pages_without_question_evidence':sorted(set(numbers)-represented),
             'structural_findings':dict(Counter(f['kind'] for f in structural)),
             'ocr_status_counts':dict(Counter(c['status'] for c in finals)),
             'initial_supported':sum(c['initial']['status']=='SUPPORTED' for c in comparisons),
             'targeted_second_pass_questions':sum(c['second_pass'] is not None for c in comparisons),
             'automated_gate':aggregate_gate(structural,finals),
             'integrity_gate':'PASS' if all(sha(Path(p))==h for p,h in inputs.items()) else 'FAIL',
             'human_benchmark_required':False,'empirical_accuracy':None,
             'limits':['OCR agreement is corroboration, not a gold-standard error rate',
                       'Shared OCR-engine failures and incorrect source-region segmentation can survive',
                       'Configured counts and candidate source coverage remain unverified']}
    queue=[{'kind':'question_ocr_disagreement',**c} for c in comparisons if c['final']['status']!='SUPPORTED']+structural
    save=lambda name,value:(args.output/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    save('summary.json',summary)
    for name,rows in [('comparisons.jsonl',comparisons),('structural_findings.jsonl',structural),('automatic_repair_queue.jsonl',queue)]:
        (args.output/name).write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in rows),encoding='utf-8')
    save('manifest.json',{'inputs':inputs,'settings':{'full_page_dpi':180,'crop_dpi':240,'psm':6,'workers':args.workers},
                          'outputs':{str(p.relative_to(args.output)):sha(p) for p in args.output.rglob('*') if p.is_file()}})
    print(json.dumps(summary,indent=2),flush=True)


if __name__=='__main__':
    main()
