"""Conservative proposal parser. Raw page lines are always retained separately."""
import re

VERSION = '0.1.2'
QUESTION = re.compile(r'^(?:Q\s*\.\s*)?(\d{1,3})(?:\s*[.)]\s*|\s+)(.*)', re.I)
PASSAGE = re.compile(r'^([IVX]+)\s*[.)]\s+(.+)$', re.I)
SECTION = re.compile(r'^(?:Section\s*:|PART\s*[-Ã¢â‚¬â€œ])\s*(.+)', re.I)
LETTER_OPTION = re.compile(r'(?<!\w)(?:\(([A-Da-d])\)|([A-Da-d])[.)])\s+')
NUM_OPTION = re.compile(r'(?m)^\s*(?:Ans\s*)?([1-4])[.,]\s*', re.I)


def needs_ocr(text):
    return (not text.strip() or bool(re.search(r'\(cid:\d+\)', text)) or '\ufffd' in text
            or sum(ord(c) < 32 and c not in '\r\n\t' for c in text) / max(1, len(text)) > .1)


def option_parts(text):
    options_heading = re.search(r'(?mi)^(?:Options\s*:|Ans\s*:?)\s*$', text)
    base = options_heading.end() if options_heading else 0
    content = text[base:]
    matches = list(LETTER_OPTION.finditer(content))
    numeric = bool(options_heading) or (not matches and bool(re.search(r'(?m)^\s*Ans\s*1\.', content, re.I)))
    if numeric:
        matches = list(NUM_OPTION.finditer(content))
    options = []
    for i, match in enumerate(matches):
        label = 'ABCD'[int(match.group(1))-1] if numeric else (match.group(1) or match.group(2)).upper()
        options.append({'label': label, 'raw_label': match.group(0).strip(),
                        'text': content[match.end():matches[i+1].start() if i+1 < len(matches) else len(content)].strip()})
    stem = text[:base].strip() if options_heading else content[:matches[0].start()].strip() if matches else text.strip()
    stem = '\n'.join(line for line in stem.splitlines() if not re.match(
        r'^(?:Question Number\s*:|Correct\s*:|Options\s*:|Ans\s*$|Line Question Option\s*:|Single Line Question Option\s*:)', line, re.I))
    return stem, options


def evidence(lines):
    return [{'pdf_page': x['pdf_page'], 'line_id': x['line_id'], 'bbox': x['bbox']} for x in lines]


def parse_paper(pages, paper, source_hash):
    questions, passages, unresolved = [], [], []
    block = []
    passage = None
    section = 'unknown'
    instructions = []
    essay = False
    number = None
    last_number = None
    numeric_options = False

    def anchor(lines, kind):
        x = lines[0]
        return f'{source_hash}:p{x["pdf_page"]:04d}:{x["line_id"]}:{kind}'

    def flush():
        nonlocal block, number, last_number, numeric_options
        if not block:
            return
        raw = '\n'.join(x['text'] for x in block)
        answer = re.search(r'(?mi)^CORRECT\s+(?:OPTION|ANSWER)\s*[:Ã¯Â¼Å¡].*$', raw)
        parse_text = raw[:answer.start()] if answer else raw
        stem, opts = option_parts(parse_text)
        if number is not None and (essay or opts):
            issues = ['human_review_required']
            if len(re.sub(r'\W', '', stem)) < 15:
                issues.append('short_or_missing_stem')
            if not essay and [o['label'] for o in opts] != list('ABCD'):
                issues.append('option_labels_incomplete_or_duplicate')
            if last_number is not None and int(number) != last_number + 1:
                issues.append('number_sequence_gap_or_reset')
            last_number = int(number)
            if re.search(r'CORRECT\s+(?:OPTION|ANSWER)', raw, re.I):
                issues.append('inline_answer_present_unverified')
            if any(x.get('page_issues') for x in block):
                issues.append('source_page_issue')
            questions.append({'question_id': anchor(block, 'question'), 'paper_id': paper['paper_id'],
                'year_label': paper['year_label'], 'source_hash': source_hash, 'section_id': section,
                'printed_question_number': number, 'pdf_pages': sorted({x['pdf_page'] for x in block}),
                'printed_page': None, 'parent_question_id': None,
                'passage_id': passage['passage_id'] if passage and not essay else None,
                'raw_text': raw, 'stem': stem, 'corrected_text': None, 'options': opts,
                'inline_answer_raw': answer.group(0) if answer else None,
                'marks': None, 'format': 'essay' if essay else 'mcq',
                'section_instructions': '\n'.join(instructions), 'evidence': evidence(block),
                'extraction_method': sorted({x['method'] for x in block}), 'parser_version': VERSION,
                'review_status': 'unreviewed', 'issues': issues})
        elif passage:
            passage['raw_text'] += '\n' + raw
            passage['evidence'].extend(evidence(block))
        else:
            unresolved.append({'block_id': anchor(block, 'unresolved'), 'paper_id': paper['paper_id'],
                               'raw_text': raw, 'evidence': evidence(block),
                               'reason': 'numbered_candidate_without_options' if number else 'unclassified_text',
                               'review_status': 'unresolved'})
        block = []
        number = None
        numeric_options = False

    for page in pages:
        if page.get('format_hint') == 'essay' and not essay:
            flush()
            essay = True
            passage = None
            section = f'essay@p{page["pdf_page"]}'
            last_number = None
        for original in page['lines']:
            line = {**original, 'pdf_page': page['pdf_page'], 'method': page['method'], 'page_issues': page.get('issues', [])}
            text = line['text'].strip()
            if not text:
                continue
            meta_question = re.match(r'^Question Number\s*:\s*(\d{1,3})\b', text, re.I)
            if meta_question:
                flush()
                number = meta_question.group(1)
                block = [line]
                continue
            if re.match(r'^(?:Options\s*:|Ans\s*$)', text, re.I):
                numeric_options = True
            # Candidate metadata is excluded from parser state, not from raw page output.
            if re.search(r'^(?:Linked Answer Question:|Direction:|Sub Question No\s*:|Question (?:ID|Type|Label|Number)\s*:)', text, re.I):
                continue
            sec = SECTION.match(text)
            if sec:
                flush()
                passage = None
                section = f'{sec.group(1).strip()}@p{page["pdf_page"]}'
                last_number = None
                instructions = []
                essay = False
                continue
            if re.search(r'Answer\s+any\s+(?:TWO|THREE|\d+)', text, re.I):
                flush()
                essay = True
                instructions.append(text)
                continue
            if essay and not questions and re.search(r'All questions carry|Answer to each question|Instructions\s*:', text, re.I):
                instructions.append(text)
                continue
            if essay and number is None and re.search(r'All questions carry|Answer to each question|Instructions\s*:', text, re.I):
                instructions.append(text)
                continue
            pas = PASSAGE.match(text)
            completed_options = len(option_parts('\n'.join(x['text'] for x in block))[1]) >= 4
            configured_heading = (paper.get('passage_heading_max_x') is not None
                                  and line['bbox'][0] <= paper['passage_heading_max_x'])
            roman_statement = (pas and pas.group(1).islower() and number is not None
                               and not completed_options)
            if pas and not roman_statement and not essay and (configured_heading or (paper.get('passage_heading_max_x') is None
                                                             and (number is None or completed_options))):
                flush()
                passage = {'passage_id': anchor([line], 'passage'), 'paper_id': paper['paper_id'],
                           'printed_label': pas.group(1), 'raw_text': text, 'evidence': evidence([line]),
                           'review_status': 'unreviewed'}
                passages.append(passage)
                continue
            if re.match(r'^Ans\s*1\.', text, re.I):
                numeric_options = True
            # A numeric footer is retained as passage evidence, never a new question.
            passage_footer = (passage is not None and number is None
                              and page.get('height') is not None
                              and line['bbox'][1] >= page['height'] * .88
                              and re.fullmatch(r'\d{1,3}(?:\s+[^\w\d_]+|\s+\u03c1)?', text))
            q = None if passage_footer else QUESTION.match(text)
            numeric_continuation = (q and number is not None and block and not essay
                                    and not completed_options
                                    and re.match(r'^\d{1,3}\s+[A-Za-z]', text)
                                    and line['bbox'][0] > block[0]['bbox'][0] + 15)
            if q and not numeric_continuation and not (numeric_options and re.match(r'^[1-4]\.', text)):
                flush()
                number = q.group(1)
                block = [line]
            elif block:
                block.append(line)
            elif passage:
                passage['raw_text'] += '\n' + text
                passage['evidence'].extend(evidence([line]))
            else:
                block.append(line)
    flush()
    return questions, passages, unresolved


def parse_key_lines(pages, status):
    result = []
    for page in pages:
        for line in page['lines']:
            for match in re.finditer(r'(?<!\w)(\d{1,3})\s+(Withdrawn|[A-D])(?=\s|$)', line['text'], re.I):
                result.append({'printed_question_number': match.group(1), 'answer': match.group(2),
                    'pdf_page': page['pdf_page'], 'line_id': line['line_id'], 'bbox': line['bbox'],
                    'key_status': status, 'verification_status': 'unverified', 'raw_line': line['text']})
    return result
