import unittest
from extraction.image_repairs import apply_proposals
class ImageRepairTests(unittest.TestCase):
    def test_explicit_before_and_source_images_required(self):
        q={'question_id':'q','stem':'before'}
        p={'question_id':'q','before':{'stem':'before'},'after':{'stem':'after'},'image_paths':['local.png'],'status':'assistant_image_proposal_unreviewed'}
        rows,logs=apply_proposals([q],[p])
        self.assertEqual(rows[0]['stem'],'after')
        self.assertEqual(q['stem'],'before')
        self.assertEqual(len(logs),1)
        p['before']['stem']='stale'
        with self.assertRaises(ValueError):apply_proposals([q],[p])
    def test_source_and_field_allowlist(self):
        p={'question_id':'q','before':{'question_id':'q'},'after':{'question_id':'new'},'image_paths':['local.png']}
        with self.assertRaises(ValueError):apply_proposals([{'question_id':'q'}],[p])
