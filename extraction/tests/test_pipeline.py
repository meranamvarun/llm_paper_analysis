import unittest

from extraction.pipeline import parse_paper, parse_key_lines, needs_ocr
from extraction.run import word_lines


def page(n, text):
    return {'pdf_page': n, 'method': 'fixture', 'lines': [
        {'text': t, 'bbox': [0, i*10, 500, i*10+9], 'line_id': f'p{n}-l{i}'}
        for i, t in enumerate(text.splitlines())], 'issues': []}


def parse(pages, **kw):
    return parse_paper(pages, {'paper_id': 'paper', 'year_label': 2020, **kw}, 'a'*64)


class ParserTests(unittest.TestCase):
    def test_number_inside_incomplete_letter_option(self):
        for continuation in ['16 child receives a share.', '3 SCC 24.']:
            with self.subTest(continuation=continuation):
                ps = [page(1, '56. Which rule applies?\n(A) First\n(B) Citation or section\n'
                           + continuation + '\n(C) Third\n(D) Fourth\n57 Next question?\n'
                           '(A) One (B) Two (C) Three (D) Four')]
                ps[0]['lines'][3]['bbox'][0] = 40
                qs, _, _ = parse(ps)
                self.assertEqual([q['printed_question_number'] for q in qs], ['56', '57'])
                self.assertIn(continuation, qs[0]['options'][1]['text'])
                self.assertEqual(len(qs[0]['evidence']), 6)

    def test_footer_does_not_split_cross_page_passage(self):
        ps = [page(43, 'XXIII. Initial passage text.\n43 \u03c1\nPG 2026'),
              page(44, 'Continued passage citing A. Example.\n100. Which rule applies?\n'
                   '(A) One (B) Two (C) Three (D) Four')]
        ps[0]['height'] = 800
        ps[0]['lines'][1]['bbox'] = [290, 750, 540, 765]
        ps[0]['lines'][2]['bbox'] = [50, 755, 100, 770]
        qs, passages, _ = parse(ps)
        self.assertEqual([q['printed_question_number'] for q in qs], ['100'])
        self.assertIn('Continued passage', passages[0]['raw_text'])
        self.assertIn('43 \u03c1', passages[0]['raw_text'])
        self.assertEqual(len(passages[0]['evidence']), 4)
        self.assertEqual(qs[0]['passage_id'], passages[0]['passage_id'])

    def test_indented_unpunctuated_numeric_continuation(self):
        ps = [page(1, '108. Consider the following statements.\n'
                   'i. The rule includes articles 32, 226 or\n'
                   '136 of the example instrument.\n'
                   '(A) All (B) Some (C) Neither (D) Other\n'
                   '109 Next unpunctuated question?\n'
                   '(A) First (B) Second (C) Third (D) Fourth')]
        ps[0]['lines'][2]['bbox'][0] = 40
        qs, _, _ = parse(ps, passage_heading_max_x=20)
        self.assertEqual([q['printed_question_number'] for q in qs], ['108', '109'])
        self.assertIn('136 of the example instrument.', qs[0]['stem'])
        self.assertEqual(qs[0]['raw_text'], '\n'.join(l['text'] for l in ps[0]['lines'][:4]))

    def test_lowercase_roman_statements_at_heading_margin(self):
        ps = [page(1, 'VIII. Initial passage.\n108. Consider these statements.\n'
                   'i. First proposition.\nii. Second proposition.\niii. Third proposition.\n'
                   'Choose a combination.\n(A) All (B) First (C) Second (D) None\n'
                   'IX. Next passage.\n109. Which principle applies?\n'
                   '(A) First (B) Second (C) Third (D) Fourth')]
        qs, passages, _ = parse(ps, passage_heading_max_x=90)
        self.assertEqual([q['printed_question_number'] for q in qs], ['108', '109'])
        self.assertEqual([p['printed_label'] for p in passages], ['VIII', 'IX'])
        self.assertIn('iii. Third proposition.', qs[0]['stem'])
        self.assertEqual(qs[0]['raw_text'], '\n'.join(l['text'] for l in ps[0]['lines'][1:7]))
        self.assertTrue(all(q['review_status'] == 'unreviewed' for q in qs))

    def test_cross_page_and_inline_options(self):
        qs, passages, unresolved = parse([
            page(1, '1. Which rule applies?\n(A) First (B) Second'),
            page(2, '(C) Third\n(D) Fourth\n2. Next question?\n(A) A (B) B (C) C (D) D')])
        self.assertEqual(qs[0]['pdf_pages'], [1, 2])
        self.assertEqual([x['label'] for x in qs[0]['options']], list('ABCD'))
        self.assertEqual(len(qs), 2)
        self.assertEqual(unresolved, [])

    def test_numbered_passage_is_not_a_question(self):
        qs, passages, unresolved = parse([page(1,
            'I. Read this passage.\n1. This numbered paragraph explains the law.\n'
            '2. This paragraph continues it.\n1. Which principle applies?\n'
            '(A) A (B) B (C) C (D) D')])
        self.assertEqual(len(qs), 1)
        self.assertEqual(len(passages), 1)
        self.assertIn('numbered paragraph', passages[0]['raw_text'])
        self.assertEqual(qs[0]['passage_id'], passages[0]['passage_id'])

    def test_sections_and_stable_ids(self):
        ps = [page(1, 'Section : Constitutional Law\nQ.1 First?\nAns 1. A\n2. B\n3. C\n4. D\n'
            'Section : Jurisprudence\nQ.1 Second?\nAns 1. E\n2. F\n3. G\n4. H')]
        qs, _, _ = parse(ps)
        self.assertEqual(len(qs), 2)
        self.assertNotEqual(qs[0]['question_id'], qs[1]['question_id'])
        self.assertNotEqual(qs[0]['section_id'], qs[1]['section_id'])
        self.assertEqual(qs, parse(ps)[0])

    def test_essay_instructions(self):
        qs, _, _ = parse([page(1, 'PART-B\nAnswer any TWO of the following questions\n'
            '1. Critically examine the doctrine.\n2. Discuss the judgment.')])
        self.assertEqual(len(qs), 2)
        self.assertTrue(all(q['format'] == 'essay' for q in qs))
        self.assertIn('Answer any TWO', qs[0]['section_instructions'])

    def test_malformed_options_and_unresolved(self):
        qs, _, unresolved = parse([page(1, '1. Which is correct?\n(A) A (B) B (D) D\n'
            '2. Incomplete stem without options')])
        self.assertIn('option_labels_incomplete_or_duplicate', qs[0]['issues'])
        self.assertEqual(len(unresolved), 1)

    def test_multi_column_key_and_withdrawal(self):
        rows = parse_key_lines([page(5, 'Q. No. Correct Answer\n1 C 41 D 81 Withdrawn\n2 A 42 B 82 C')], 'provisional')
        self.assertEqual(len(rows), 6)
        self.assertEqual(rows[2]['answer'], 'Withdrawn')
        self.assertEqual(rows[2]['pdf_page'], 5)
        self.assertEqual(rows[0]['key_status'], 'provisional')

    def test_ocr_routing(self):
        self.assertTrue(needs_ocr(''))
        self.assertTrue(needs_ocr('\x00\x01\x02Question'))
        self.assertTrue(needs_ocr('(cid:2)56.(cid:2)Which question?'))
        self.assertFalse(needs_ocr('Readable question text.'))

    def test_paper_boundary_does_not_continue(self):
        a = parse([page(1, '1. Incomplete question')])[0]
        b = parse([page(2, '(A) First (B) Second (C) Third (D) Fourth')])[0]
        self.assertEqual(a, [])
        self.assertEqual(b, [])

    def test_numbered_essay_instructions_not_prompts(self):
        qs, _, _ = parse([page(1, 'PART-B\n1. Answer any TWO of the following questions\n'
            '2. All questions carry equal marks\n3. Answer to each question shall not exceed 800 words\n'
            '1. Explain the doctrine.\n2. Evaluate the judgment.')])
        self.assertEqual([q['printed_question_number'] for q in qs], ['1', '2'])
        self.assertIn('800 words', qs[0]['section_instructions'])

    def test_inline_answer_not_part_of_option(self):
        qs, _, _ = parse([page(1, '1. Which applies?\n(A) One (B) Two (C) Three (D) Four\nCORRECT OPTION: C')])
        self.assertEqual(qs[0]['options'][-1]['text'], 'Four')
        self.assertEqual(qs[0]['inline_answer_raw'], 'CORRECT OPTION: C')

    def test_lowercase_options_and_roman_statements(self):
        qs, passages, _ = parse([page(1, '1. Consider the statements.\nI. First statement.\n'
            'II. Second statement.\na) First\nb) Second\nc) Third\nd) Fourth')])
        self.assertEqual(len(qs), 1)
        self.assertEqual(passages, [])
        self.assertEqual([o['label'] for o in qs[0]['options']], list('ABCD'))

    def test_uppercase_options_not_passages(self):
        qs, passages, _ = parse([page(1, '1. Select a rule.\nA. First\nB. Second\nC. Third\nD. Fourth')])
        self.assertEqual(len(qs[0]['options']), 4)
        self.assertEqual(passages, [])

    def test_exported_exam_metadata_and_numbered_options(self):
        qs, _, _ = parse([page(1, 'Question Number : 1 Question Id : 999 Question Type: MCQ\n'
            'Correct : 1 Wrong : 0.25\nWhich rule applies?\nOptions :\n'
            '1. First\n2. Second\n3. Third\n4. Fourth\n'
            'Question Number : 2 Question Id : 998 Question Type: MCQ\nSecond question?\nOptions :\n'
            '1. A\n2. B\n3. C\n4. D')])
        self.assertEqual(len(qs), 2)
        self.assertEqual([o['text'] for o in qs[0]['options']], ['First','Second','Third','Fourth'])
        self.assertNotIn('Wrong', qs[0]['stem'])

    def test_ans_heading_on_separate_line(self):
        qs, _, _ = parse([page(1, 'Q.1 Which rule?\nAns\n1. First\n2. Second\n3. Third\n4. Fourth')])
        self.assertEqual(len(qs), 1)
        self.assertEqual([o['label'] for o in qs[0]['options']], list('ABCD'))

    def test_number_alone_then_stem(self):
        qs, _, _ = parse([page(1, '1)\nWhich rule?\n(A) A (B) B (C) C (D) D')])
        self.assertEqual(len(qs), 1)
        self.assertIn('Which rule?', qs[0]['stem'])

    def test_geometry_reunites_number_gutter_with_stems(self):
        words = [{'text':text,'x0':x,'x1':x+20,'top':y,'bottom':y+8}
                 for text,x,y in [('1.',10,10),('2.',10,30),('First?',40,10),('Second?',40,30)]]
        self.assertEqual([l['text'] for l in word_lines(words)], ['1. First?', '2. Second?'])


if __name__ == '__main__':
    unittest.main()
