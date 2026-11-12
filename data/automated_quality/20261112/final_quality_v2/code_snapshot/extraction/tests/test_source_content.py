import unittest
from extraction.source_content import strip_export_metadata, clean_source_formatting
class SourceContentTests(unittest.TestCase):
    def test_metadata_no_is_not_a_prose_negation(self):
        value='Single Line Question Option : No Option Orientation : Vertical\nNo person shall be punished.\nSub Question No : 7'
        self.assertEqual(strip_export_metadata(value),'No person shall be punished.')

    def test_footer_requires_source_geometry_and_number_prefix_is_literal(self):
        q={'stem':'1 5. Question','printed_question_number':'15','options':[{'text':'Answer 3 rho PG 2026'}],'evidence':[{'pdf_page':1,'line_id':'f'}]}
        pages={1:{'height':800,'width':600,'lines':[{'line_id':'f','text':'3 rho PG 2026','bbox':[50,755,550,770]}]}}
        self.assertEqual(clean_source_formatting(q,pages)['stem'],'15. Question')
        self.assertEqual(clean_source_formatting(q,pages)['options'][0]['text'],'Answer')
        pages[1]['lines'][0]['bbox']=[50,400,550,420]
        self.assertNotIn('options',clean_source_formatting(q,pages))
