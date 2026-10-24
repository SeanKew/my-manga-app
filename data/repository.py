"""Database operations used by the library UI and import service."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from data.database import connection, initialize_database, storage_root


class MangaRepository:
    def __init__(self, db_path: str | Path | None = None):
        root = storage_root()
        self.db_path = Path(db_path) if db_path else root / "manga.db"
        self.library_dir = root / "library_files"
        self.library_dir.mkdir(parents=True, exist_ok=True)
        initialize_database(self.db_path)

    def find_by_hash(self, content_hash: str) -> dict | None:
        with connection(self.db_path) as db:
            row = db.execute("SELECT * FROM manga WHERE content_hash = ?", (content_hash,)).fetchone()
            return dict(row) if row else None

    def add_manga(
        self,
        title: str,
        source_uri: str,
        content_hash: str,
        cover_path: str,
        source_type: str = "local",
    ) -> tuple[int, bool]:
        existing = self.find_by_hash(content_hash)
        if existing:
            return int(existing["id"]), False
        with connection(self.db_path) as db:
            cursor = db.execute(
                """INSERT INTO manga(title, source_type, source_uri, content_hash, cover_path)
                   VALUES (?, ?, ?, ?, ?)""",
                (title, source_type, source_uri, content_hash, cover_path),
            )
            return int(cursor.lastrowid), True

    @staticmethod
    def _online_content_hash(title: str, catalog_id: str | int | None = None) -> str:
        clean_title = " ".join(str(title or "").split())
        identity = f"catalog:{catalog_id}" if catalog_id is not None else f"title:{clean_title.casefold()}"
        return hashlib.sha256(f"online-manga:{identity}".encode("utf-8")).hexdigest()

    def add_online_manga(
        self,
        title: str,
        source_uri: str,
        cover_url: str = "",
        catalog_id: str | int | None = None,
        in_library: bool = False,
    ) -> tuple[int, bool]:
        """Create/update a reading session; bookshelf membership is explicit."""
        clean_title = " ".join(str(title or "").split())
        clean_url = str(source_uri or "").strip()
        if not clean_title or not clean_url:
            raise ValueError("漫画标题和阅读来源不能为空")

        content_hash = self._online_content_hash(clean_title, catalog_id)
        with connection(self.db_path) as db:
            row = db.execute(
                "SELECT id FROM manga WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()
            if row:
                db.execute(
                    """UPDATE manga
                       SET cover_path = CASE WHEN ? <> '' THEN ? ELSE cover_path END,
                           is_in_library = CASE WHEN ? = 1 THEN 1 ELSE is_in_library END
                       WHERE id = ?""",
                    (cover_url, cover_url, int(in_library), row["id"]),
                )
                return int(row["id"]), False

            cursor = db.execute(
                """INSERT INTO manga(
                       title, source_type, source_uri, content_hash, cover_path, is_in_library
                   ) VALUES (?, 'online', ?, ?, ?, ?)""",
                (clean_title, clean_url, content_hash, cover_url, int(in_library)),
            )
            return int(cursor.lastrowid), True

    def add_to_library(self, manga_id: int) -> None:
        """Make an existing online reading session visible on the bookshelf."""
        with connection(self.db_path) as db:
            db.execute("UPDATE manga SET is_in_library = 1 WHERE id = ?", (manga_id,))

    def is_online_manga_in_library(
        self, title: str, catalog_id: str | int | None = None
    ) -> bool:
        """Return whether an online title is currently saved to the bookshelf."""
        content_hash = self._online_content_hash(title, catalog_id)
        with connection(self.db_path) as db:
            row = db.execute(
                "SELECT is_in_library FROM manga WHERE content_hash = ?",
                (content_hash,),
            ).fetchone()
        return bool(row and row["is_in_library"])

    def add_chapter(self, manga_id: int, title: str, chapter_index: int, page_paths: Iterable[str]) -> int:
        with connection(self.db_path) as db:
            cursor = db.execute(
                """INSERT INTO chapter(manga_id, title, chapter_index, page_paths_json)
                   VALUES (?, ?, ?, ?)""",
                (manga_id, title, chapter_index, json.dumps(list(page_paths), ensure_ascii=False)),
            )
            return int(cursor.lastrowid)

    def list_manga(
        self,
        query: str = "",
        favorites_only: bool = False,
        category_id: int | None = None,
    ) -> list[dict]:
        sql = """SELECT DISTINCT m.* FROM manga m"""
        params: list[object] = []
        if category_id is not None:
            sql += " JOIN manga_category mc ON mc.manga_id = m.id"
        sql += " WHERE m.is_in_library = 1"
        if query.strip():
            sql += " AND m.title LIKE ?"
            params.append(f"%{query.strip()}%")
        if favorites_only:
            sql += " AND m.is_favorite = 1"
        if category_id is not None:
            sql += " AND mc.category_id = ?"
            params.append(category_id)
        sql += " ORDER BY m.created_at DESC, m.id DESC"
        with connection(self.db_path) as db:
            return [dict(row) for row in db.execute(sql, params).fetchall()]

    def get_manga(self, manga_id: int) -> dict | None:
        with connection(self.db_path) as db:
            row = db.execute("SELECT * FROM manga WHERE id = ?", (manga_id,)).fetchone()
            return dict(row) if row else None

    def set_favorite(self, manga_id: int, favorite: bool) -> None:
        with connection(self.db_path) as db:
            db.execute("UPDATE manga SET is_favorite = ? WHERE id = ?", (int(favorite), manga_id))

    def delete_manga(self, manga_id: int) -> None:
        with connection(self.db_path) as db:
            db.execute("DELETE FROM manga WHERE id = ?", (manga_id,))

    def list_chapters(self, manga_id: int) -> list[dict]:
        with connection(self.db_path) as db:
            rows = db.execute(
                "SELECT * FROM chapter WHERE manga_id = ? ORDER BY chapter_index",
                (manga_id,),
            ).fetchall()
        chapters = []
        for row in rows:
            item = dict(row)
            item["page_paths"] = json.loads(item.pop("page_paths_json"))
            chapters.append(item)
        return chapters

    def get_progress(self, manga_id: int) -> dict | None:
        with connection(self.db_path) as db:
            row = db.execute("SELECT * FROM reading_progress WHERE manga_id = ?", (manga_id,)).fetchone()
            return dict(row) if row else None

    def save_progress(self, manga_id: int, chapter_id: int, page_index: int) -> None:
        with connection(self.db_path) as db:
            db.execute(
                """INSERT INTO reading_progress(manga_id, chapter_id, page_index, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(manga_id) DO UPDATE SET
                     chapter_id = excluded.chapter_id,
                     page_index = excluded.page_index,
                     updated_at = CURRENT_TIMESTAMP""",
                (manga_id, chapter_id, max(0, page_index)),
            )

    def save_online_progress(self, manga_id: int, source_url: str, scroll_y: int) -> None:
        """Save the current web page URL and vertical scroll position for an online manga."""
        with connection(self.db_path) as db:
            db.execute(
                """INSERT INTO reading_progress(manga_id, chapter_id, page_index, updated_at, source_url)
                   VALUES (?, NULL, ?, CURRENT_TIMESTAMP, ?)
                   ON CONFLICT(manga_id) DO UPDATE SET
                     chapter_id = NULL,
                     page_index = excluded.page_index,
                     updated_at = CURRENT_TIMESTAMP,
                     source_url = excluded.source_url""",
                (manga_id, max(0, int(scroll_y)), str(source_url or "")),
            )

    def save_native_reader_state(
        self,
        manga_id: int,
        source_url: str,
        image_urls: Iterable[str],
        page_index: int,
    ) -> None:
        """Persist extracted page URLs and the current native-reader page."""
        clean_urls = [str(url).strip() for url in image_urls if str(url).strip()][:250]
        if not clean_urls:
            raise ValueError("在线阅读页面列表不能为空")
        with connection(self.db_path) as db:
            db.execute(
                """INSERT INTO online_reader_state(
                       manga_id, source_url, image_urls_json, page_index, updated_at
                   ) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(manga_id) DO UPDATE SET
                     source_url = excluded.source_url,
                     image_urls_json = excluded.image_urls_json,
                     page_index = excluded.page_index,
                     updated_at = CURRENT_TIMESTAMP""",
                (
                    manga_id,
                    str(source_url or ""),
                    json.dumps(clean_urls, ensure_ascii=False),
                    max(0, min(int(page_index), len(clean_urls) - 1)),
                ),
            )

    def get_native_reader_state(self, manga_id: int) -> dict | None:
        """Load the last extracted pages for an online manga, if any."""
        with connection(self.db_path) as db:
            row = db.execute(
                "SELECT * FROM online_reader_state WHERE manga_id = ?",
                (manga_id,),
            ).fetchone()
        if not row:
            return None
        item = dict(row)
        try:
            urls = json.loads(item.pop("image_urls_json", "[]"))
        except (TypeError, json.JSONDecodeError):
            urls = []
        item["image_urls"] = [url for url in urls if isinstance(url, str)]
        return item

    def list_categories(self) -> list[dict]:
        with connection(self.db_path) as db:
            return [dict(row) for row in db.execute("SELECT * FROM category ORDER BY name").fetchall()]

    def add_category(self, name: str) -> int:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("分类名称不能为空")
        with connection(self.db_path) as db:
            db.execute("INSERT OR IGNORE INTO category(name) VALUES (?)", (clean_name,))
            row = db.execute("SELECT id FROM category WHERE name = ?", (clean_name,)).fetchone()
            return int(row["id"])

    def assign_category(self, manga_id: int, category_id: int, assigned: bool = True) -> None:
        with connection(self.db_path) as db:
            if assigned:
                db.execute(
                    "INSERT OR IGNORE INTO manga_category(manga_id, category_id) VALUES (?, ?)",
                    (manga_id, category_id),
                )
            else:
                db.execute(
                    "DELETE FROM manga_category WHERE manga_id = ? AND category_id = ?",
                    (manga_id, category_id),
                )
