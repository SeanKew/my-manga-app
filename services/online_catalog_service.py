"""Search manga metadata through the public AniList GraphQL API.

This service returns catalog metadata and official AniList page links. It does not
provide manga page images or bypass publisher access controls.
"""
from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_URL = "https://graphql.anilist.co"
SEARCH_QUERY = """
query ($search: String!) {
  Page(page: 1, perPage: 20) {
    media(search: $search, type: MANGA, isAdult: false, sort: [SEARCH_MATCH]) {
      id
      title { romaji english native }
      synonyms
      description(asHtml: false)
      coverImage { large extraLarge }
      siteUrl
      chapters
      volumes
      status
      averageScore
      genres
      startDate { year }
    }
  }
}
"""
DETAIL_QUERY = """
query ($id: Int!) {
  Media(id: $id, type: MANGA) {
    id
    title { romaji english native }
    synonyms
    description(asHtml: false)
    coverImage { large extraLarge }
    siteUrl
    chapters
    volumes
    status
    averageScore
    genres
    startDate { year }
    staff(perPage: 10, sort: [RELEVANCE]) {
      edges { role node { name { full } } }
    }
  }
}
"""


class MangaCatalogError(RuntimeError):
    """A network or API error while searching the online manga catalog."""


def _request(query: str, variables: dict) -> dict:
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Manga.app/0.1 (online catalog search)",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise MangaCatalogError(
            "无法连接在线漫画资料库，请检查网络后重试。"
        ) from exc

    if payload.get("errors"):
        message = payload["errors"][0].get("message", "在线资料库暂时不可用")
        raise MangaCatalogError(str(message)[:240])
    data = payload.get("data")
    if not isinstance(data, dict):
        raise MangaCatalogError("在线资料库返回了无法识别的数据。")
    return data


def search_manga(query: str) -> list[dict]:
    """Search public manga metadata. Empty queries return no results."""
    query = query.strip()
    if not query:
        return []
    data = _request(SEARCH_QUERY, {"search": query})
    page = data.get("Page") or {}
    media = page.get("media") or []
    return [item for item in media if isinstance(item, dict)]


def get_manga_details(media_id: int) -> dict:
    """Fetch public metadata for one AniList manga entry."""
    if not isinstance(media_id, int) or media_id <= 0:
        raise ValueError("漫画编号无效")
    data = _request(DETAIL_QUERY, {"id": media_id})
    media = data.get("Media")
    if not isinstance(media, dict):
        raise MangaCatalogError("没有找到这部漫画。")
    return media


def english_title(item: dict) -> str:
    """Pick the best English/romanized title for provider searches."""
    titles = item.get("title") or {}
    return titles.get("english") or titles.get("romaji") or titles.get("native") or "Untitled manga"


def chinese_title(item: dict) -> str | None:
    """Prefer Chinese aliases supplied by AniList, with safe common-title fallbacks."""
    import re

    titles = item.get("title") or {}
    english = titles.get("english") or ""
    romaji = titles.get("romaji") or ""
    native = titles.get("native") or ""
    for synonym in item.get("synonyms") or []:
        if isinstance(synonym, str) and re.search(r"[\u3400-\u9fff]", synonym):
            return synonym.strip()

    aliases = {
        "one punch man": "一拳超人",
        "one-punch man": "一拳超人",
        "one piece": "航海王／海贼王",
        "demon slayer: kimetsu no yaiba": "鬼灭之刃",
        "demon slayer": "鬼灭之刃",
        "jujutsu kaisen": "咒术回战",
        "chainsaw man": "电锯人",
        "spy x family": "间谍过家家",
        "attack on titan": "进击的巨人",
        "my hero academia": "我的英雄学院",
        "frieren: beyond journey's end": "葬送的芙莉莲",
        "solo leveling": "我独自升级",
        "blue lock": "蓝色监狱",
        "naruto": "火影忍者",
        "dragon ball": "龙珠",
        "sakamoto days": "坂本日常",
        "kaiju no. 8": "怪兽8号",
    }
    for candidate in (english, romaji, native):
        key = " ".join(str(candidate).casefold().split())
        if key in aliases:
            return aliases[key]
    return None


def display_title(item: dict) -> str:
    """Prefer a Chinese title when known; otherwise use a useful catalog title."""
    return chinese_title(item) or english_title(item)


def plain_description(item: dict, limit: int = 1200) -> str:
    """Remove basic HTML tags and decode common entities from API descriptions."""
    import re
    from html import unescape

    value = unescape(str(item.get("description") or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit] + ("…" if len(value) > limit else "")
