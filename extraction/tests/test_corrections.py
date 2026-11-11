import copy
import unittest

from extraction.corrections import apply_accepted


def fixture():
    original = {'question_id': 'old', 'raw_text': 'observed',
                'evidence': [{'pdf_page': 1}], 'review_status': 'unreviewed'}
    replacement = dict(original, question_id='new', raw_text='earlier\nobserved')
    other = dict(original, question_id='other')
    item = {'packet_item_id': 'review-1', 'kind': 'id_alias',
            'baseline': original, 'reparse': replacement,
            'proposal': {'old_id': 'old', 'new_id': 'new'}}
    decision = {'packet_item_id': 'review-1', 'decision_id': 'decision-1',
                'decision': 'accept', 'packet_items_sha256': 'packet-hash',
                'baseline_question_id': 'old', 'proposed_question_id': 'new'}
    return [original, other], [item], [decision]


class CorrectionTests(unittest.TestCase):
    def test_alias_changes_only_accepted_record_and_preserves_inputs(self):
        baseline, items, decisions = fixture()
        frozen = copy.deepcopy((baseline, items, decisions))
        result, log = apply_accepted(baseline, items, decisions, 'packet-hash')
        self.assertEqual(result[0]['question_id'], 'new')
        self.assertEqual(result[1], baseline[1])
        self.assertEqual(log[0]['before'], baseline[0])
        self.assertEqual(log[0]['after'], result[0])
        self.assertEqual((baseline, items, decisions), frozen)
        self.assertEqual(result[0]['review_status'], 'unreviewed')
        self.assertEqual(result[0]['accepted_correction']['decision_id'], 'decision-1')

    def test_transcription_keeps_raw_evidence_and_separates_corrected_text(self):
        baseline, items, decisions = fixture()
        items[0].update(kind='transcription', reparse=None, proposal={
            'printed_question_number': '24', 'stem': 'Correct stem?',
            'parenthetical_text': '(Context)',
            'options': [{'label': label, 'text': label+' text'} for label in 'ABCD']})
        decisions[0]['proposed_question_id'] = None
        result, log = apply_accepted(baseline, items, decisions, 'packet-hash')
        self.assertEqual(result[0]['raw_text'], 'observed')
        self.assertEqual(result[0]['evidence'], baseline[0]['evidence'])
        self.assertEqual(result[0]['printed_question_number'], '24')
        self.assertIn('(Context)', result[0]['corrected_text'])
        self.assertEqual(len(result[0]['options']), 4)
        self.assertEqual(log[0]['old_id'], log[0]['new_id'])

    def test_parser_version_only_snapshot_difference_is_logged(self):
        baseline, items, decisions = fixture()
        items[0]['baseline'] = copy.deepcopy(baseline[0])
        baseline[0]['parser_version'] = 'older'
        items[0]['baseline']['parser_version'] = 'newer'
        _, log = apply_accepted(baseline, items, decisions, 'packet-hash')
        self.assertEqual(log[0]['before']['parser_version'], 'older')
        self.assertEqual(log[0]['packet_baseline']['parser_version'], 'newer')

    def test_rejects_stale_or_unsafe_application(self):
        for defect in ['hash', 'reject', 'duplicate', 'stale', 'missing', 'collision', 'evidence']:
            with self.subTest(defect=defect):
                baseline, items, decisions = fixture()
                if defect == 'hash': decisions[0]['packet_items_sha256'] = 'changed'
                if defect == 'reject': decisions[0]['decision'] = 'reject'
                if defect == 'duplicate': decisions.append(copy.deepcopy(decisions[0]))
                if defect == 'stale': baseline[0]['raw_text'] = 'changed'; items[0]['baseline'] = dict(baseline[0], raw_text='observed')
                if defect == 'missing': baseline.pop(0)
                if defect == 'collision': baseline[1]['question_id'] = 'new'
                if defect == 'evidence': items[0]['reparse']['evidence'] = []
                with self.assertRaises(ValueError):
                    apply_accepted(baseline, items, decisions, 'packet-hash')
