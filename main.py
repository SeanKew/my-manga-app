import flet as ft
import aiohttp
import asyncio

# ---------------------------- 数据模型 ----------------------------
class Manga:
    def __init__(self, id: str, title: str, cover_url: str = "", description: str = ""):
        self.id = id
        self.title = title
        self.cover_url = cover_url
        self.description = description

class Chapter:
    def __init__(self, id: str, title: str, chapter_number: str):
        self.id = id
        self.title = title
        self.chapter_number = chapter_number

# ---------------------------- MangaDex API 源 ----------------------------
class MangaDexSource:
    API_BASE = "https://api.mangadex.org"
    COVER_BASE = "https://uploads.mangadex.org/covers"

    @staticmethod
    async def search(keyword: str, session: aiohttp.ClientSession):
        params = {"title": keyword, "limit": 15, "includes[]": ["cover_art"]}
        try:
            async with session.get(f"{MangaDexSource.API_BASE}/manga", params=params) as resp:
                if resp.status != 200: return []
                data = await resp.json()
                results = []
                for item in data.get("data", []):
                    title = item["attributes"]["title"].get("en") or next(iter(item["attributes"]["title"].values()), "Untitled")
                    cover_id = next((r["id"] for r in item["relationships"] if r["type"] == "cover_art"), None)
                    cover_url = f"{MangaDexSource.COVER_BASE}/{item['id']}/{cover_id}.jpg" if cover_id else ""
                    results.append(Manga(item["id"], title, cover_url, item["attributes"]["description"].get("en", "")))
                return results
        except: return []

    @staticmethod
    async def get_chapters(manga_id: str, session: aiohttp.ClientSession):
        params = {"manga": manga_id, "translatedLanguage[]": ["en", "zh"], "order[chapter]": "asc", "limit": 100}
        try:
            async with session.get(f"{MangaDexSource.API_BASE}/manga/{manga_id}/feed", params=params) as resp:
                if resp.status != 200: return []
                data = await resp.json()
                return [Chapter(i["id"], i["attributes"].get("title", ""), i["attributes"]["chapter"]) 
                        for i in data.get("data", []) if i["attributes"].get("chapter")]
        except: return []

    @staticmethod
    async def get_images(chapter_id: str, session: aiohttp.ClientSession):
        try:
            async with session.get(f"{MangaDexSource.API_BASE}/at-home/server/{chapter_id}") as resp:
                data = await resp.json()
                host, hash = data["baseUrl"], data["chapter"]["hash"]
                return [f"{host}/data/{hash}/{p}" for p in data["chapter"]["data"]]
        except: return []

# ---------------------------- 核心 UI ----------------------------
class MangaNexusApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.session = None
        self.source = MangaDexSource()
        
        # 搜索页状态保持
        self.search_results = []
        self.last_keyword = ""

    async def init_session(self):
        self.session = aiohttp.ClientSession(connector=aiohttp.TCPConnector(limit=5))

    def show_loading(self):
        self.page.overlay.append(ft.ProgressBar(width=self.page.width, color="blue"))
        self.page.update()

    def hide_loading(self):
        self.page.overlay.clear()
        self.page.update()

    async def show_search_page(self, e=None):
        self.page.clean()
        search_input = ft.TextField(value=self.last_keyword, label="搜索漫画...", expand=True, on_submit=self.do_search)
        
        results_view = ft.ListView(expand=True, spacing=10)
        for m in self.search_results:
            results_view.controls.append(self.build_manga_card(m))

        async def on_search_click(e): await self.do_search(search_input.value)

        self.page.add(
            ft.AppBar(title=ft.Text("MangaNexus"), bgcolor=ft.colors.SURFACE_VARIANT),
            ft.Row([search_input, ft.IconButton(ft.icons.SEARCH, on_click=on_search_click)]),
            results_view
        )

    async def do_search(self, keyword):
        if not keyword: return
        self.last_keyword = keyword
        self.show_loading()
        self.search_results = await self.source.search(keyword, self.session)
        self.hide_loading()
        await self.show_search_page()

    def build_manga_card(self, manga):
        return ft.Card(
            content=ft.ListTile(
                leading=ft.Image(src=manga.cover_url, width=50, fit=ft.ImageFit.COVER),
                title=ft.Text(manga.title, max_lines=1),
                subtitle=ft.Text(manga.description, max_lines=2),
                on_click=lambda _: self.page.run_task(self.show_chapters, manga)
            )
        )

    async def show_chapters(self, manga):
        self.show_loading()
        chapters = await self.source.get_chapters(manga.id, self.session)
        self.hide_loading()
        
        self.page.clean()
        chapter_list = ft.ListView(expand=True)
        for ch in chapters:
            chapter_list.controls.append(
                ft.ListTile(title=ft.Text(f"第 {ch.chapter_number} 话 {ch.title}"), 
                            on_click=lambda _, c=ch: self.page.run_task(self.show_reader, c, manga))
            )
            
        self.page.add(
            ft.AppBar(title=ft.Text(manga.title), leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=self.show_search_page)),
            chapter_list
        )

    async def show_reader(self, chapter, manga):
        self.show_loading()
        images = await self.source.get_images(chapter.id, self.session)
        self.hide_loading()

        img_controls = []
        for url in images:
            img_controls.append(ft.Image(src=url, width=self.page.width, fit=ft.ImageFit.FIT_WIDTH))

        reader_view = ft.ListView(expand=True, controls=img_controls)

        def on_resize(e):
            for img in img_controls:
                img.width = self.page.width
            self.page.update()

        self.page.on_resize = on_resize
        self.page.clean()
        self.page.add(
            ft.AppBar(title=ft.Text(f"第 {chapter.chapter_number} 话"), 
                      leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: self.page.run_task(self.show_chapters, manga))),
            reader_view
        )

async def main(page: ft.Page):
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10
    app = MangaNexusApp(page)
    await app.init_session()
    await app.show_search_page()

if __name__ == "__main__":
    ft.app(target=main)
