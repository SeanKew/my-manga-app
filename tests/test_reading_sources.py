import unittest
from urllib.parse import unquote

from services.reading_sources_service import discover_reading_sources


class ReadingSourceDiscoveryTests(unittest.TestCase):
    def test_blank_title_returns_no_sources(self):
        self.assertEqual([], discover_reading_sources("  "))

    def test_returns_curated_sources_and_discloses_availability(self):
        sources = discover_reading_sources("One Punch Man")
        self.assertIn("mangaplus", [source["id"] for source in sources])
        self.assertIn("webtoon", [source["id"] for source in sources])
        self.assertTrue(all(source["url"].startswith("https://") for source in sources))
        self.assertTrue(all(source["availability"] for source in sources))

    def test_search_title_is_url_encoded(self):
        sources = discover_reading_sources("Spy x Family")
        webtoon = next(source for source in sources if source["id"] == "webtoon")
        self.assertIn("Spy+x+Family", webtoon["url"])


if __name__ == "__main__":
    unittest.main()
