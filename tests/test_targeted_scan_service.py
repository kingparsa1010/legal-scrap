import unittest
from scanner.parser import parse_classes, parse_search_results
from services.targeted_scan_service import collect_targeted_scan, _matches_target_class


class FakeClient:
    def __init__(self, first_page_html: str, second_page_html: str = ""):
        self.first_page_html = first_page_html
        self.second_page_html = second_page_html

    def search_first_page(self, params, captcha):
        return self.first_page_html, 20

    def get_page(self, page_num, params, captcha, total_records):
        return self.second_page_html


class TargetedScanFilterTests(unittest.TestCase):
    def test_parse_classes_persian_and_english(self):
        self.assertEqual(parse_classes("۵"), [5])
        self.assertEqual(parse_classes("۵، ۲۹، ۳۰"), [5, 29, 30])
        self.assertEqual(parse_classes("35"), [35])
        self.assertEqual(parse_classes("1 تا 5"), [1, 2, 3, 4, 5])
        self.assertEqual(parse_classes("3, 35, 39"), [3, 35, 39])
        self.assertNotIn(5, parse_classes("35"))
        self.assertNotIn(5, parse_classes("30, 35, 39"))
        self.assertNotIn(5, parse_classes("43"))

    def test_matches_target_class(self):
        row_c5 = {"classes": [5], "has_class_5": True}
        row_c35 = {"classes": [35], "has_class_5": False}
        row_multi_with_5 = {"classes": [3, 5, 29], "has_class_5": True}
        row_multi_without_5 = {"classes": [30, 35, 39], "has_class_5": False}

        self.assertTrue(_matches_target_class(row_c5, 5))
        self.assertTrue(_matches_target_class(row_multi_with_5, 5))
        self.assertFalse(_matches_target_class(row_c35, 5))
        self.assertFalse(_matches_target_class(row_multi_without_5, 5))

    def test_collect_targeted_scan_filters_out_non_class_5(self):
        # HTML containing two records: one in class 5 and one in class 35
        html = """
        <a href="/detail/1">
            <h2>Brand Class 5</h2>
            <span>شماره اظهارنامه: 1001</span>
            <span>تاریخ اظهارنامه: 1403/01/01</span>
            <span>وضعیت پرونده: ثبت شده</span>
            <span>طبقه بندی: ۵</span>
        </a>
        <a href="/detail/2">
            <h2>Brand Class 35</h2>
            <span>شماره اظهارنامه: 1002</span>
            <span>تاریخ اظهارنامه: 1403/01/01</span>
            <span>وضعیت پرونده: ثبت شده</span>
            <span>طبقه بندی: ۳۵</span>
        </a>
        <a href="/detail/3">
            <h2>Brand Multi Including 5</h2>
            <span>شماره اظهارنامه: 1003</span>
            <span>تاریخ اظهارنامه: 1403/01/01</span>
            <span>وضعیت پرونده: ثبت شده</span>
            <span>طبقه بندی بین المللی: ۳، ۵، ۲۹</span>
        </a>
        <a href="/detail/4">
            <h2>Brand Class 43</h2>
            <span>شماره اظهارنامه: 1004</span>
            <span>تاریخ اظهارنامه: 1403/01/01</span>
            <span>وضعیت پرونده: ثبت شده</span>
            <span>طبقات: ۴۳</span>
        </a>
        """
        client = FakeClient(first_page_html=html)
        emitted_records = []

        collected = collect_targeted_scan(
            client=client,
            params={"SignProductId": "5"},
            captcha="1234",
            max_pages=1,
            is_cancelled=lambda: False,
            on_progress=lambda *_: None,
            on_record=lambda r: emitted_records.append(r),
        )

        # Only 2 out of 4 records have class 5
        self.assertEqual(len(collected), 2)
        self.assertEqual(len(emitted_records), 2)

        collected_nos = [r["declaration_no"] for r in collected]
        self.assertIn("1001", collected_nos)
        self.assertIn("1003", collected_nos)
        self.assertNotIn("1002", collected_nos)
        self.assertNotIn("1004", collected_nos)


if __name__ == "__main__":
    unittest.main()
