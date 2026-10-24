"""Helpers for rendering local image pages."""
from __future__ import annotations

import base64
from pathlib import Path


def load_page_base64(path: str) -> str:
    image_path = Path(path)
    if not image_path.is_file():
        raise FileNotFoundError(f"漫画页面文件不存在：{image_path.name}")
    return base64.b64encode(image_path.read_bytes()).decode("ascii")
