import logging
import unittest

from sequoia_diff.string_comparisons import (
    levenshtein_distance,
    normalized_levenshtein_distance,
    normalized_tri_gram_distance,
    tri_gram_distance,
)


class TestStringComparisons(unittest.TestCase):
    def test_levenshtein_distance(self):
        data: list[tuple[str | None, str | None, int, float, float, float]] = [
            ("", "", 0, 0.0, 0.0, 0.0),
            ("abc", "", 3, 1.0, 2.0, 1.0),
            ("", "abc", 3, 1.0, 2.0, 1.0),
            ("abc", "abc", 0, 0.0, 0.0, 0.0),
            ("kitten", "sitting", 3, 3.0 / 7.0, 7, 7.0 / 9.0),
            ("flaw", "lawn", 2, 2.0 / 4.0, 2, 0.5),
            ("ab", "bc", 2, 1.0, 2.0, 1.0),
            ("a", "b", 1, 1.0, 2.0, 1.0),
            ("Apple", "apple", 1, 1.0 / 5.0, 2, 1.0 / 3.0),
            (None, "abc", 3, 1.0, 2.0, 1.0),
            ("abc", None, 3, 1.0, 2.0, 1.0),
            (None, None, 0, 0.0, 0.0, 0.0),
        ]

        for s1, s2, lev, lev_norm, tri, tri_norm in data:
            logging.debug(f"s1: {s1}, s2: {s2}")

            self.assertEqual(levenshtein_distance(s1, s2), lev)
            self.assertAlmostEqual(normalized_levenshtein_distance(s1, s2), lev_norm)
            self.assertEqual(tri_gram_distance(s1, s2), tri)
            self.assertAlmostEqual(normalized_tri_gram_distance(s1, s2), tri_norm)
