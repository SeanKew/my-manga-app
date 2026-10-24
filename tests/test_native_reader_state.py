import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data.repository import MangaRepository


class NativeReaderStateTests(unittest.TestCase):
    def test_native_reader_pages_and_position_are_persisted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("data.repository.storage_root", return_value=root / "app-data"):
                repository = MangaRepository(db_path=root / "manga.db")
                manga_id, created = repository.add_online_manga(
                    title="Example Manga",
                    source_uri="https://reader.example.org/manga/1",
                    catalog_id=123,
                )
                self.assertTrue(created)
                pages = [
                    "https://cdn.example.org/page-1.jpg",
                    "https://cdn.example.org/page-2.jpg",
                ]
                repository.save_native_reader_state(
                    manga_id,
                    "https://reader.example.org/manga/1/chapter/2",
                    pages,
                    1,
                )
                state = repository.get_native_reader_state(manga_id)

        self.assertIsNotNone(state)
        self.assertEqual(pages, state["image_urls"])
        self.assertEqual(1, state["page_index"])
        self.assertEqual(
            "https://reader.example.org/manga/1/chapter/2",
            state["source_url"],
        )

    def test_native_reader_position_is_clamped_to_available_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("data.repository.storage_root", return_value=root / "app-data"):
                repository = MangaRepository(db_path=root / "manga.db")
                manga_id, _ = repository.add_online_manga(
                    title="Example Manga",
                    source_uri="https://reader.example.org/manga/1",
                )
                repository.save_native_reader_state(
                    manga_id,
                    "https://reader.example.org/chapter/1",
                    ["https://cdn.example.org/page-1.jpg"],
                    99,
                )
                state = repository.get_native_reader_state(manga_id)

        self.assertEqual(0, state["page_index"])


if __name__ == "__main__":
    unittest.main()
