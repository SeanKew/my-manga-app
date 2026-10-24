"""Discover candidate legal/free online reading sources.

This module only creates links to known publisher/platform pages. It does not
scrape chapter images, bypass paywalls, or claim a title is available before the
user checks the provider's own catalog and regional terms.
"""
from __future__ import annotations

from urllib.parse import quote_plus


def discover_reading_sources(title: str) -> list[dict[str, str]]:
    """Return curated official reading destinations for a non-empty title."""
    title = " ".join(str(title or "").split())
    if not title:
        return []

    query = quote_plus(title)
    return [
        {
            "id": "mangaplus",
            "name": "MANGA Plus by SHUEISHA",
            "url": "https://mangaplus.shueisha.co.jp/",
            "description": "集英社官方漫画平台；部分作品和章节可免费阅读，具体取决于作品及地区。",
            "availability": "需在官方目录确认",
        },
        {
            "id": "webtoon",
            "name": "WEBTOON",
            "url": f"https://www.webtoons.com/en/search?keyword={query}",
            "description": "官方漫画平台；包含免费作品，部分内容或功能可能有地区及账号限制。",
            "availability": "打开官方搜索确认",
        },
        {
            "id": "anilist",
            "name": "AniList 作品资料",
            "url": "https://anilist.co/search/manga",
            "description": "用于核对作品资料和相关链接，不是章节阅读服务。",
            "availability": "资料来源",
        },
    ]
