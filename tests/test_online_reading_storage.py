import tempfile
import unittest
from pathlib import Path

from data.repository import MangaRepository


class OnlineReadingStorageTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = MangaRepository(db_path=Path(self.temp_dir.name) / "test.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_online_manga_is_added_once_by_catalog_id(self):
        first_id, created = self.repo.add_online_manga(
            "一拳超人",
            "https://reader.example/search",
            "https://img.example/cover.jpg",
            catalog_id=101,
        )
        second_id, created_again = self.repo.add_online_manga(
            "一拳超人",
            "https://reader.example/chapter/1",
            catalog_id=101,
        )
        self.assertTrue(created)
        self.assertFalse(created_again)
        self.assertEqual(first_id, second_id)
        self.assertEqual("online", self.repo.get_manga(first_id)["source_type"])

    def test_online_favorite_and_scroll_position_are_persisted(self):
        manga_id, _ = self.repo.add_online_manga(
            "一拳超人",
            "https://reader.example/search",
            catalog_id=101,
        )
        self.repo.set_favorite(manga_id, True)
        self.repo.save_online_progress(manga_id, "https://reader.example/chapter/3", 1280)

        manga = self.repo.get_manga(manga_id)
        progress = self.repo.get_progress(manga_id)
        self.assertEqual(1, manga["is_favorite"])
        self.assertEqual("https://reader.example/chapter/3", progress["source_url"])
        self.assertEqual(1280, progress["page_index"])
        self.assertIsNone(progress["chapter_id"])

    def test_online_progress_is_clamped_to_non_negative_values(self):
        manga_id, _ = self.repo.add_online_manga(
            "Temporary online entry",
            "https://reader.example/",
            catalog_id=102,
        )
        self.repo.save_online_progress(manga_id, "https://reader.example/chapter/1", -10)
        self.assertEqual(0, self.repo.get_progress(manga_id)["page_index"])


if __name__ == "__main__":
    unittest.main()
