"""Non-destructive environment checks used by local development and CI."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REQUIRED_FILES = (
    Path("main.py"),
    Path("requirements.txt"),
    Path("data/database.py"),
    Path("data/repository.py"),
    Path("services/local_import_service.py"),
    Path("services/online_catalog_service.py"),
    Path("services/reading_sources_service.py"),
    Path("services/native_reading_service.py"),
    Path("tests/test_online_catalog.py"),
    Path("tests/test_reading_sources.py"),
    Path("tests/test_native_reading_service.py"),
    Path("tests/test_native_reader_state.py"),
    Path("ui/reader_page.py"),
)


def main() -> int:
    missing = [str(path) for path in REQUIRED_FILES if not path.is_file()]
    if missing:
        print("Missing required files:")
        for item in missing:
            print(f"  - {item}")
        return 1
    if importlib.util.find_spec("flet") is None:
        print("Missing dependency: flet. Run: python -m pip install -r requirements.txt")
        return 1
    if importlib.util.find_spec("flet_webview") is None:
        print("Missing dependency: flet-webview. Run: python -m pip install -r requirements.txt")
        return 1
    print("Environment check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
