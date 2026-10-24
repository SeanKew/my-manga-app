import unittest

from services.native_reading_service import (
    AD_BLOCK_LINK_PREFIXES,
    COSMETIC_AD_FILTER_JS,
    IMAGE_EXTRACTION_JS,
    IMAGE_MESSAGE_PREFIX,
    normalize_image_candidates,
)


class NativeReadingServiceTests(unittest.TestCase):
    def test_resolves_relative_image_urls_and_deduplicates(self):
        images = normalize_image_candidates(
            ["/chapter/001.jpg", "https://cdn.example.org/p2.jpg", "/chapter/001.jpg"],
            "https://reader.example.org/manga/1/chapter/2",
        )
        self.assertEqual(
            [
                "https://reader.example.org/chapter/001.jpg",
                "https://cdn.example.org/p2.jpg",
            ],
            images,
        )

    def test_rejects_non_http_urls(self):
        images = normalize_image_candidates(
            ["data:image/png;base64,AAAA", "blob:https://reader.example.org/123", "javascript:alert(1)"],
            "https://reader.example.org/chapter/2",
        )
        self.assertEqual([], images)

    def test_rejects_small_ad_like_image_dimensions(self):
        images = normalize_image_candidates(
            [
                {"url": "https://cdn.example.org/banner.jpg", "width": 728, "height": 90},
                {"url": "https://cdn.example.org/page.jpg", "width": 760, "height": 1100},
            ],
            "https://reader.example.org/chapter/2",
        )
        self.assertEqual(["https://cdn.example.org/page.jpg"], images)

    def test_extract_message_prefix_is_supported(self):
        payload = IMAGE_MESSAGE_PREFIX + '["https://cdn.example.org/page.jpg"]'
        self.assertEqual(
            ["https://cdn.example.org/page.jpg"],
            normalize_image_candidates(payload, "https://reader.example.org/chapter/2"),
        )

    def test_ad_filter_and_extractor_have_expected_hooks(self):
        self.assertTrue(AD_BLOCK_LINK_PREFIXES)
        self.assertIn("MutationObserver", COSMETIC_AD_FILTER_JS)
        self.assertIn("googleads", COSMETIC_AD_FILTER_JS)
        self.assertIn(IMAGE_MESSAGE_PREFIX, IMAGE_EXTRACTION_JS)
        self.assertIn("document.images", IMAGE_EXTRACTION_JS)


if __name__ == "__main__":
    unittest.main()
