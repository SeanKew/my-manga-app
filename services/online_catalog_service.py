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


def display_title(item: dict) -> str:
    """Pick a useful title regardless of which language fields are populated."""
    titles = item.get("title") or {}
    return titles.get("english") or titles.get("native") or titles.get("romaji") or "未命名漫画"


def plain_description(item: dict, limit: int = 1200) -> str:
    """Remove basic HTML tags and decode common entities from API descriptions."""
    import re
    from html import unescape

    value = unescape(str(item.get("description") or ""))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value[:limit] + ("…" if len(value) > limit else "")
