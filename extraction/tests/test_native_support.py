import unittest
from extraction.native_support import native_region
class Page:
    def get_height(self):return 200
    def get_width(self):return 100
class TextPage:
    def get_text_bounded(self,left,bottom,right,top):
        assert (left,bottom,right,top)==(0,148,100,192)
        return 'Literal source text'
class NativeTests(unittest.TestCase):
    def test_coordinate_conversion_and_source_text(self):
        q={'pdf_pages':[1],'evidence':[{'pdf_page':1,'bbox':[0,10,100,50]}]}
        self.assertEqual(native_region(q,{1:(Page(),TextPage())}),'Literal source text')
