import unittest
from scanner.similarity import TrademarkSimilarityEngine, normalize_persian


class SimilarityRegressionTests(unittest.TestCase):
    def setUp(self):
        self.engine = TrademarkSimilarityEngine()

    def test_arabic_and_persian_letters_normalize(self):
        self.assertEqual(normalize_persian("ي ك"), "ی ک")

    def test_exact_match(self):
        self.assertEqual(self.engine.calculate_similarity("متاسنت", "متاسنت"), 100.0)

    def test_short_substring_is_not_automatic_high_risk(self):
        self.assertLess(self.engine.calculate_similarity("سامان", "ما"), 70.0)

    def test_whole_token_containment_is_high(self):
        self.assertEqual(self.engine.calculate_similarity("داروسازی متاسنت ایران", "متاسنت"), 95.0)


if __name__ == "__main__":
    unittest.main()
