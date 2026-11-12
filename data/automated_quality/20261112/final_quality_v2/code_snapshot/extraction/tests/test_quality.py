import copy
import tempfile
import unittest
from pathlib import Path

from extraction.quality import normalize_text, scan_text, clean_records, write_new_run, apply_source_reviews
from extraction.benchmark import edit_distance, score_reference
from extraction.quality_run import sample_pages


class QualityTests(unittest.TestCase):
    def test_whitespace_only_cleanup_preserves_semantics(self):
        value = "Do NOT pay \u20b9 1,000; s.16(3) \u2260 18.\u00a0  A\tB\nC\u0301"
        clean, changes = normalize_text(value)
        self.assertEqual(clean, "Do NOT pay \u20b9 1,000; s.16(3) \u2260 18. A B\n\u0106")
        self.assertTrue(changes)
        self.assertEqual(normalize_text(clean), (clean, []))

    def test_dictionary_unknown_is_flag_not_replacement(self):
        text = "Justice Qzxname's non-obstante rule and l0w \u00ae"
        flags = scan_text(text, lambda token: token.lower() in {'justice', 'non', 'obstante', 'rule', 'and'})
        self.assertIn('out_of_lexicon', [f['reason'] for f in flags])
        self.assertIn('mixed_digit_letter', [f['reason'] for f in flags])
        self.assertIn('suspicious_symbol', [f['reason'] for f in flags])
        unknown = next(f for f in flags if f['reason']=='out_of_lexicon')
        self.assertEqual(unknown['text'], "Qzxname's")
        self.assertEqual(text[unknown['start']:unknown['end']], unknown['text'])

    def test_ascii_artifacts_screened_but_blanks_preserved(self):
        text='@ Alias # mark ~ ` currency | list * star ____ blank'
        flags=scan_text(text,lambda _:True)
        chars=[f['text'] for f in flags if f['reason']=='suspicious_ascii']
        self.assertEqual(chars,['@','#','~','`','|','*'])
        self.assertFalse(any('_' in f['text'] for f in flags))

    def test_currency_percent_and_degree_are_screened_without_deletion(self):
        text='2017 $C; 10%; 5\u00b0; pre\u2022natal; Summit+5 = example'
        flags=scan_text(text,lambda _:True)
        self.assertTrue({'$','%','\u00b0','\u2022','+','='} <= {f['text'] for f in flags})
        self.assertEqual(normalize_text(text)[0],text)

    def test_encoding_damage_is_rejected(self):
        rows=[{'question_id':'q','text_proposal':{'stem':'Owner','options':[]}}]
        flag={'flag_id':'one','record_id':'q','field':'stem','start':0,'end':5,'text':'Owner'}
        review={'flag_id':'one','disposition':'source_supported_change','replacement':'Owner?s',
                'source_checked':True,'image_paths':['image.jpg']}
        with self.assertRaises(ValueError):apply_source_reviews(rows,[flag],[review])

    def test_scope_traceability_and_immutability(self):
        rows = [{'question_id':'q1','year_label':2020,'stem':'Not\u00a0  clear',
                 'options':[{'label':'A','text':'\u20b9 30'}], 'raw_text':'ORIGINAL',
                 'accepted_correction':{'decision_id':'accepted'}},
                {'question_id':'q0','year_label':2015,'stem':'Not\u00a0  clear','options':[]}]
        frozen = copy.deepcopy(rows)
        cleaned, changes, flags = clean_records(rows, lambda _: True)
        self.assertEqual(rows, frozen)
        self.assertEqual(cleaned[0]['stem'], rows[0]['stem'])
        self.assertEqual(cleaned[0]['text_proposal']['stem'],'Not clear')
        self.assertEqual(cleaned[0]['accepted_correction'],rows[0]['accepted_correction'])
        self.assertEqual(cleaned[1], rows[1])
        self.assertEqual(changes[0]['record_id'],'q1')
        self.assertEqual(changes[0]['field'],'stem')
        self.assertEqual(cleaned[0]['raw_text'],'ORIGINAL')
        self.assertEqual(cleaned[0]['text_proposal']['review_status'],'unreviewed')

    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'run'
            write_new_run(out, {'items.json': []})
            with self.assertRaises(FileExistsError):write_new_run(out, {'items.json': [1]})
            self.assertEqual((out/'items.json').read_text().strip(),'[]')

    def test_source_changes_require_evidence_and_use_original_offsets(self):
        rows=[{'question_id':'q','year_label':2020,'stem':'x','options':[],
               'text_proposal':{'stem':'Acontract \u00ae l0w','options':[],'review_status':'unreviewed'}}]
        flags=[{'flag_id':'one','record_id':'q','field':'stem','start':0,'end':9,'text':'Acontract'},
               {'flag_id':'two','record_id':'q','field':'stem','start':10,'end':11,'text':'\u00ae'}]
        reviews=[{'flag_id':'one','disposition':'source_supported_change','replacement':'A contract',
                  'source_checked':True,'image_paths':['image.jpg']},
                 {'flag_id':'two','disposition':'source_supported_change','replacement':'',
                  'source_checked':True,'image_paths':['image.jpg']}]
        before=copy.deepcopy(rows)
        result,log=apply_source_reviews(rows,flags,reviews)
        self.assertEqual(result[0]['text_proposal']['stem'],'A contract l0w')
        self.assertEqual(rows,before)
        self.assertEqual(len(log),2)
        reviews[0]['source_checked']=False
        with self.assertRaises(ValueError):apply_source_reviews(rows,flags,reviews)

    def test_source_change_rejects_stale_span_and_missing_review(self):
        rows=[{'question_id':'q','text_proposal':{'stem':'word','options':[]}}]
        flag={'flag_id':'one','record_id':'q','field':'stem','start':0,'end':4,'text':'stale'}
        review={'flag_id':'one','disposition':'source_supported_change','replacement':'new',
                'source_checked':True,'image_paths':['image.jpg']}
        with self.assertRaises(ValueError):apply_source_reviews(rows,[flag],[review])
        with self.assertRaises(ValueError):apply_source_reviews(rows,[flag],[])


class BenchmarkTests(unittest.TestCase):
    def test_option_comparison_ignores_metadata_and_whitespace(self):
        pred=[{'alignment_id':'a','stem':'Text', 'options':[{'label':'A','text':'One  two','raw_label':'(A)'}]}]
        gold=[{'alignment_id':'a','stem':'Text', 'options':[{'label':'A','text':'One two'}],
               'gold_status':'adjudicated','reviewers':['one','two'],'adjudicator':'three'}]
        self.assertEqual(score_reference(pred,gold)['fully_correct_options'],1)

    def test_sampling_includes_pages_without_questions_and_is_reproducible(self):
        pages=[{'pdf_page':i,'height':800,'lines':[],'method':'fixture'} for i in range(1,9)]
        config={'papers':[{'paper_id':'p','year_label':2020,'body_ranges':[[1,8]]}]}
        sample=sample_pages(pages,config,per_stratum=3)
        self.assertEqual(sample,sample_pages(pages,config,per_stratum=3))
        self.assertEqual(sample['strata'][0]['population_size'],8)
        self.assertEqual(len(sample['sample_pages']),3)
        self.assertTrue(all(r['reviewer_a'] is None for r in sample['sample_pages']))

    def test_edit_distance(self):
        self.assertEqual(edit_distance('kitten','sitting'),3)
        self.assertEqual(edit_distance([],['x']),1)
        self.assertEqual(edit_distance('',''),0)

    def test_missing_gold_never_passes(self):
        report=score_reference([],[])
        self.assertEqual(report['gate'],'NOT_ASSESSED')
        self.assertIsNone(report['cer'])

    def test_errors_missing_extra_and_critical(self):
        pred=[{'alignment_id':'a','stem':'Pay 16','options':[{'label':'A','text':'Yes'}]},
              {'alignment_id':'extra','stem':'Extra','options':[]}]
        gold=[{'alignment_id':'a','stem':'Not pay 16','options':[{'label':'A','text':'Yes'},{'label':'B','text':'No'}], 'critical_tokens':['Not','16'], 'gold_status':'adjudicated','reviewers':['one','two'],'adjudicator':'three'},
              {'alignment_id':'missing','stem':'Missing','options':[], 'gold_status':'adjudicated','reviewers':['one','two'],'adjudicator':'three'}]
        report=score_reference(pred,gold)
        self.assertEqual(report['missing_items'],['missing'])
        self.assertEqual(report['extra_items'],['extra'])
        self.assertEqual(report['critical_token_errors'],1)
        self.assertEqual(report['fully_correct_options'],0)
        self.assertEqual(report['gate'],'FAIL')
        self.assertGreater(report['character_edits'],0)
        self.assertGreater(report['word_edits'],0)

    def test_unreviewed_reference_rejected(self):
        with self.assertRaises(ValueError):
            score_reference([], [{'alignment_id':'a','stem':'text','options':[], 'gold_status':'ai_proposal'}])

    def test_numeric_and_negation_errors_are_counted_without_spelling_folding(self):
        gold=[{'alignment_id':'a','stem':'Do not apply section 16 in 2020.',
               'options':[{'label':'A','text':'First'},{'label':'B','text':'Second'}],
               'critical_tokens':['not','16','2020'], 'gold_status':'adjudicated',
               'reviewers':['one','two'],'adjudicator':'three'}]
        pred=[{'alignment_id':'a','stem':'Do apply section 18 in 2021.',
               'options':[{'label':'B','text':'Second'},{'label':'A','text':'First'}]}]
        result=score_reference(pred,gold)
        self.assertEqual(result['critical_token_errors'],3)
        self.assertEqual(result['fully_correct_options'],0)
        self.assertEqual(result['gate'],'FAIL')

    def test_text_match_alone_cannot_approve_overall_benchmark(self):
        gold=[{'alignment_id':'a','stem':'Literal text','options':[], 'gold_status':'adjudicated',
               'reviewers':['one','two'],'adjudicator':'three'}]
        result=score_reference([{'alignment_id':'a','stem':'Literal text','options':[]}],gold)
        self.assertEqual(result['cer'],0)
        self.assertEqual(result['text_gate'],'PASS')
        self.assertEqual(result['gate'],'NOT_ASSESSED')

    def test_strata_report_separate_native_and_ocr_failures(self):
        gold=[{'alignment_id':key,'stratum_id':stratum,'stem':'not 16','options':[],
               'gold_status':'adjudicated','reviewers':['one','two'],'adjudicator':'three'}
              for key,stratum in [('a','native'),('b','ocr')]]
        pred=[{'alignment_id':'a','stem':'not 16','options':[]},
              {'alignment_id':'b','stem':'18','options':[]}]
        result=score_reference(pred,gold)
        self.assertEqual(result['stratum_reports']['native']['text_gate'],'PASS')
        self.assertEqual(result['stratum_reports']['ocr']['text_gate'],'FAIL')

if __name__=='__main__':unittest.main()
