"""Import local CBZ/ZIP archives and individual image files."""
from __future__ import annotations

import hashlib
import re
import shutil
import uuid
import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath

from data.repository import MangaRepository

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ARCHIVE_EXTENSIONS = {".cbz", ".zip"}
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_UNPACKED_BYTES = 300 * 1024 * 1024
MAX_PAGES = 1500


def _natural_key(value: str) -> list[object]:
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", value)]


def import_local_file(repository: MangaRepository, filename: str, payload: bytes) -> dict:
    """Persist an imported item; returns its id and whether a new item was created."""
    if not payload:
        raise ValueError("文件内容为空")
    if len(payload) > MAX_ARCHIVE_BYTES:
        raise ValueError("文件超过 100 MB，请先压缩或拆分后再导入")

    name = Path(filename).name
    extension = Path(name).suffix.lower()
    if extension not in IMAGE_EXTENSIONS | ARCHIVE_EXTENSIONS:
        raise ValueError("目前只支持 CBZ、ZIP、JPG、JPEG、PNG、WEBP 和 GIF 文件")

    content_hash = hashlib.sha256(payload).hexdigest()
    existing = repository.find_by_hash(content_hash)
    if existing:
        return {"id": int(existing["id"]), "created": False, "title": existing["title"]}

    import_id = uuid.uuid4().hex
    target_dir = repository.library_dir / import_id
    target_dir.mkdir(parents=True, exist_ok=False)
    page_paths: list[str] = []

    try:
        if extension in ARCHIVE_EXTENSIONS:
            with zipfile.ZipFile(BytesIO(payload)) as archive:
                candidates = []
                unpacked_total = 0
                for info in archive.infolist():
                    if info.is_dir():
                        continue
                    member = PurePosixPath(info.filename)
                    if member.is_absolute() or ".." in member.parts:
                        continue
                    if member.suffix.lower() not in IMAGE_EXTENSIONS:
                        continue
                    if info.file_size < 0:
                        continue
                    unpacked_total += info.file_size
                    if unpacked_total > MAX_UNPACKED_BYTES:
                        raise ValueError("解压后的图片总量超过 300 MB，已取消导入")
                    candidates.append(info)
                if not candidates:
                    raise ValueError("压缩包里没有找到支持的图片")
                if len(candidates) > MAX_PAGES:
                    raise ValueError("单个压缩包最多支持 1500 张图片")
                candidates.sort(key=lambda item: _natural_key(item.filename))
                for index, info in enumerate(candidates, start=1):
                    output = target_dir / f"{index:05d}{info.filename and Path(info.filename).suffix.lower()}"
                    with archive.open(info) as source, output.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
                    page_paths.append(str(output))
        else:
            output = target_dir / f"00001{extension}"
            output.write_bytes(payload)
            page_paths.append(str(output))

        title = Path(name).stem.strip() or "未命名漫画"
        manga_id, created = repository.add_manga(
            title=title,
            source_uri=f"local://{import_id}/{name}",
            content_hash=content_hash,
            cover_path=page_paths[0],
            source_type="local",
        )
        if not created:
            shutil.rmtree(target_dir, ignore_errors=True)
            existing = repository.get_manga(manga_id)
            return {"id": manga_id, "created": False, "title": existing["title"] if existing else title}

        repository.add_chapter(manga_id, "第 1 话", 0, page_paths)
        return {"id": manga_id, "created": True, "title": title}
    except Exception:
        shutil.rmtree(target_dir, ignore_errors=True)
        raise
