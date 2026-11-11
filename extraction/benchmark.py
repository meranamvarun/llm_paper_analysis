"""Score explicit human-adjudicated alignments; absent gold never implies accuracy."""
import argparse
import json
import re
import unicodedata
from pathlib import Path


def edit_distance(a, b):
    if len(a) < len(b):
        a, b = b, a
    previous = list(range(len(b)+1))
    for i, left in enumerate(a, 1):
        row = [i]
        for j, right in enumerate(b, 1):
            row.append(min(row[-1]+1, previous[j]+1, previous[j-1]+(left != right)))
        previous = row
    return previous[-1]


def normalize(text):
    return ' '.join(unicodedata.normalize('NFC', text).split())


def fields(item):
    if item is None:
        return {}
    return {'stem': normalize(item['stem']), **{
        f'option[{i}]': normalize(o['label']+' '+o['text']) for i, o in enumerate(item['options'])}}


def score_reference(predictions, references, _include_strata=True):
    def index(rows):
        result = {r['alignment_id']: r for r in rows}
        if len(result) != len(rows):
            raise ValueError('Duplicate alignment ID')
        return result
    pred, gold = index(predictions), index(references)
    for r in references:
        reviewers = r.get('reviewers', [])
        if (r.get('gold_status') != 'adjudicated' or len(set(reviewers)) < 2
                or not all(reviewers) or not r.get('adjudicator')):
            raise ValueError('Reference requires two independent reviewers and adjudication')
    report = {'gate': 'NOT_ASSESSED', 'cer': None, 'wer': None,
              'reference_items': len(gold), 'prediction_items': len(pred),
              'missing_items': sorted(gold.keys()-pred.keys()), 'extra_items': sorted(pred.keys()-gold.keys()),
              'character_edits': 0, 'reference_characters': 0, 'word_edits': 0, 'reference_words': 0,
              'exact_fields': 0, 'reference_fields': 0, 'exact_items': 0,
              'fully_correct_options': 0, 'critical_token_errors': 0, 'critical_tokens_checked': 0}
    if not gold:
        return report
    for key in gold.keys() | pred.keys():
        expected, actual = fields(gold.get(key)), fields(pred.get(key))
        for field in expected.keys() | actual.keys():
            ref, value = expected.get(field, ''), actual.get(field, '')
            report['character_edits'] += edit_distance(ref, value)
            report['reference_characters'] += len(ref)
            report['word_edits'] += edit_distance(ref.split(), value.split())
            report['reference_words'] += len(ref.split())
            if field in expected:
                report['reference_fields'] += 1
                report['exact_fields'] += int(field in actual and value == ref)
        if key in gold:
            report['exact_items'] += int(key in pred and expected == actual)
            report['fully_correct_options'] += int(key in pred and
                {k: v for k, v in expected.items() if k != 'stem'} ==
                {k: v for k, v in actual.items() if k != 'stem'})
            expected_text = '\n'.join(expected.values())
            actual_text = '\n'.join(actual.values())
            for token in gold[key].get('critical_tokens', []):
                pattern = r'(?<!\w)' + re.escape(token) + r'(?!\w)'
                required = len(re.findall(pattern, expected_text))
                if not required:
                    raise ValueError('Critical token not present in reference')
                report['critical_tokens_checked'] += 1
                report['critical_token_errors'] += int(required != len(re.findall(pattern, actual_text)))
    for rate, numerator, denominator in [('cer','character_edits','reference_characters'), ('wer','word_edits','reference_words')]:
        report[rate] = report[numerator] / report[denominator] if report[denominator] else None
    matched = len(gold.keys() & pred.keys())
    report['question_precision'] = matched / len(pred) if pred else 0
    report['question_recall'] = matched / len(gold)
    report['option_accuracy'] = report['fully_correct_options'] / len(gold)
    text_pass = (report['cer'] is not None and report['cer'] <= .005
                 and report['wer'] is not None and report['wer'] <= .01
                 and report['question_precision'] >= .99 and report['question_recall'] >= .99
                 and report['option_accuracy'] >= .99 and not report['critical_token_errors']
                 and not report['missing_items'] and not report['extra_items'])
    report['text_gate'] = 'PASS' if text_pass else 'FAIL'
    report['gate'] = 'NOT_ASSESSED' if text_pass else 'FAIL'
    report['remaining_gates'] = ['page_boundary_split_merge_audit', 'passage_links',
                                 'all_strata', 'critical_token_annotation_coverage', 'uncertainty_analysis']
    if _include_strata:
        strata = {r.get('stratum_id') for r in references} - {None}
        report['stratum_reports'] = {}
        for stratum in sorted(strata):
            refs = [r for r in references if r.get('stratum_id') == stratum]
            values = [r for r in predictions if gold.get(r['alignment_id'], r).get('stratum_id') == stratum]
            report['stratum_reports'][stratum] = score_reference(values, refs, _include_strata=False)
        report['strata_status'] = 'reported' if strata else 'NOT_ANNOTATED'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--predictions', type=Path, required=True)
    parser.add_argument('--references', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    read = lambda p: [json.loads(line) for line in p.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
    result = score_reference(read(args.predictions), read(args.references))
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)


if __name__ == '__main__':
    main()
