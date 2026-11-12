import unittest
from extraction.recovery import letter_parts, answer_delimited_blocks, transfer_cleaning, metadata_options, numbered_source_blocks, numeric_parts

class RecoveryTests(unittest.TestCase):
    def test_initials_and_subsections_are_not_options(self):
        text="Question under section 19(1)(a) applies?\n(A) H.L.A. Hart\n(B) M.C. Mehta\n(C) Both (A) and (B)\n(D) Neither (A) nor (B)"
        stem,opts=letter_parts(text)
        self.assertEqual(stem,"Question under section 19(1)(a) applies?")
        self.assertEqual([o['label'] for o in opts],list('ABCD'))
        self.assertEqual(opts[0]['text'],'H.L.A. Hart')
        self.assertEqual(opts[2]['text'],'Both (A) and (B)')
    def test_earlier_statement_labels_stay_in_stem(self):
        stem,opts=letter_parts("Match:\n(A) item one\n(B) item two\nCodes:\n(A) 1\n(B) 2\n(C) 3\n(D) 4")
        self.assertIn('(A) item one',stem)
        self.assertEqual(opts[0]['text'],'1')
    def test_ambiguous_or_missing_block_abstains(self):
        self.assertIsNone(letter_parts("Question\n(A) one\n(C) three\n(D) four"))

    def test_answer_gaps_define_passages_not_numbered_paragraphs(self):
        lines=[{'text':t,'pdf_page':1,'line_id':str(i),'bbox':[10,i*10,200,i*10+8]} for i,t in enumerate(['Initial passage text','1. Question one','(A) one','(B) two','(C) three','(D) four','CORRECT OPTION: A','16. Numbered passage paragraph','2. Question two','(A) one','(B) two','(C) three','(D) four','CORRECT OPTION: B'])]
        blocks=answer_delimited_blocks(lines,2)
        self.assertEqual([b['number'] for b in blocks],[1,2])
        self.assertEqual(blocks[1]['preceding_passage'][0]['text'],'16. Numbered passage paragraph')
        self.assertEqual(blocks[0]['lines'][-1]['text'],'CORRECT OPTION: A')
    def test_missing_source_number_abstains(self):
        self.assertIsNone(answer_delimited_blocks([{'text':'1. Question'}],2))
    def test_cleaning_transfer_and_abstention(self):
        q={'stem':'Question','original_stem':'Question','original_options':[{'text':'long source context with wrod unchanged suffix'}],'options':[{'text':'long source context with word unchanged suffix'}]}
        r=transfer_cleaning('Question',[{'text':'long source context with wrod unchanged suffix'}],q)
        self.assertIn('word',r[1][0]['text'])
        self.assertIsNone(transfer_cleaning('Question',[{'text':'different'}],q))
    def test_metadata_requires_literal_all_four_labels(self):
        lines=[{'text':t} for t in ['Question Number : 7','Options :','1. one','2. two','3. three','4. four','Question Number : 8']]
        self.assertEqual(len(metadata_options(lines,7)),1)
        lines[4]['text']='2. three'
        self.assertEqual(metadata_options(lines,7),[])

    def test_two_columns_with_statute_reference(self):
        stem,opts=letter_parts("Question\n(a) Section 190(1)(b) (B) Section 159\n(C) Section 190(1)(a) (d) Section 173(8)")
        self.assertEqual([o['label'] for o in opts],list('ABCD'))
        self.assertEqual(opts[0]['text'],'Section 190(1)(b)')
    def test_ambiguous_inline_marker_abstains(self):
        self.assertIsNone(letter_parts("Question\n(A) Both (B) and other (B) text\n(C) three (D) four"))

    def test_literal_source_starts_reject_indented_statements(self):
        rows=[{'text':t,'bbox':[x,0,300,10]} for t,x in [('1. Question',10),('2. Internal statement',35),('(A) one',20),('2  . Actual next',10)]]
        r=numbered_source_blocks(rows,2)
        self.assertEqual([b['start'] for b in r],[0,3])
        self.assertIsNone(numbered_source_blocks(rows,3))
    def test_explicit_numbering_resets(self):
        rows=[{'text':t,'bbox':[10,0,300,10]} for t in ['1. first','2. second','1. restart','2. next']]
        r=numbered_source_blocks(rows,2,blocks=2)
        self.assertEqual([b['block'] for b in r],[0,0,1,1])
    def test_bare_2018_labels_require_complete_sequence(self):
        r=letter_parts('Question\nA one\nB two\nC three\nD four',allow_bare=True)
        self.assertEqual([o['label'] for o in r[1]],list('ABCD'))

    def test_spaced_labels_and_one_row_options(self):
        r=letter_parts('Question\n( A) one ( B) two ( C) three ( D) four')
        self.assertEqual([o['label'] for o in r[1]],list('ABCD'))
        r=letter_parts('Question\n(A) one\n( b) two\n(C) three\n( d) four')
        self.assertEqual(r[1][3]['text'],'four')

    def test_cleanup_already_satisfied_by_source_header_filter(self):
        q={'stem':'Question','original_stem':'Question','original_options':[{'text':'A long literal answer. * 6 PG'}],'options':[{'text':'A long literal answer.'}]}
        r=transfer_cleaning('Question',[{'text':'A long literal answer.'}],q)
        self.assertEqual(r[1][0]['text'],'A long literal answer.')

    def test_numeric_labels_read_literal_punctuation_variants(self):
        r=numeric_parts('Question\nOptions :\n1. one\n2, two\n3. three\n4 four')
        self.assertEqual([o['label'] for o in r],list('ABCD'))
        self.assertEqual(r[-1]['text'],'four')
        self.assertIsNone(numeric_parts('Options :\n1. one\n2. two\n2. three\n4. four'))
