"""Discover free and language-aware online manga reading sources.

Results are discovery links, not guarantees: platforms can vary by title, chapter,
language, region, sign-in requirements, and their own access terms.
"""
from __future__ import annotations

from urllib.parse import quote_plus


def _is_one_punch_man(*values: str) -> bool:
    joined = " ".join(values).casefold().replace("-", " ")
    return "one punch man" in joined or "一拳超人" in joined or "ワンパンマン" in joined


def discover_reading_sources(
    title: str,
    english_title: str | None = None,
) -> list[dict[str, str]]:
    """Return official platform links plus a Chinese-language discovery search."""
    title = " ".join(str(title or "").split())
    english_title = " ".join(str(english_title or "").split())
    if not title and not english_title:
        return []

    chinese_query = quote_plus(f"{title or english_title} 中文 漫画 官方 正版 免费 阅读")
    english_query = quote_plus(f"{english_title or title} manga official free chapters")
    viz_url = (
        "https://www.viz.com/shonenjump/chapters/one-punch-man?locale=en"
        if _is_one_punch_man(title, english_title)
        else f"https://www.viz.com/search?search={quote_plus(english_title or title)}"
    )

    return [
        {
            "id": "chinese_licensed_search",
            "name": "搜索中文正版免费阅读来源",
            "url": f"https://www.google.com/search?q={chinese_query}",
            "language": "简体中文 / 繁體中文",
            "description": "优先用中文标题寻找官方或获授权平台；搜索结果可能包含付费内容，需确认授权、免费章节和地区限制。",
            "availability": "搜索发现，未逐条验证",
        },
        {
            "id": "viz",
            "name": "VIZ / Shonen Jump",
            "url": viz_url,
            "language": "English",
            "description": "官方平台；《一拳超人》部分章节可免费阅读，但语言与可用地区有限制。",
            "availability": "以平台章节页为准",
        },
        {
            "id": "mangaplus",
            "name": "MANGA Plus by SHUEISHA",
            "url": f"https://www.google.com/search?q=site%3Amangaplus.shueisha.co.jp+{english_query}",
            "language": "依作品与地区而定",
            "description": "集英社官方平台；部分作品/章节免费，目录不一定收录此作品或提供中文。",
            "availability": "官方站内结果需确认",
        },
        {
            "id": "webtoon",
            "name": "WEBTOON 官方目录",
            "url": f"https://www.webtoons.com/en/search?keyword={quote_plus(title or english_title)}",
            "language": "多语言作品，依标题而定",
            "description": "官方漫画平台，提供许多免费作品；不保证收录正在搜索的日本漫画。",
            "availability": "官方目录需确认",
        },
    ]
