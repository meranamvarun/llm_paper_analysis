"""Screen frozen records and freeze a stratified source-page benchmark locally."""
import argparse
import functools
import hashlib
import importlib.metadata
import json
import random
from collections import Counter
from pathlib import Path

from extraction.quality import VERSION, clean_records, normalize_text, scan_text, write_new_run
from extraction.run import body_page


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sample_pages(pages, config, seed=20261111, per_stratum=5):
    if per_stratum < 1:
        raise ValueError('Positive sample size required')
    rng = random.Random(seed)
    sample, strata = [], []
    for paper in sorted(config['papers'], key=lambda p: (p['year_label'], p['paper_id'])):
        if not 2016 <= paper['year_label'] <= 2026:
            continue
        groups = {}
        for page in pages:
            if body_page(page, paper) is not None:
                groups.setdefault(page['method'], []).append(page['pdf_page'])
        for method, population in sorted(groups.items()):
            population = sorted(set(population))
            selected = sorted(rng.sample(population, min(len(population), per_stratum)))
            stratum = f"{paper['paper_id']}:{method}"
            strata.append({'stratum_id': stratum, 'year_label': paper['year_label'], 'method': method,
                           'population_pages': population, 'sampled_pages': selected,
                           'sample_size': len(selected), 'population_size': len(population),
                           'sampling_fraction': len(selected)/len(population)})
            for page in selected:
                sample.append({'sample_id': f'page-{len(sample)+1:03d}', 'stratum_id': stratum,
                               'paper_id': paper['paper_id'], 'year_label': paper['year_label'],
                               'pdf_page': page, 'method': method, 'reviewer_a': None, 'reviewer_b': None,
                               'independent_readings_complete': False, 'adjudicator': None,
                               'reference_status': 'blank_unreviewed', 'visible_question_starts': None,
                               'continuations': None, 'split_merge_audit': None, 'passage_boundaries': None})
    return {'seed': seed, 'pages_per_stratum': per_stratum, 'strata': strata,
            'sample_pages': sample, 'status': 'frozen_before_human_annotation',
            'analysis_note': 'Disproportionate page sample; no unweighted corpus accuracy claim'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--passages', type=Path, required=True)
    parser.add_argument('--pages', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    from wordfreq import zipf_frequency
    known = functools.lru_cache(None)(lambda word: zipf_frequency(word, 'en', wordlist='large') > 0)
    read = lambda p: [json.loads(line) for line in p.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    inputs = {str(p): digest(p) for p in [args.records, args.passages, args.pages, args.config]}
    rows, changes, flags = clean_records(read(args.records), known)
    for i, flag in enumerate(flags, 1):
        flag['flag_id'] = f'flag-{i:05d}'
    scope = {r['paper_id'] for r in rows if 'text_proposal' in r}
    passage_flags = []
    for passage in read(args.passages):
        if passage['paper_id'] not in scope:
            continue
        text, _ = normalize_text(passage['raw_text'])
        for flag in scan_text(text, known):
            passage_flags.append({**flag, 'record_id': passage['passage_id'], 'field': 'raw_text',
                                  'context': text[max(0, flag['start']-65):flag['end']+65],
                                  'status': 'context_only_pending_review'})
    benchmark = sample_pages(read(args.pages), json.loads(args.config.read_text(encoding='utf-8-sig')))
    summary = {'version': VERSION, 'in_scope_questions_scanned': sum('text_proposal' in q for q in rows),
               'total_records_preserved': len(rows), 'fields_with_formatting_changes': len(changes),
               'flags': len(flags), 'flags_by_reason': dict(Counter(f['reason'] for f in flags)),
               'flagged_questions': len({f['record_id'] for f in flags}), 'passage_flags': len(passage_flags),
               'lexicon': 'wordfreq 3.1.1 English large; Zipf frequency > 0',
               'accuracy_status': 'NOT_ESTABLISHED', 'human_benchmark_gate': 'NOT_ASSESSED'}
    write_new_run(args.output, {'questions.jsonl': rows, 'changes.jsonl': changes, 'flags.jsonl': flags,
                               'passage_flags.jsonl': passage_flags, 'summary.json': summary,
                               'benchmark_sample.json': benchmark,
                               'human_reference_template.jsonl': benchmark['sample_pages']})
    if any(digest(Path(p)) != value for p, value in inputs.items()):
        raise RuntimeError('Frozen input changed')
    manifest = {'input_hashes': inputs, 'output_hashes': {p.name: digest(p) for p in args.output.iterdir()},
                'code_hashes': {str(p): digest(p) for p in [Path(__file__), Path(__file__).with_name('quality.py')]},
                'packages': {name: importlib.metadata.version(name) for name in ['wordfreq','ftfy','regex']}}
    (args.output/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
