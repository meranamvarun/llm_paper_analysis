import unittest
from extraction.recheck_merge import contains_regions
class RecheckMergeTests(unittest.TestCase):
    def test_crop_must_cover_every_current_source_region(self):
        q={'pdf_pages':[1,2],'evidence':[{'pdf_page':1,'bbox':[0,10,100,40]},{'pdf_page':2,'bbox':[0,20,100,60]}]}
        good=[{'pdf_page':1,'crop_top':6,'crop_bottom':44},{'pdf_page':2,'crop_top':16,'crop_bottom':64}]
        self.assertTrue(contains_regions(q,good))
        self.assertFalse(contains_regions(q,good[:1]))
        good[1]['crop_bottom']=50
        self.assertFalse(contains_regions(q,good))
