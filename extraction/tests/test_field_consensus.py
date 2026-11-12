import unittest
from extraction.field_consensus import consensus, decode_field_image, field_source_support
class ConsensusTests(unittest.TestCase):
    def test_two_literal_readings_must_agree_and_be_nonempty(self):
        self.assertEqual(consensus('Do not use section 16.','Do not use section 16.'),'Do not use section 16.')
        self.assertIsNone(consensus('Do not use section 16.','Do use section 16.'))
        self.assertIsNone(consensus('section 16','section 18'))
        self.assertIsNone(consensus('',''))

    def test_resolves_indirect_png_predictor_parameters(self):
        import zlib
        from pypdf import PdfWriter
        from pypdf.generic import EncodedStreamObject,DictionaryObject,NameObject,NumberObject
        writer=PdfWriter();params=DictionaryObject({NameObject('/Predictor'):NumberObject(15),NameObject('/Colors'):NumberObject(3),NameObject('/Columns'):NumberObject(2)})
        stream=EncodedStreamObject();stream._data=zlib.compress(bytes([1,255,0,0,1,0,255]))
        stream.update({NameObject('/Filter'):NameObject('/FlateDecode'),NameObject('/DecodeParms'):writer._add_object(params),NameObject('/Width'):NumberObject(2),NameObject('/Height'):NumberObject(1),NameObject('/ColorSpace'):NameObject('/DeviceRGB'),NameObject('/BitsPerComponent'):NumberObject(8)})
        image=decode_field_image(stream)
        self.assertEqual(image.getpixel((0,0)),(255,0,0))
        self.assertEqual(image.getpixel((1,0)),(0,0,255))

    def test_each_field_must_have_its_own_source_support(self):
        q={'stem':'Question','options':[{'text':t} for t in ['section 16','two','three','four']]}
        values=['Question','section 16','two','three','four']
        group={f:{'readings':[{'psm':7,'text':t,'returncode':0,'path':'local'}]} for f,t in zip(['stem','option_A','option_B','option_C','option_D'],values)}
        self.assertIsNotNone(field_source_support(q,group))
        group['option_A']['readings'][0]['text']='section 18'
        self.assertIsNone(field_source_support(q,group))
