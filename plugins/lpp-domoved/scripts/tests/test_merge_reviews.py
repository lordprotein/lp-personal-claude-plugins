import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import merge_reviews  # noqa: E402


class MergeReviewsTest(unittest.TestCase):
    def test_merge_pages_without_dups(self):
        p1 = {"url": "u", "site": "avito", "rating": 4.5, "count": 23, "summary": "Есть проблемы с шумоизоляцией",
              "distribution": {"5": 16}, "pages": 8, "blocked": False,
              "reviews": [{"date": "25 августа", "text": "Тёплый дом"}, {"date": "3 августа", "pros": "УК моет полы"}]}
        p2 = {"site": "avito", "blocked": False, "reviews": [{"date": "25 августа", "text": "Тёплый дом"},
                                                            {"date": "28 ноября 2025", "text": "Всегда чисто"}]}
        p3 = {"blocked": True, "reviews": []}
        res = merge_reviews.merge([p1, p2, p3])
        self.assertFalse(res["blocked"])
        self.assertEqual(res["count"], 23)
        self.assertEqual(res["summary"], "Есть проблемы с шумоизоляцией")
        self.assertEqual(len(res["reviews"]), 3)

    def test_first_blocked_then_ok(self):
        res = merge_reviews.merge([{"blocked": True, "reviews": []}, {"rating": 4.0, "reviews": [{"text": "ok"}]}])
        self.assertFalse(res["blocked"])
        self.assertEqual(res["rating"], 4.0)

    def test_all_blocked(self):
        self.assertTrue(merge_reviews.merge([{"blocked": True}])["blocked"])

    def test_empty(self):
        self.assertEqual(merge_reviews.merge([])["reviews"], [])


if __name__ == "__main__":
    unittest.main()
