"""Manga.app: local manga library and reader MVP."""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from urllib.parse import urlparse

import flet as ft

try:
    import flet_webview as fwv
except ImportError:
    # Keep the rest of the app usable in runtimes that did not bundle the extension.
    fwv = None

from data.repository import MangaRepository
from services.local_import_service import import_local_file
from services.online_catalog_service import MangaCatalogError, display_title, english_title, plain_description, search_manga
from services.reading_sources_service import discover_reading_sources
from ui.reader_page import load_page_base64


def has_chinese_text(value: str) -> bool:
    return any(0x3400 <= ord(char) <= 0x9fff for char in value)


def main(page: ft.Page):
    page.title = "Manga.app"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 12
    page.spacing = 10

    repository = MangaRepository()
    picker = ft.FilePicker()
    page.services.append(picker)
    url_launcher = ft.UrlLauncher()
    page.services.append(url_launcher)

    status = ft.Text("准备就绪。支持 CBZ/ZIP 漫画压缩包和单张图片。", color=ft.Colors.GREY_400)
    search_box = ft.TextField(
        label="搜索漫画",
        hint_text="输入漫画名称",
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda _: refresh_library(),
        expand=True,
    )
    favorites_only = ft.Checkbox(
        label="只看收藏",
        value=False,
        on_change=lambda _: refresh_library(),
    )
    import_category = ft.TextField(
        label="导入时添加到分类（可选）",
        hint_text="例如：待阅读",
    )
    manga_list = ft.ListView(expand=True, spacing=8, auto_scroll=False)

    def show_status(message: str, error: bool = False):
        status.value = message
        status.color = ft.Colors.RED_300 if error else ft.Colors.GREY_400
        page.update()

    async def open_online_url(url: str, in_app: bool = False):
        """Open a discovered reading link with an awaited Flet URL launcher."""
        try:
            if in_app:
                await url_launcher.launch_url(
                    url,
                    mode=ft.LaunchMode.IN_APP_WEB_VIEW,
                    web_view_configuration=ft.WebViewConfiguration(
                        enable_javascript=True,
                        enable_dom_storage=True,
                    ),
                )
            else:
                await url_launcher.launch_url(
                    url,
                    mode=ft.LaunchMode.EXTERNAL_APPLICATION,
                )
        except Exception as ex:
            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("无法打开链接"),
                content=ft.Text(
                    "系统未能打开这个页面。请确认网络连接，或改用外部浏览器。\n"
                    f"错误信息：{str(ex)[:240]}"
                ),
                actions=[
                    ft.TextButton("关闭", on_click=lambda e: page.pop_dialog()),
                ],
            )
            page.show_dialog(dialog)

    def open_source_in_app(source: dict, manga: dict):
        target_url = str(source.get("url") or "")
        parsed = urlparse(target_url)
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            show_status("这个来源不是有效的网页地址。", error=True)
            return
        title = display_title(manga)
        cover_url = (manga.get("coverImage") or {}).get("large") or (manga.get("coverImage") or {}).get("extraLarge") or ""
        manga_id, _created = repository.add_online_manga(
            title=title,
            source_uri=target_url,
            cover_url=cover_url,
            catalog_id=manga.get("id"),
        )
        try:
            page.pop_dialog()
        except Exception:
            pass
        open_online_reader(manga_id, target_url, title, cover_url=cover_url, initial_scroll=0)

    def build_source_card(source: dict, manga: dict) -> ft.Control:
        url = source["url"]
        return ft.Container(
            padding=10,
            border=ft.Border.all(1, ft.Colors.GREY_800),
            border_radius=10,
            content=ft.Column(
                [
                    ft.Text(source["name"], weight=ft.FontWeight.BOLD),
                    ft.Text(
                        f"语言：{source.get('language', '依平台而定')} · {source.get('availability', '需确认')}",
                        size=12,
                        color=ft.Colors.GREY_400,
                    ),
                    ft.Text(source.get("description", ""), size=12),
                    ft.Row(
                        [
                            ft.TextButton(
                                "在 Manga.app 内阅读",
                                on_click=lambda e, item=source, book=manga: open_source_in_app(item, book),
                            ),
                            ft.TextButton(
                                "外部浏览器打开",
                                on_click=lambda e, target=url: page.run_task(open_online_url, target, False),
                            ),
                        ],
                        wrap=True,
                    ),
                ],
                tight=True,
                spacing=4,
            ),
        )

    def refresh_library():
        manga_list.controls.clear()
        items = repository.list_manga(
            query=search_box.value or "",
            favorites_only=bool(favorites_only.value),
        )
        if not items:
            manga_list.controls.append(
                ft.Container(
                    padding=24,
                    content=ft.Text("资料库还是空的。点击「导入漫画」添加 CBZ、ZIP 或图片文件。"),
                )
            )
        for item in items:
            chapters = repository.list_chapters(item["id"])
            page_count = sum(len(chapter["page_paths"]) for chapter in chapters)
            progress = repository.get_progress(item["id"])
            is_online = item.get("source_type") == "online"
            if is_online:
                progress_text = "点击继续在线阅读"
                if progress and progress.get("source_url"):
                    progress_text = "上次阅读位置已保存"
                page_summary = "在线漫画"
            else:
                progress_text = "尚未阅读"
                if progress:
                    progress_text = f"上次阅读第 {progress['page_index'] + 1} 页"
                page_summary = f"{page_count} 页"
            cover_path = item.get("cover_path") or ""
            cover_control = (
                ft.Image(src=cover_path, width=54, height=76, fit=ft.BoxFit.CONTAIN)
                if is_online and cover_path.startswith(("https://", "http://"))
                else ft.Icon(ft.Icons.MENU_BOOK, size=34, color=ft.Colors.CYAN_300)
            )
            manga_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Row(
                            [
                                cover_control,
                                ft.Column(
                                    [
                                        ft.Text(item["title"], weight=ft.FontWeight.BOLD, max_lines=2),
                                        ft.Text(
                                            f"{page_summary} · {progress_text}",
                                            size=12,
                                            color=ft.Colors.GREY_400,
                                        ),
                                    ],
                                    expand=True,
                                    spacing=4,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.FAVORITE if item["is_favorite"] else ft.Icons.FAVORITE_BORDER,
                                    icon_color=ft.Colors.PINK_300 if item["is_favorite"] else None,
                                    tooltip="取消收藏" if item["is_favorite"] else "收藏",
                                    on_click=lambda e, manga_id=item["id"], fav=bool(item["is_favorite"]):
                                        toggle_favorite(manga_id, not fav),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                                    tooltip="继续阅读",
                                    on_click=lambda e, manga_id=item["id"]: open_reader(manga_id),
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                    )
                )
            )
        page.update()

    def toggle_favorite(manga_id: int, favorite: bool):
        repository.set_favorite(manga_id, favorite)
        refresh_library()
        show_status("已更新收藏状态。")

    async def import_files(_):
        try:
            files = await picker.pick_files(
                dialog_title="选择漫画文件",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["cbz", "zip", "jpg", "jpeg", "png", "webp", "gif"],
                allow_multiple=True,
                with_data=True,
            )
            if not files:
                show_status("已取消导入。")
                return

            imported = 0
            duplicates = 0
            category_name = (import_category.value or "").strip()
            category_id = repository.add_category(category_name) if category_name else None

            for file in files:
                payload = getattr(file, "bytes", None)
                if payload is None and getattr(file, "path", None):
                    payload = Path(file.path).read_bytes()
                if payload is None:
                    raise ValueError(f"无法读取文件内容：{file.name}")
                result = import_local_file(repository, file.name, payload)
                if result["created"]:
                    imported += 1
                    if category_id is not None:
                        repository.assign_category(result["id"], category_id)
                else:
                    duplicates += 1

            refresh_library()
            show_status(f"导入完成：新增 {imported} 项，跳过重复 {duplicates} 项。")
        except Exception as ex:
            show_status(f"导入失败：{ex}", error=True)

    def open_reader(manga_id: int):
        manga = repository.get_manga(manga_id)
        if not manga:
            show_status("找不到这本漫画。", error=True)
            return
        if manga.get("source_type") == "online":
            progress = repository.get_progress(manga_id) or {}
            source_url = progress.get("source_url") or manga.get("source_uri") or ""
            if not source_url:
                show_status("这本在线漫画还没有阅读来源，请重新从在线发现页打开。", error=True)
                return
            open_online_reader(
                manga_id,
                source_url,
                manga["title"],
                cover_url=manga.get("cover_path") or "",
                initial_scroll=int(progress.get("page_index") or 0),
            )
            return
        chapters = repository.list_chapters(manga_id)
        if not chapters or not chapters[0]["page_paths"]:
            show_status("这本漫画没有可阅读的页面。", error=True)
            return
        progress = repository.get_progress(manga_id)
        chapter = next(
            (item for item in chapters if progress and item["id"] == progress["chapter_id"]),
            chapters[0],
        )
        page_index = 0
        if progress and progress["chapter_id"] == chapter["id"]:
            page_index = min(max(0, progress["page_index"]), len(chapter["page_paths"]) - 1)
        render_reader(manga, chapter, page_index)

    def render_reader(manga: dict, chapter: dict, page_index: int):
        page_paths = chapter["page_paths"]
        page_index = min(max(0, page_index), len(page_paths) - 1)
        repository.save_progress(manga["id"], chapter["id"], page_index)

        try:
            image_base64 = load_page_base64(page_paths[page_index])
            image_control = ft.Image(
                src_base64=image_base64,
                fit=ft.BoxFit.CONTAIN,
                width=page.width,
                height=max(300, (page.height or 800) - 190),
            )
            image_area = ft.Container(
                content=image_control,
                expand=True,
                alignment=ft.Alignment.CENTER,
            )
        except Exception as ex:
            image_area = ft.Container(
                expand=True,
                alignment=ft.Alignment.CENTER,
                content=ft.Text(f"无法打开图片：{ex}", color=ft.Colors.RED_300),
            )

        def back_to_library(_):
            page.clean()
            build_library_view()

        def move_page(delta: int):
            next_index = page_index + delta
            if 0 <= next_index < len(page_paths):
                render_reader(manga, chapter, next_index)
            else:
                show_status("已经是本章的最后一页。" if delta > 0 else "已经是本章的第一页。")

        page.clean()
        page.add(
            ft.AppBar(
                title=ft.Text(manga["title"], max_lines=1),
                leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=back_to_library),
            ),
            ft.Text(f"{chapter['title']} · 第 {page_index + 1} / {len(page_paths)} 页"),
            ft.ProgressBar(value=(page_index + 1) / len(page_paths)),
            image_area,
            ft.Row(
                [
                    ft.Button(
                        content="上一页",
                        icon=ft.Icons.CHEVRON_LEFT,
                        disabled=page_index == 0,
                        on_click=lambda _: move_page(-1),
                        width=150,
                    ),
                    ft.Button(
                        content="下一页",
                        icon=ft.Icons.CHEVRON_RIGHT,
                        disabled=page_index >= len(page_paths) - 1,
                        on_click=lambda _: move_page(1),
                        width=150,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Text("阅读进度已自动保存。", size=12, color=ft.Colors.GREY_400),
        )
        page.update()


    def open_online_reader(
        manga_id: int,
        initial_url: str,
        title: str,
        cover_url: str = "",
        initial_scroll: int = 0,
    ):
        """Read provider-owned pages in-app and persist the URL + scroll position."""
        parsed = urlparse(str(initial_url or ""))
        if parsed.scheme not in {"https", "http"} or not parsed.netloc:
            show_status("无法在阅读器中打开：来源地址无效。", error=True)
            return
        if fwv is None:
            show_status(
                "当前安装包缺少内置网页组件，正在尝试用外部浏览器打开。请重新安装最新构建以启用应用内阅读。",
                error=True,
            )
            page.run_task(open_online_url, initial_url, False)
            return
        manga = repository.get_manga(manga_id)
        if not manga:
            show_status("找不到这本漫画。", error=True)
            return

        state = {
            "url": initial_url,
            "scroll_y": max(0, int(initial_scroll)),
            "restore_y": max(0, int(initial_scroll)),
            "last_saved_y": -1,
            "last_saved_at": 0.0,
            "restore_pending": int(initial_scroll) > 0,
        }
        page.padding = 0
        reading_status = ft.Text(
            "正在启用 JavaScript 并加载网页……",
            size=12,
            color=ft.Colors.GREY_400,
        )
        favorite_button = ft.IconButton(
            icon=ft.Icons.FAVORITE if manga.get("is_favorite") else ft.Icons.FAVORITE_BORDER,
            icon_color=ft.Colors.PINK_300 if manga.get("is_favorite") else None,
            tooltip="取消收藏" if manga.get("is_favorite") else "收藏这部漫画",
        )

        def save_position(force: bool = False):
            now = time.monotonic()
            if not force and now - state["last_saved_at"] < 1.0:
                return
            repository.save_online_progress(manga_id, state["url"], state["scroll_y"])
            state["last_saved_y"] = state["scroll_y"]
            state["last_saved_at"] = now
            reading_status.value = "阅读位置已自动保存"

        def on_web_scroll(event):
            try:
                state["scroll_y"] = max(0, int(float(event.y)))
            except (TypeError, ValueError, AttributeError):
                return
            save_position()

        def on_url_change(event):
            changed_url = str(getattr(event, "data", "") or "")
            parsed_url = urlparse(changed_url)
            if parsed_url.scheme not in {"https", "http"} or not parsed_url.netloc:
                return
            state["url"] = changed_url
            if state["restore_pending"]:
                repository.save_online_progress(manga_id, state["url"], state["restore_y"])
                return
            state["scroll_y"] = 0
            repository.save_online_progress(manga_id, state["url"], 0)
            reading_status.value = "章节地址已更新，阅读位置自动保存"

        def on_web_error(event):
            error_text = str(getattr(event, "data", "") or "未知错误")
            reading_status.value = f"部分网页资源载入失败：{error_text[:100]}"
            page.update()

        # Start on a blank page so JavaScript can be enabled before the target
        # site begins its first navigation. Android WebView defaults may otherwise
        # leave JavaScript disabled for the initial request.
        webview = fwv.WebView(
            url="about:blank",
            expand=True,
            bgcolor="#111216",
            on_scroll=on_web_scroll,
            on_url_change=on_url_change,
            on_web_resource_error=on_web_error,
        )

        async def initialize_webview():
            try:
                await webview.set_javascript_mode(fwv.JavaScriptMode.UNRESTRICTED)
                await webview.load_request(initial_url)
                reading_status.value = "JavaScript 已启用，正在载入页面……"
            except Exception as ex:
                reading_status.value = (
                    "内嵌网页无法启用脚本或加载失败；请点击「外部打开」继续。"
                    f"（{str(ex)[:100]}）"
                )
            page.update()

        async def on_page_ended(_event):
            try:
                actual_url = await webview.get_current_url()
                if actual_url:
                    actual = urlparse(actual_url)
                    if actual.scheme in {"https", "http"} and actual.netloc:
                        state["url"] = actual_url
            except Exception:
                pass
            if state["restore_pending"]:
                try:
                    await asyncio.sleep(0.35)
                    await webview.scroll_to(0, state["restore_y"])
                    state["scroll_y"] = state["restore_y"]
                except Exception:
                    pass
                state["restore_pending"] = False
            save_position(force=True)
            page.update()

        webview.on_page_ended = on_page_ended

        def back_to_library(_event=None):
            save_position(force=True)
            page.padding = 12
            build_library_view()

        async def webpage_back(_event=None):
            try:
                if await webview.can_go_back():
                    await webview.go_back()
                else:
                    back_to_library()
            except Exception:
                back_to_library()

        async def reload_page(_event=None):
            try:
                await webview.reload()
            except Exception as ex:
                reading_status.value = f"刷新失败：{str(ex)[:120]}"
                page.update()

        async def open_current_in_browser(_event=None):
            try:
                current_url = await webview.get_current_url()
            except Exception:
                current_url = state["url"]
            await open_online_url(current_url or state["url"], False)

        def toggle_online_favorite(_event=None):
            current = repository.get_manga(manga_id) or {}
            favorite = not bool(current.get("is_favorite"))
            repository.set_favorite(manga_id, favorite)
            favorite_button.icon = ft.Icons.FAVORITE if favorite else ft.Icons.FAVORITE_BORDER
            favorite_button.icon_color = ft.Colors.PINK_300 if favorite else None
            favorite_button.tooltip = "取消收藏" if favorite else "收藏这部漫画"
            page.update()

        favorite_button.on_click = toggle_online_favorite
        page.clean()
        page.add(
            ft.SafeArea(
                expand=True,
                content=ft.Column(
                    expand=True,
                    spacing=0,
                    controls=[
                        ft.Container(
                            padding=8,
                            content=ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.ARROW_BACK,
                                        tooltip="返回书架",
                                        on_click=back_to_library,
                                    ),
                                    ft.Text(title, weight=ft.FontWeight.BOLD, max_lines=1, expand=True),
                                    favorite_button,
                                ],
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            ),
                        ),
                        ft.Divider(height=1, color=ft.Colors.GREY_800),
                        ft.Container(content=webview, expand=True),
                        ft.Divider(height=1, color=ft.Colors.GREY_800),
                        ft.Container(
                            padding=8,
                            content=ft.Column(
                                [
                                    ft.Row(
                                        [
                                            ft.TextButton(
                                                "网页后退",
                                                icon=ft.Icons.ARROW_BACK,
                                                on_click=lambda e: page.run_task(webpage_back),
                                            ),
                                            ft.TextButton(
                                                "刷新",
                                                icon=ft.Icons.REFRESH,
                                                on_click=lambda e: page.run_task(reload_page),
                                            ),
                                            ft.TextButton(
                                                "外部打开",
                                                icon=ft.Icons.OPEN_IN_BROWSER,
                                                on_click=lambda e: page.run_task(open_current_in_browser),
                                            ),
                                        ],
                                        wrap=True,
                                    ),
                                    reading_status,
                                ],
                                spacing=2,
                            ),
                        ),
                    ],
                ),
            )
        )
        page.update()
        # The WebView must be attached to the page before native methods are called.
        page.run_task(initialize_webview)

    async def run_online_search(query: str, results: ft.ListView, message: ft.Text, button: ft.Button):
        query = query.strip()
        if not query:
            message.value = "请输入漫画名称后再搜索。"
            results.controls.clear()
            page.update()
            return
        button.disabled = True
        message.value = "正在搜索漫画资料（支持中文、英文或日文标题）……"
        results.controls.clear()
        page.update()
        try:
            items = await asyncio.to_thread(search_manga, query)
            if not items:
                message.value = "没有找到资料，可以试试作品的英文、日文或中文别名。"
            else:
                message.value = f"找到 {len(items)} 条资料。详情页会列出可尝试的阅读来源；免费章节和中文版本以平台实际页面为准。"
                for item in items:
                    cover = (item.get("coverImage") or {}).get("large") or (item.get("coverImage") or {}).get("extraLarge")
                    title = display_title(item)
                    english_name = english_title(item)
                    year = (item.get("startDate") or {}).get("year") or "年份未知"
                    chapters = item.get("chapters")
                    chapter_text = f"{chapters} 话" if chapters else "话数未知"
                    score = item.get("averageScore")
                    subtitle = f"{year} · {chapter_text}" + (f" · 评分 {score}/100" if score else "")
                    if english_name and english_name != title:
                        subtitle = f"{english_name} · {subtitle}"
                    summary = plain_description(item, 180)
                    if not has_chinese_text(summary):
                        summary = "暂无中文简介；打开详情查找中文阅读来源。"
                    def show_details(_event, manga=item):
                        raw_description = plain_description(manga)
                        has_chinese_description = any("\u3400" <= ch <= "\u9fff" for ch in raw_description)
                        detail_text = (
                            raw_description
                            if has_chinese_description
                            else "目前没有可用的中文简介；请查看下方中文阅读来源或平台提供的语言选项。"
                        )
                        reading_sources = discover_reading_sources(
                            display_title(manga), english_title(manga)
                        )
                        source_controls = [build_source_card(source, manga) for source in reading_sources]
                        detail_dialog = ft.AlertDialog(
                            modal=True,
                            title=ft.Text(display_title(manga)),
                            content=ft.Container(
                                width=420,
                                content=ft.Column(
                                    [
                                        ft.Text(f"状态：{manga.get('status') or '未知'}"),
                                        ft.Text(f"章节：{manga.get('chapters') or '未知'} · 卷数：{manga.get('volumes') or '未知'}"),
                                        ft.Text("类型：" + "、".join(manga.get("genres") or []) if manga.get("genres") else "类型：未知"),
                                        ft.Text(detail_text, selectable=True),
                                        ft.Text(
                                            "下列链接分别打开应用内网页或外部浏览器。平台可能只提供部分免费章节，并可能因地区、语言或账号而不同。",
                                            color=ft.Colors.GREY_400,
                                        ),
                                        *source_controls,
                                    ],
                                    tight=True,
                                    scroll=ft.ScrollMode.AUTO,
                                ),
                            ),
                            actions=[
                                ft.TextButton(
                                    "打开 AniList 资料",
                                    on_click=lambda e, url=manga.get("siteUrl"): page.run_task(open_online_url, url, False) if url else None,
                                ),
                                ft.TextButton("关闭", on_click=lambda e: close_details(detail_dialog)),
                            ],
                            actions_alignment=ft.MainAxisAlignment.END,
                        )
                        page.show_dialog(detail_dialog)
                    results.controls.append(
                        ft.Card(
                            content=ft.Container(
                                padding=10,
                                content=ft.Row(
                                    [
                                        ft.Image(src=cover, width=76, height=108, fit=ft.BoxFit.CONTAIN)
                                        if cover else ft.Container(width=76, height=108, alignment=ft.Alignment.CENTER, content=ft.Icon(ft.Icons.MENU_BOOK)),
                                        ft.Column(
                                            [
                                                ft.Text(title, weight=ft.FontWeight.BOLD, max_lines=3),
                                                ft.Text(subtitle, size=12, color=ft.Colors.GREY_400),
                                                ft.Text(summary, size=12, max_lines=3),
                                                ft.TextButton("查看详情", on_click=show_details),
                                            ],
                                            expand=True,
                                            spacing=4,
                                        ),
                                    ],
                                    vertical_alignment=ft.CrossAxisAlignment.START,
                                ),
                            ),
                        )
                    )
        except MangaCatalogError as ex:
            message.value = f"联网搜索失败：{ex}"
        except Exception as ex:
            message.value = f"搜索时发生错误：{ex}"
        finally:
            button.disabled = False
            page.update()

    def close_details(dialog):
        page.pop_dialog()
        page.update()

    def build_online_view():
        query_box = ft.TextField(
            label="联网搜索漫画",
            hint_text="输入中文、英文或日文标题，例如：一拳超人",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_submit=lambda e: page.run_task(run_online_search, query_box.value or "", results, message, search_button),
        )
        results = ft.ListView(expand=True, spacing=8, auto_scroll=False)
        message = ft.Text(
            "支持中文、英文和日文搜索。资料来源为 AniList，阅读来源会单独列出。",
            color=ft.Colors.GREY_400,
        )
        search_button = ft.Button(
            "搜索",
            icon=ft.Icons.SEARCH,
            on_click=lambda e: page.run_task(run_online_search, query_box.value or "", results, message, search_button),
        )
        page.clean()
        page.add(
            ft.AppBar(
                title=ft.Text("Manga.app · 在线发现"),
                leading=ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda e: build_library_view()),
            ),
            ft.Text("联网搜索", size=20, weight=ft.FontWeight.BOLD),
            ft.Row([query_box, search_button]),
            message,
            ft.Divider(),
            results,
            ft.Text(
                "优先显示可识别的中文标题；部分作品暂无中文简介。阅读来源会标明语言，并提示免费章节需进一步确认。",
                size=12,
                color=ft.Colors.GREY_500,
            ),
        )
        page.update()

    def build_library_view():
        page.padding = 12
        page.clean()
        page.add(
            ft.AppBar(
                title=ft.Text("Manga.app · 个人漫画库"),
                actions=[
                    ft.IconButton(
                        icon=ft.Icons.PUBLIC,
                        tooltip="联网搜索漫画",
                        on_click=lambda _: build_online_view(),
                    ),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        tooltip="刷新资料库",
                        on_click=lambda _: refresh_library(),
                    )
                ],
            ),
            ft.Row(
                [
                    ft.Button(
                        content="导入漫画",
                        icon=ft.Icons.FOLDER_OPEN,
                        on_click=import_files,
                    ),
                    ft.Text("支持 CBZ / ZIP / JPG / PNG / WEBP / GIF", size=12, color=ft.Colors.GREY_400),
                ],
                wrap=True,
            ),
            import_category,
            ft.Row([search_box, favorites_only], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            status,
            ft.Divider(),
            manga_list,
        )
        refresh_library()

    build_library_view()


if __name__ == "__main__":
    ft.run(main)
