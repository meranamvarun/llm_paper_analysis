"""Traceable formatting proposals and lexical screening; never spell-correct source."""
import copy
import json
import re
import unicodedata
from pathlib import Path

VERSION = '0.1.0'
TOKEN = re.compile(r"[^\W_]+(?:['\u2019][^\W_]+)*", re.UNICODE)
SUSPICIOUS = set('\u00ae\u00a5\u2017\u2016\u201f\u201e\u2015\u20ac\u00a2\ufffd\u00ad\u00b0\u2022')


def apply_source_reviews(rows, flags, reviews):
    result = copy.deepcopy(rows)
    records = {r['question_id']: r for r in result}
    flags_by_id = {f['flag_id']: f for f in flags}
    reviews_by_id = {r['flag_id']: r for r in reviews}
    if (len(flags_by_id) != len(flags) or len(reviews_by_id) != len(reviews)
            or flags_by_id.keys() != reviews_by_id.keys()):
        raise ValueError('Exactly one review is required per flag')
    grouped = {}
    for key, review in reviews_by_id.items():
        if review['disposition'] not in {'retain_lexical','source_supported_change','unresolved'}:
            raise ValueError('Invalid disposition')
        if review['disposition'] != 'source_supported_change':
            continue
        if (not review.get('source_checked') or not review.get('image_paths')
                or not isinstance(review.get('replacement'), str)):
            raise ValueError('Replacement requires image-based source check')
        if '\ufffd' in review['replacement'] or re.search(r'\w\?\w', review['replacement']):
            raise ValueError('Replacement contains possible encoding damage')
        flag = flags_by_id[key]
        grouped.setdefault((flag['record_id'], flag['field']), []).append((flag, review))
    logs = []
    for (record_id, field), pairs in grouped.items():
        record = records[record_id]
        proposal = record['text_proposal']
        index = None if field == 'stem' else int(re.fullmatch(r'options\[(\d+)\]\.text', field).group(1))
        original = proposal['stem'] if index is None else proposal['options'][index]['text']
        value, previous_start = original, len(original)+1
        for flag, review in sorted(pairs, key=lambda p: p[0]['start'], reverse=True):
            start, end = flag['start'], flag['end']
            if not 0 <= start < end <= len(original) or original[start:end] != flag['text'] or end > previous_start:
                raise ValueError('Stale or overlapping replacement span')
            previous_start = start
            value = value[:start] + review['replacement'] + value[end:]
            logs.append({'record_id': record_id, 'field': field, 'flag_id': flag['flag_id'],
                         'start': start, 'end': end, 'before': flag['text'], 'after': review['replacement'],
                         'review': copy.deepcopy(review), 'status': 'ai_proposal_unreviewed'})
        value, _ = normalize_text(value)
        if index is None:
            proposal['stem'] = value
        else:
            proposal['options'][index]['text'] = value
        proposal['review_status'] = 'unreviewed'
    return result, logs


def normalize_text(text):
    value = unicodedata.normalize('NFC', text)
    value = value.replace('\r\n', '\n').replace('\r', '\n')
    value = '\n'.join(re.sub(r'[^\S\n]+', ' ', line).strip() for line in value.split('\n'))
    return value, ([] if value == text else ['NFC_and_horizontal_whitespace'])


def scan_text(text, known):
    flags = []
    for match in TOKEN.finditer(text):
        word = match.group()
        reason = None
        if any(c.isalpha() for c in word) and any(c.isdigit() for c in word):
            reason = 'mixed_digit_letter'
        elif any(c.isalpha() for c in word):
            lookup = re.sub(r"['\u2019]s$", '', word, flags=re.I)
            if not known(lookup):
                reason = 'out_of_lexicon'
        if reason:
            flags.append({'start': match.start(), 'end': match.end(), 'text': word, 'reason': reason})
    for i, char in enumerate(text):
        if char in SUSPICIOUS or (unicodedata.category(char).startswith('C') and char not in '\n\r\t'):
            flags.append({'start': i, 'end': i+1, 'text': char, 'reason': 'suspicious_symbol'})
        elif char in '@#~`|*$%+=':
            flags.append({'start': i, 'end': i+1, 'text': char, 'reason': 'suspicious_ascii'})
    return sorted(flags, key=lambda f: (f['start'], f['reason']))


def clean_records(rows, known):
    result = copy.deepcopy(rows)
    changes, flags = [], []
    for record in result:
        if not 2016 <= record['year_label'] <= 2026:
            continue
        proposal = {'stem': record['stem'], 'options': copy.deepcopy(record['options']),
                    'review_status': 'unreviewed', 'version': VERSION}
        fields = [('stem', record['stem'])] + [(f'options[{i}].text', o['text']) for i, o in enumerate(record['options'])]
        for field, before in fields:
            after, operations = normalize_text(before)
            if field == 'stem':
                proposal['stem'] = after
            else:
                proposal['options'][int(re.search(r'\d+', field).group())]['text'] = after
            common = {'record_id': record['question_id'], 'year_label': record['year_label'],
                      'pdf_pages': record.get('pdf_pages', []), 'field': field}
            if operations:
                changes.append({**common, 'before': before, 'after': after, 'operations': operations,
                                'status': 'formatting_proposal_unreviewed'})
            for flag in scan_text(after, known):
                flags.append({**common, **flag, 'context': after[max(0, flag['start']-65):flag['end']+65],
                              'offset_basis': 'text_proposal', 'status': 'pending_source_check'})
        record['text_proposal'] = proposal
    return result, changes, flags


def write_new_run(path, files):
    path = Path(path)
    path.mkdir(parents=True, exist_ok=False)
    for name, value in files.items():
        if Path(name).name != name:
            raise ValueError('Output names must be basenames')
        if name.endswith('.jsonl'):
            text = ''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in value)
        else:
            text = json.dumps(value, ensure_ascii=False, indent=2)
        (path/name).write_text(text, encoding='utf-8')
