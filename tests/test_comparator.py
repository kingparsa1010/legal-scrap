import unittest
from scanner.comparator import compare_stores, is_rejected_entry


class ComparatorFilterTests(unittest.TestCase):
    def test_is_rejected_entry(self):
        # Explicit is_rejected flag
        self.assertTrue(is_rejected_entry({"is_rejected": True}))
        self.assertTrue(is_rejected_entry({"is_rejected": 1}))
        self.assertTrue(is_rejected_entry({"is_rejected": "true"}))
        self.assertTrue(is_rejected_entry({"is_rejected": "1"}))

        # Rejected via status string
        self.assertTrue(is_rejected_entry({"status": "رد شده"}))
        self.assertTrue(is_rejected_entry({"status": "رد شده "}))
        self.assertTrue(is_rejected_entry({"status": "رد مشروط"}))
        self.assertTrue(is_rejected_entry({"status": "ابطال شده"}))
        self.assertTrue(is_rejected_entry({"status": "ابطال"}))
        self.assertTrue(is_rejected_entry({"status": "کان لم یکن"}))
        self.assertTrue(is_rejected_entry({"status": "انصراف داده شده"}))

        # Non-rejected active statuses
        self.assertFalse(is_rejected_entry({"status": "ثبت قطعی شده", "is_rejected": False}))
        self.assertFalse(is_rejected_entry({"status": "آگهی نوبت اول", "is_rejected": 0}))
        self.assertFalse(is_rejected_entry({"status": "پذیرش بلامانع"}))
        self.assertFalse(is_rejected_entry({"status": "در حال بررسی اولیه"}))
        self.assertFalse(is_rejected_entry({"status": "در حال رفع نقص"}))

    def test_compare_stores_filters_out_rejected_class5_records(self):
        data_store = {
            "1": {
                "declaration_no": "1001",
                "title": "Roblance روبالانس",
                "status": "ثبت قطعی شده",
                "is_rejected": False,
            }
        }
        # class5_store has one rejected record that matches title, and one active record that does not
        class5_store = {
            "2001": {
                "declaration_no": "2001",
                "title": "Roblue روبلو",
                "status": "رد شده",
                "is_rejected": True,
                "has_class_5": True,
            },
            "2002": {
                "declaration_no": "2002",
                "title": "DifferentBrand برند کاملا متفاوت",
                "status": "ثبت قطعی شده",
                "is_rejected": False,
                "has_class_5": True,
            },
        }

        # By default, rejected records from class5_store should NOT appear in matches
        matches = compare_stores(data_store, class5_store, threshold=70.0)
        self.assertEqual(len(matches), 0)

        # If include_rejected is True, the rejected record should match
        matches_with_rejected = compare_stores(data_store, class5_store, threshold=70.0, include_rejected=True)
        self.assertEqual(len(matches_with_rejected), 1)
        self.assertEqual(matches_with_rejected[0]["title_b"], "Roblue روبلو")
        self.assertEqual(matches_with_rejected[0]["status_b"], "رد شده")

    def test_compare_stores_includes_active_matching_class5_records(self):
        data_store = {
            "1": {
                "declaration_no": "1001",
                "title": "Roblance روبالانس",
                "status": "ثبت قطعی شده",
                "is_rejected": False,
            }
        }
        class5_store = {
            "2001": {
                "declaration_no": "2001",
                "title": "Roblue روبلو",
                "status": "آگهی نوبت اول",  # active/pending
                "is_rejected": False,
                "has_class_5": True,
            }
        }

        matches = compare_stores(data_store, class5_store, threshold=70.0)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]["title_a"], "Roblance روبالانس")
        self.assertEqual(matches[0]["title_b"], "Roblue روبلو")
        self.assertGreaterEqual(matches[0]["score"], 70.0)


if __name__ == "__main__":
    unittest.main()
