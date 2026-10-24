import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data.repository import MangaRepository


class ShelfMembershipTests(unittest.TestCase):
    def create_repository(self, root: Path) -> MangaRepository:
        return MangaRepository(db_path=root / "manga.db")

    def test_new_online_reader_session_is_not_automatically_on_shelf(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("data.repository.storage_root", return_value=root / "app-data"):
                repo = self.create_repository(root)
                manga_id, created = repo.add_online_manga(
                    title="Example Manga",
                    source_uri="https://reader.example.org/manga/1",
                    catalog_id=123,
                )
                visible = repo.list_manga()
                saved = repo.is_online_manga_in_library("Example Manga", 123)
                item = repo.get_manga(manga_id)

        self.assertTrue(created)
        self.assertEqual([], visible)
        self.assertFalse(saved)
        self.assertEqual(0, item["is_in_library"])

    def test_add_online_manga_to_shelf_makes_it_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("data.repository.storage_root", return_value=root / "app-data"):
                repo = self.create_repository(root)
                manga_id, _ = repo.add_online_manga(
                    title="Example Manga",
                    source_uri="https://reader.example.org/manga/1",
                    catalog_id=123,
                )
                repo.add_to_library(manga_id)
                visible = repo.list_manga()
                saved = repo.is_online_manga_in_library("Example Manga", 123)

        self.assertEqual([manga_id], [item["id"] for item in visible])
        self.assertTrue(saved)

    def test_duplicate_add_to_shelf_updates_existing_hidden_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("data.repository.storage_root", return_value=root / "app-data"):
                repo = self.create_repository(root)
                first_id, created = repo.add_online_manga(
                    title="Example Manga",
                    source_uri="https://reader.example.org/manga/1",
                    catalog_id=123,
                )
                second_id, duplicate_created = repo.add_online_manga(
                    title="Example Manga",
                    source_uri="https://reader.example.org/manga/1",
                    cover_url="https://cdn.example.org/cover.jpg",
                    catalog_id=123,
                    in_library=True,
                )
                visible = repo.list_manga()
                saved_item = repo.get_manga(second_id)

        self.assertTrue(created)
        self.assertFalse(duplicate_created)
        self.assertEqual(first_id, second_id)
        self.assertEqual([first_id], [item["id"] for item in visible])
        self.assertEqual(1, saved_item["is_in_library"])
        self.assertEqual("https://cdn.example.org/cover.jpg", saved_item["cover_path"])

    def test_delete_removes_online_item_and_saved_reader_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch("data.repository.storage_root", return_value=root / "app-data"):
                repo = self.create_repository(root)
                manga_id, _ = repo.add_online_manga(
                    title="Example Manga",
                    source_uri="https://reader.example.org/manga/1",
                    catalog_id=123,
                    in_library=True,
                )
                repo.save_native_reader_state(
                    manga_id,
                    "https://reader.example.org/chapter/1",
                    ["https://cdn.example.org/page-1.jpg"],
                    0,
                )
                repo.delete_manga(manga_id)
                visible = repo.list_manga()
                reader_state = repo.get_native_reader_state(manga_id)

        self.assertEqual([], visible)
        self.assertIsNone(reader_state)

    def test_existing_database_migrates_and_keeps_old_entries_visible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            db_path = root / "legacy.db"
            import sqlite3
            with sqlite3.connect(db_path) as db:
                db.execute(
                    """CREATE TABLE manga (
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           title TEXT NOT NULL,
                           source_type TEXT NOT NULL DEFAULT 'local',
                           source_uri TEXT NOT NULL DEFAULT '',
                           content_hash TEXT UNIQUE,
                           cover_path TEXT NOT NULL DEFAULT '',
                           is_favorite INTEGER NOT NULL DEFAULT 0,
                           created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                       )"""
                )
                db.execute(
                    "INSERT INTO manga(title, source_type, source_uri, content_hash) VALUES (?, ?, ?, ?)",
                    ("Old Manga", "local", "local-file", "old-hash"),
                )
            with patch("data.repository.storage_root", return_value=root / "app-data"):
                repo = MangaRepository(db_path=db_path)
                visible = repo.list_manga()

        self.assertEqual(["Old Manga"], [item["title"] for item in visible])
        self.assertEqual(1, visible[0]["is_in_library"])


if __name__ == "__main__":
    unittest.main()
