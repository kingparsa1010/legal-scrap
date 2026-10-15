import unittest
from services.search_request_service import build_search_request, SearchRequestError


class SearchRequestServiceTests(unittest.TestCase):
    def test_rejects_unbounded_custom_search(self):
        with self.assertRaises(SearchRequestError):
            build_search_request({}, False)

    def test_normalizes_persian_digits(self):
        request = build_search_request({"class": "۵", "declaration_no": "۱۲۳"}, False)
        self.assertEqual(request.params["SignProductId"], "5")
        self.assertEqual(request.params["DeclarationNo"], "123")


if __name__ == "__main__":
    unittest.main()
