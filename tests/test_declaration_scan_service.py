import unittest
from services.declaration_scan_service import collect_declarations, IncompleteFullScan


class FakeSession:
    def get(self, *args, **kwargs):
        raise AssertionError("network should not be called")


class DeclarationScanServiceTests(unittest.TestCase):
    def test_full_scan_refuses_page_cap_before_mutating_snapshot(self):
        html = '<a href="?TotalRecord=100"></a>'
        existing = {"old": {"dec_no_id": "old", "title": "safe"}}
        with self.assertRaises(IncompleteFullScan):
            collect_declarations(FakeSession(), html, "full_rescan", 2, existing,
                                 lambda: True, lambda *_: None, lambda *_: None)
        self.assertIn("old", existing)

    def test_full_scan_rejects_unexpected_empty_page(self):
        html = '<a href="?TotalRecord=1"></a><tbody id="DataList"></tbody>'
        with self.assertRaises(IncompleteFullScan):
            collect_declarations(FakeSession(), html, "full_rescan", 1, {},
                                 lambda: True, lambda *_: None, lambda *_: None)


if __name__ == "__main__":
    unittest.main()
