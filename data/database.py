"""SQLite storage helpers for Manga.app."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def storage_root() -> Path:
    """Return Flet's durable app data directory, with a dev fallback."""
    configured = os.environ.get("FLET_APP_STORAGE_DATA")
    root = Path(configured).expanduser() if configured else Path.cwd() / ".manga-data"
    root.mkdir(parents=True, exist_ok=True)
    return root


def connect(db_path: str | Path) -> sqlite3.Connection:
    connection = sqlite3.connect(str(db_path), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize_database(db_path: str | Path) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS manga (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                source_type TEXT NOT NULL DEFAULT 'local',
                source_uri TEXT NOT NULL DEFAULT '',
                content_hash TEXT UNIQUE,
                cover_path TEXT NOT NULL DEFAULT '',
                is_favorite INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chapter (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                chapter_index INTEGER NOT NULL,
                page_paths_json TEXT NOT NULL,
                UNIQUE(manga_id, chapter_index)
            );

            CREATE TABLE IF NOT EXISTS reading_progress (
                manga_id INTEGER PRIMARY KEY REFERENCES manga(id) ON DELETE CASCADE,
                chapter_id INTEGER REFERENCES chapter(id) ON DELETE SET NULL,
                page_index INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS category (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE COLLATE NOCASE
            );

            CREATE TABLE IF NOT EXISTS manga_category (
                manga_id INTEGER NOT NULL REFERENCES manga(id) ON DELETE CASCADE,
                category_id INTEGER NOT NULL REFERENCES category(id) ON DELETE CASCADE,
                PRIMARY KEY (manga_id, category_id)
            );

            CREATE INDEX IF NOT EXISTS idx_manga_title ON manga(title COLLATE NOCASE);
            CREATE INDEX IF NOT EXISTS idx_chapter_manga ON chapter(manga_id, chapter_index);
            """
        )
