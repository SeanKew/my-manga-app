import unittest
from unittest.mock import patch

from services.online_catalog_service import (
    MangaCatalogError,
    display_title,
    get_manga_details,
    plain_description,
    search_manga,
)


SAMPLE = {
    "id": 123,
    "title": {"english": "Example Manga", "native": "例"},
    "description": "<b>Hello</b> &amp; world",
    "siteUrl": "https://anilist.co/manga/123",
}


class OnlineCatalogTests(unittest.TestCase):
    @patch("services.online_catalog_service._request")
    def test_search_returns_catalog_results(self, request):
        request.return_value = {"Page": {"media": [SAMPLE]}}
        self.assertEqual([SAMPLE], search_manga("Example"))
        request.assert_called_once()

    @patch("services.online_catalog_service._request")
    def test_blank_search_does_not_call_network(self, request):
        self.assertEqual([], search_manga("   "))
        request.assert_not_called()

    @patch("services.online_catalog_service._request")
    def test_details_reject_invalid_id(self, request):
        with self.assertRaises(ValueError):
            get_manga_details(0)
        request.assert_not_called()

    @patch("services.online_catalog_service._request")
    def test_details_missing_entry_raises_catalog_error(self, request):
        request.return_value = {"Media": None}
        with self.assertRaises(MangaCatalogError):
            get_manga_details(123)

    def test_title_and_description_are_safely_formatted(self):
        self.assertEqual("Example Manga", display_title(SAMPLE))
        self.assertEqual("Hello & world", plain_description(SAMPLE))


if __name__ == "__main__":
    unittest.main()
