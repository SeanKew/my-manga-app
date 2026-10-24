"""Manga.app: local manga library and reader MVP."""
from __future__ import annotations

import base64
from pathlib import Path

import flet as ft

from data.repository import MangaRepository
from services.local_import_service import import_local_file
from ui.reader_page import load_page_base64


def main(page: ft.Page):
    page.title = "Manga.app"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 12
    page.spacing = 10

    repository = MangaRepository()
    picker = ft.FilePicker()
    page.services.append(picker)

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
            progress_text = "尚未阅读"
            if progress:
                progress_text = f"上次阅读第 {progress['page_index'] + 1} 页"
            manga_list.controls.append(
                ft.Card(
                    content=ft.Container(
                        padding=10,
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.MENU_BOOK,
                                    size=34,
                                    color=ft.Colors.CYAN_300,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(item["title"], weight=ft.FontWeight.BOLD, max_lines=2),
                                        ft.Text(
                                            f"{page_count} 页 · {progress_text}",
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

    def build_library_view():
        page.clean()
        page.add(
            ft.AppBar(
                title=ft.Text("Manga.app · 个人漫画库"),
                actions=[
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
