"""Run with python -m extraction.run. All corpus outputs stay under ignored data/."""
import argparse
import concurrent.futures
import csv
import hashlib
import html
import importlib.metadata
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import pdfplumber
import pypdfium2 as pdfium

from .pipeline import VERSION, needs_ocr, parse_paper, parse_key_lines


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def jsonl(path, rows):
    path.write_text(''.join(json.dumps(x, ensure_ascii=False)+'\n' for x in rows), encoding='utf-8')


def word_lines(words):
    """Cluster words by baseline; preserve bounding boxes and word evidence."""
    groups = []
    for w in sorted(words, key=lambda w: (w['top'], w['x0'])):
        group = next((g for g in reversed(groups[-4:]) if abs(g[0]['top']-w['top']) <= 3), None)
        if group is None:
            groups.append([w])
        else:
            group.append(w)
    result = []
    for i, group in enumerate(groups):
        group.sort(key=lambda w: w['x0'])
        result.append({'line_id': f'l{i:04d}', 'text': ' '.join(w['text'] for w in group),
                       'bbox': [min(w['x0'] for w in group), min(w['top'] for w in group),
                                max(w['x1'] for w in group), max(w['bottom'] for w in group)]})
    return result


def ocr_page(n, image_path, tesseract, dpi, native, cache_file, psm=3):
    try:
        proc = subprocess.run([tesseract, str(image_path), 'stdout', '-l', 'eng', '--dpi', str(dpi),
                               '--psm', str(psm), 'tsv'], capture_output=True, timeout=180,
                              env={**os.environ, 'OMP_THREAD_LIMIT': '1'})
        tsv = proc.stdout.decode('utf-8', errors='replace')
        image_path.with_suffix(f'.psm{psm}.tsv').write_text(tsv, encoding='utf-8')
        image_path.with_suffix(f'.psm{psm}.stderr.txt').write_bytes(proc.stderr)
        if proc.returncode:
            raise RuntimeError(f'Tesseract exit {proc.returncode}')
        scale = 72 / dpi
        words = []
        for row in csv.DictReader(io.StringIO(tsv), delimiter='\t', quoting=csv.QUOTE_NONE):
            if row.get('level') != '5' or not row.get('text', '').strip():
                continue
            x, y, w, h = (int(row[k]) * scale for k in ('left', 'top', 'width', 'height'))
            words.append({'text': row['text'], 'x0': x, 'top': y, 'x1': x+w, 'bottom': y+h,
                          'confidence': float(row['conf']), 'ocr_block': row['block_num'],
                          'ocr_paragraph': row['par_num'], 'ocr_line': row['line_num']})
        # These configured paper bodies are single-column. Geometry reunites the
        # number gutter with its stem when Tesseract assigns separate blocks.
        lines = word_lines(words)
        text = '\n'.join(x['text'] for x in lines)
        issues = ['ocr_requires_visual_review']
        if not words:
            issues.append('no_ocr_text_blankness_unverified')
        if any(w['confidence'] < 60 for w in words):
            issues.append('low_confidence_ocr_words')
        result = {**native, 'method': f'tesseract_eng_psm{psm}', 'ocr_psm': psm, 'lines': lines, 'text': text,
                  'ocr_words': words, 'issues': issues}
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as exc:
        result = {**native, 'method': 'unresolved', 'lines': [], 'text': '',
                  'issues': ['ocr_failed', str(exc)]}
    save(image_path.with_suffix(f'.ocr-psm{psm}.json'), result)
    save(cache_file, result)
    return result


def body_page(page, paper):
    """Header filtering affects proposals only; native and OCR data stay untouched."""
    if not any(a <= page['pdf_page'] <= b for a, b in paper['body_ranges']):
        return None
    lines = []
    for line in page['lines']:
        text = line['text'].strip()
        y0, y1 = line['bbox'][1], line['bbox'][3]
        header = y0 < 60 and (re.match(r'^(?:Page \d+ of|[A-Z*#ρ ]*PG\b|PG\b|CLAT\b)', text, re.I)
                                  or re.fullmatch(r'[\d\W]+', text))
        footer = y1 > page['height']-55 and bool(re.fullmatch(r'[\d\W]+', text) or re.match(r'^Page \d+ of \d+$', text, re.I))
        if not (header or footer):
            lines.append(line)
    hint = 'essay' if any(a <= page['pdf_page'] <= b for a,b in paper.get('essay_ranges', [])) else None
    return {**page, 'lines': lines, 'format_hint': hint}


def validate(pages, questions, passages, keys, config, source_hash):
    ids = [q['question_id'] for q in questions]
    assert len(ids) == len(set(ids)), 'Duplicate question IDs'
    by_page = {p['pdf_page']: p for p in pages}
    by_paper = {p['paper_id']: p for p in config['papers']}
    passage_ids = {p['passage_id'] for p in passages}
    for q in questions:
        assert q['source_hash'] == source_hash and q['review_status'] == 'unreviewed'
        assert q['passage_id'] is None or q['passage_id'] in passage_ids
        paper = by_paper[q['paper_id']]
        assert all(paper['pdf_start'] <= n <= paper['pdf_end'] for n in q['pdf_pages'])
        refs = []
        for e in q['evidence']:
            line = next(x for x in by_page[e['pdf_page']]['lines'] if x['line_id'] == e['line_id'])
            assert e['bbox'] == line['bbox']
            refs.append(line['text'])
        assert q['raw_text'] == '\n'.join(refs), 'Raw evidence round-trip failed'
    assert all(k['verification_status'] == 'unverified' for k in keys)


def previews(source, run, pages, questions, limit):
    """Bounded, deterministic sample across years; not a coding pilot."""
    folder = run/'previews'
    folder.mkdir()
    cards = []
    pdf = pdfium.PdfDocument(str(source))
    selected = []
    # Include essays first so a small sample does not hide the distinct format.
    candidates = [q for q in questions if q['format'] == 'essay'][:1]
    for year in sorted({q['year_label'] for q in questions}):
        group = [q for q in questions if q['year_label'] == year]
        candidates.extend([group[0], group[-1]])
    candidates.extend(questions)
    seen = set()
    for q in candidates:
        if len(selected) >= limit:
            break
        if q['question_id'] not in seen:
            selected.append(q)
            seen.add(q['question_id'])
    for i, q in enumerate(selected):
        imgs = []
        for n in q['pdf_pages']:
            page = pdf[n-1]
            im = page.render(scale=1.5).to_pil().convert('RGB')
            boxes = [e['bbox'] for e in q['evidence'] if e['pdf_page'] == n]
            # Full width and vertical context expose OCR omissions beyond its boxes.
            box = (0, max(0, min(b[1] for b in boxes)*1.5-60),
                   im.width, min(im.height, max(b[3] for b in boxes)*1.5+60))
            name = f'q{i:04d}-p{n:04d}.jpg'
            im.crop(box).save(folder/name)
            imgs.append(f'<p>PDF page {n}</p><img src="previews/{name}" style="max-width:100%">')
            page.close()
        cards.append(f'<article><h2>{html.escape(q["question_id"])}</h2>' + ''.join(imgs) +
                     '<pre>'+html.escape(q['raw_text'])+'</pre><p>'+html.escape(', '.join(q['issues']))+'</p></article>')
    pdf.close()
    (run/'review.html').write_text('<!doctype html><meta charset="utf-8"><title>Unreviewed extraction sample</title>'
        '<style>body{max-width:1000px;margin:30px auto;font:16px sans-serif}pre{white-space:pre-wrap}article{border-top:2px solid #999;padding:20px 0}</style>'
        f'<h1>Unreviewed extraction sample</h1><p>Deterministic sample of {len(selected)} of {len(questions)} proposals across year labels and formats. '
        'Full queue: review_queue.jsonl. Source crops support review; nothing is adjudicated.</p>'+''.join(cards), encoding='utf-8')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, default=Path('question_paper (1).pdf'))
    ap.add_argument('--config', type=Path, default=Path('extraction/papers.json'))
    ap.add_argument('--output-root', type=Path, default=Path('data/extraction'))
    ap.add_argument('--tesseract', default=shutil.which('tesseract') or r'C:\Program Files\Tesseract-OCR\tesseract.exe')
    ap.add_argument('--dpi', type=int, default=300)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--preview-limit', type=int, default=30)
    args = ap.parse_args()
    if args.dpi < 72 or args.workers < 1 or args.preview_limit < 0:
        ap.error('dpi >= 72, workers >= 1 and preview-limit >= 0 required')
    source_hash = digest(args.source.read_bytes())
    config_bytes = args.config.read_bytes()
    config = json.loads(config_bytes)
    if source_hash != config['source_sha256']:
        ap.error('Source hash does not match reviewed candidate configuration')
    versions = {m: importlib.metadata.version(m) for m in ['pdfplumber', 'pypdfium2', 'pypdf']}
    tess_version = None
    if Path(args.tesseract).is_file():
        tess_version = subprocess.run([args.tesseract, '--version'], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    settings = {'source_hash': source_hash, 'versions': versions, 'dpi': args.dpi,
                'tesseract': tess_version, 'parser_version': VERSION, 'ocr_language': 'eng', 'ocr_psm': 3,
                'force_ocr_ranges': config.get('force_ocr_ranges', [])}
    cache = args.output_root/'cache'/digest(json.dumps(settings, sort_keys=True).encode())[:20]
    cache.mkdir(parents=True, exist_ok=True)
    run = args.output_root/'runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True, exist_ok=False)
    save(run/'run.json', {'status': 'running', 'settings': settings, 'config_sha256': digest(config_bytes),
                         'source_path': str(args.source.resolve()),
                         'code_sha256': {p.name:digest(p.read_bytes()) for p in [Path(__file__), Path(__file__).with_name('pipeline.py')]},
                         'python_version': sys.version,
                         'line_reconstruction': 'geometry-v1; configured single-column bodies',
                         'ai_assistance': 'Codex implementation; no model inference in extraction'})
    (run/'papers.json').write_bytes(config_bytes)
    pages = []
    pending = []
    pdf_images = pdfium.PdfDocument(str(args.source))
    with pdfplumber.open(args.source) as pdf:
        for n, page in enumerate(pdf.pages, 1):
            desired_psm = next((psm for a,b,psm in config.get('ocr_psm_ranges', []) if a <= n <= b), 3)
            chosen_cache = cache/f'p{n:04d}.json'
            if chosen_cache.exists():
                cached = json.loads(chosen_cache.read_text(encoding='utf-8'))
                usable = (cached['method'].startswith('tesseract') and cached.get('ocr_psm', 3) == desired_psm)
                usable = usable or (cached['method'] == 'pdfplumber_native' and not needs_ocr(cached['text']))
                if usable:
                    if cached['method'].startswith('tesseract'):
                        cached['lines'] = word_lines(cached['ocr_words'])
                        cached['text'] = '\n'.join(x['text'] for x in cached['lines'])
                    pages.append(cached)
                    continue
            words = page.extract_words(expand_ligatures=False)
            lines = word_lines(words)
            native = {'pdf_page': n, 'width': float(page.width), 'height': float(page.height),
                      'method': 'pdfplumber_native', 'text': '\n'.join(x['text'] for x in lines),
                      'lines': lines, 'native_words': words, 'issues': []}
            save(cache/f'p{n:04d}.native.json', native)
            force = any(a <= n <= b for a,b in config.get('force_ocr_ranges', []))
            if force or needs_ocr(native['text']):
                if tess_version:
                    image_path = cache/f'p{n:04d}.png'
                    image_page = pdf_images[n-1]
                    image_page.render(scale=args.dpi/72).to_pil().save(image_path)
                    image_page.close()
                    pending.append((n, image_path, native, chosen_cache, desired_psm))
                else:
                    chosen = {**native, 'method': 'unresolved', 'text': '', 'lines': [], 'issues': ['ocr_unavailable']}
                    save(chosen_cache, chosen)
                    pages.append(chosen)
            else:
                save(chosen_cache, native)
                pages.append(native)
            page.close()
            if n % 25 == 0:
                print(f'Native extraction/rendering: {n}/{len(pdf.pages)} pages', flush=True)
    pdf_images.close()
    print(f'OCR pages scheduled: {len(pending)}', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs = [pool.submit(ocr_page, n, im, args.tesseract, args.dpi, native, target, psm) for n,im,native,target,psm in pending]
        for i, job in enumerate(concurrent.futures.as_completed(jobs), 1):
            pages.append(job.result())
            if i % 10 == 0 or i == len(jobs):
                print(f'OCR complete: {i}/{len(jobs)}', flush=True)
    pages.sort(key=lambda p:p['pdf_page'])
    questions, passages, unresolved, keys, coverage = [], [], [], [], []
    for paper in config['papers']:
        body = [p for p in (body_page(p, paper) for p in pages) if p is not None]
        qs, pas, blocks = parse_paper(body, paper, source_hash)
        if paper.get('passage_format'):
            for q in qs:
                if q['format'] == 'mcq' and not q['passage_id']:
                    q['issues'].append('passage_link_unresolved')
        questions.extend(qs)
        passages.extend(pas)
        unresolved.extend(blocks)
        if paper.get('key_ranges'):
            key_pages = [p for p in pages if any(a <= p['pdf_page'] <= b for a,b in paper['key_ranges'])]
            for key in parse_key_lines(key_pages, paper['key_status']):
                keys.append({**key, 'paper_id': paper['paper_id'], 'source_hash': source_hash})
    for page in pages:
        n = page['pdf_page']
        roles = []
        for paper in config['papers']:
            if paper['pdf_start'] <= n <= paper['pdf_end']:
                roles.append({'paper_id': paper['paper_id'], 'role': 'paper'})
            if any(a <= n <= b for a,b in paper.get('key_ranges', [])):
                roles.append({'paper_id': paper['paper_id'], 'role': 'key'})
        coverage.append({'pdf_page': n, 'assignments': roles, 'issues': page['issues']})
    validate(pages, questions, passages, keys, config, source_hash)
    assert digest(args.source.read_bytes()) == source_hash, 'Source changed during run'
    queue = [{'kind': 'question', 'record_id':q['question_id'], 'issues':q['issues'], 'evidence':q['evidence']} for q in questions]
    queue += [{'kind':'page', 'pdf_page':p['pdf_page'], 'issues':p['issues']} for p in pages if p['issues']]
    queue += [{'kind':'unresolved_block', **b} for b in unresolved]
    paper_diagnostics = []
    for paper in config['papers']:
        group = [q for q in questions if q['paper_id'] == paper['paper_id'] and q['format'] == 'mcq']
        seen = {}
        for q in group:
            key = (q['section_id'], q['printed_question_number'])
            seen.setdefault(key, []).append(q['question_id'])
        duplicates = [v for v in seen.values() if len(v) > 1]
        expected = paper.get('expected_mcqs')
        observed_numbers = {int(q['printed_question_number']) for q in group}
        diagnostic = {'kind':'paper', 'paper_id':paper['paper_id'], 'year_label':paper['year_label'],
            'issues':['candidate_boundaries_require_review'], 'mcq_proposals':len(group),
            'expected_mcqs':expected, 'expected_count_source_pdf_page':paper.get('expected_count_source_pdf_page'),
            'duplicate_number_groups':duplicates,
            'missing_numbers_against_expected': sorted(set(range(1,expected+1))-observed_numbers) if expected else None}
        if duplicates:
            diagnostic['issues'].append('duplicate_numbers_within_section')
        if expected and (len(group) != expected or diagnostic['missing_numbers_against_expected']):
            diagnostic['issues'].append('expected_count_or_numbering_mismatch')
        paper_diagnostics.append(diagnostic)
    queue += paper_diagnostics
    for filename, rows in [('pages.jsonl', pages), ('questions.jsonl', questions), ('passages.jsonl', passages),
                           ('unresolved_blocks.jsonl', unresolved), ('answer_keys.jsonl', keys),
                           ('page_coverage.jsonl', coverage), ('review_queue.jsonl', queue)]:
        jsonl(run/filename, rows)
    save(run/'paper_diagnostics.json', paper_diagnostics)
    previews(args.source, run, pages, questions, args.preview_limit)
    summary = {'status': 'completed_unreviewed', 'source_hash': source_hash, 'pdf_pages':len(pages),
        'question_proposals':len(questions), 'passage_proposals':len(passages), 'key_entries':len(keys),
        'unresolved_blocks':len(unresolved), 'pages_with_issues':sum(bool(p['issues']) for p in pages),
        'unassigned_pages':[c['pdf_page'] for c in coverage if not c['assignments']],
        'by_year':{str(p['year_label']):sum(q['paper_id']==p['paper_id'] for q in questions) for p in config['papers']},
        'validation':'Unique IDs, evidence round-trip, paper boundaries, passage links, unreviewed status and unchanged source hash passed',
        'limitations':['Candidate paper/body boundaries need review', 'OCR/segmentation not human validated',
                      'Only a bounded deterministic sample has image crops', 'No automatic key-to-question joins or legal labels'],
        'cache_path':str(cache.resolve())}
    save(run/'summary.json', summary)
    metadata = json.loads((run/'run.json').read_text(encoding='utf-8'))
    save(run/'run.json', {**metadata, 'status':'completed_unreviewed'})
    save(run/'artifact_hashes.json', {p.name:digest(p.read_bytes()) for p in sorted(run.iterdir()) if p.is_file()})
    print(json.dumps({'run':str(run.resolve()), **summary}, indent=2), flush=True)


if __name__ == '__main__':
    main()
