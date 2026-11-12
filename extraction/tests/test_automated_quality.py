import unittest
from extraction.automated_quality import compare_text, structural_checks, aggregate_gate

class AutomatedQualityTests(unittest.TestCase):
    def test_missing_negation_and_changed_number_are_detected(self):
        r=compare_text('Do not apply section 16.','Do apply section 18.')
        self.assertEqual(r['missing_numbers'],['16'])
        self.assertIn('not',r['negation_disagreements'])
        self.assertLess(r['ordered_token_agreement'],1)

    def test_order_matters_and_case_is_lexical_only(self):
        self.assertEqual(compare_text('Alpha beta','ALPHA BETA')['ordered_token_agreement'],1)
        self.assertLess(compare_text('Alpha beta','beta alpha')['ordered_token_agreement'],1)

    def test_missing_source_cannot_pass(self):
        r=compare_text('Literal text','')
        self.assertEqual(r['status'],'NO_OCR_EVIDENCE')
        self.assertEqual(aggregate_gate([], [r]),'NEEDS_AUTOMATED_REPAIR')
        self.assertEqual(aggregate_gate([], []),'NOT_RUN')

    def test_structural_defects(self):
        config={'source_sha256':'hash','papers':[{'paper_id':'p','year_label':2020,'body_ranges':[[1,2]],'expected_mcqs':2,'passage_format':True}]}
        q={'question_id':'same','paper_id':'p','year_label':2020,'source_hash':'hash','section_id':'one','printed_question_number':'1','format':'mcq','stem':'Question','options':[{'label':'A','text':'One'}],'passage_id':'missing','pdf_pages':[1],'evidence':[{'pdf_page':1,'line_id':'l1','bbox':[0,0,10,10]}]}
        findings=structural_checks([q,q],[],config)
        types={f['kind'] for f in findings}
        self.assertTrue({'duplicate_id','option_structure','passage_reference','duplicate_number','missing_number'} <= types)
        self.assertEqual(aggregate_gate(findings,[compare_text('Same','Same')]),'NEEDS_AUTOMATED_REPAIR')

    def test_passing_automated_checks_do_not_require_humans(self):
        self.assertEqual(aggregate_gate([], [compare_text('Do not use 16','Do not use 16')]),'PASS')
        self.assertNotIn('accuracy',compare_text('Same','Same'))

if __name__=='__main__':unittest.main()

class TypographicSupportTests(unittest.TestCase):
    def test_only_typographic_apostrophes_and_ligatures_normalize(self):
        self.assertEqual(compare_text("man's first", "man\u201fs \ufb01rst")['ordered_token_agreement'],1)
        self.assertLess(compare_text("don't",'dont')['ordered_token_agreement'],1)
        self.assertTrue(compare_text('not 16','not 18')['missing_numbers'])
