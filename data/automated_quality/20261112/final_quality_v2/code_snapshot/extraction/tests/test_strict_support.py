import unittest
from extraction.automated_quality import compare_text
from extraction.strict_support import strict_supported

class StrictSupportTests(unittest.TestCase):
    def test_one_valid_word_error_in_long_text_is_not_cleared(self):
        source=' '.join(['principle']*60)+' liability '+' '.join(['doctrine']*60)
        check=compare_text(source.replace('liability','liberty'),source)
        self.assertGreater(check['ordered_token_agreement'],.98)
        self.assertFalse(strict_supported(check))

    def test_exact_machine_support_can_pass_without_humans(self):
        self.assertTrue(strict_supported(compare_text('not 16','not 16')))
        self.assertFalse(strict_supported(compare_text('not 16','')))

if __name__=='__main__':unittest.main()
