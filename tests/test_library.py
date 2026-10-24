import tempfile
import unittest
import zipfile
from io import BytesIO
from pathlib import Path

from data.repository import MangaRepository
from services.local_import_service import import_local_file


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.repo = MangaRepository(db_path=root / "manga.db")
        self.repo.library_dir = root / "library_files"
        self.repo.library_dir.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_favorite_search_and_category(self):
        manga_id, created = self.repo.add_manga("Sample", "local://sample", "hash-a", "/cover.jpg")
        self.assertTrue(created)
        self.repo.set_favorite(manga_id, True)
        category_id = self.repo.add_category("Sci-fi")
        self.repo.assign_category(manga_id, category_id)
        self.assertEqual([manga_id], [item["id"] for item in self.repo.list_manga("amp", True, category_id)])
        self.assertEqual([], self.repo.list_manga("missing"))

    def test_reading_progress_persists(self):
        manga_id, _ = self.repo.add_manga("Sample", "local://sample", "hash-b", "/cover.jpg")
        chapter_id = self.repo.add_chapter(manga_id, "Chapter 1", 0, ["/p1.jpg", "/p2.jpg"])
        self.repo.save_progress(manga_id, chapter_id, 1)
        self.assertEqual(1, self.repo.get_progress(manga_id)["page_index"])

    def test_import_cbz_and_detect_duplicate(self):
        archive_bytes = BytesIO()
        with zipfile.ZipFile(archive_bytes, "w") as archive:
            archive.writestr("page10.jpg", b"fake-image-10")
            archive.writestr("page2.jpg", b"fake-image-2")
        payload = archive_bytes.getvalue()
        first = import_local_file(self.repo, "demo.cbz", payload)
        second = import_local_file(self.repo, "demo.cbz", payload)
        self.assertTrue(first["created"])
        self.assertFalse(second["created"])
        chapter = self.repo.list_chapters(first["id"])[0]
        self.assertEqual(2, len(chapter["page_paths"]))
        self.assertEqual(b"fake-image-2", Path(chapter["page_paths"][0]).read_bytes())
        self.assertEqual(b"fake-image-10", Path(chapter["page_paths"][1]).read_bytes())


if __name__ == "__main__":
    unittest.main()
