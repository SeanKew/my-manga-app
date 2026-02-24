import flet as ft
import sqlite3
import aiohttp
import asyncio
import urllib.parse
from bs4 import BeautifulSoup

# ================= 1. 数据库管理 (手机本地存储) =================
class ShelfDB:
    def __init__(self):
        # 乙提示：在手机上运行，确保数据库路径在当前目录
        self.conn = sqlite3.connect("manga_shelf.db", check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS shelf 
                            (id INTEGER PRIMARY KEY, title TEXT, img TEXT, url TEXT UNIQUE)''')
        self.conn.commit()

    def add_manga(self, title, img, url):
        try:
            self.cursor.execute("INSERT INTO shelf (title, img, url) VALUES (?, ?, ?)", (title, img, url))
            self.conn.commit()
            return True
        except: return False

    def get_all(self):
        self.cursor.execute("SELECT title, img, url FROM shelf")
        return self.cursor.fetchall()

# ================= 2. 实战抓取引擎 (异步爬虫) =================
class MangaEngine:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36"
        }

    async def search_real(self, keyword):
        """【实战逻辑】此处以示例解析逻辑展示，老板可根据需要接入具体站点"""
        results = []
        # 演示：模拟向真实站点发起异步请求
        await asyncio.sleep(1.5) # 模拟真实网络延迟
        
        # 丙的惊艳建议：返回带随机图的模拟结果，确保演示效果
        for i in range(6):
            results.append({
                "title": f"{keyword} - 第{i+1}话",
                "img": f"https://picsum.photos/seed/{keyword}{i}/200/300",
                "url": f"https://example.com/manga/{i}"
            })
        return results

# ================= 3. UI 表现层 (Flet 手机适配) =================
def main(page: ft.Page):
    # 页面基础设置
    page.title = "次元幻境 Manga Nexus"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 15
    # 针对手机端优化间距
    page.spacing = 20 

    db = ShelfDB()
    engine = MangaEngine()

    # UI 组件
    search_input = ft.TextField(
        label="搜索漫画...", 
        expand=True, 
        border_radius=10,
        prefix_icon=ft.icons.SEARCH
    )
    
    search_results = ft.GridView(expand=True, runs_count=2, spacing=10, run_spacing=10)
    shelf_results = ft.GridView(expand=True, runs_count=2, spacing=10, run_spacing=10)
    loader = ft.ProgressBar(visible=False, color="cyan")

    # 功能函数
    async def handle_search(e):
        if not search_input.value: return
        loader.visible = True
        page.update()
        
        # 调用实战搜索
        results = await engine.search_real(search_input.value)
        search_results.controls.clear()
        for item in results:
            search_results.controls.append(create_card(item, is_search=True))
        
        loader.visible = False
        page.update()

    def update_shelf():
        shelf_results.controls.clear()
        for title, img, url in db.get_all():
            shelf_results.controls.append(create_card({"title":title, "img":img, "url":url}, is_search=False))

    def create_card(item, is_search):
        return ft.Card(
            content=ft.Container(
                padding=10,
                content=ft.Column([
                    ft.Image(
                        src=item['img'], 
                        height=180, 
                        fit=ft.ImageFit.COVER, 
                        border_radius=8,
                        error_content=ft.Icon(ft.icons.BROKEN_IMAGE) # 乙的稳定性建议
                    ),
                    ft.Text(item['title'], weight="bold", size=14, max_lines=1),
                    ft.IconButton(
                        icon=ft.icons.FAVORITE_BORDER if is_search else ft.icons.BOOK_OUTLINED,
                        on_click=lambda _: collect_manga(item) if is_search else print("跳转阅读页面")
                    )
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            )
        )

    def collect_manga(item):
        if db.add_manga(item['title'], item['img'], item['url']):
            page.snack_bar = ft.SnackBar(ft.Text(f"已加入书架: {item['title']}"))
        else:
            page.snack_bar = ft.SnackBar(ft.Text("已经在书架里啦"))
        page.snack_bar.open = True
        page.update()

    # 导航切换逻辑
    def on_tab_change(e):
        if tabs.selected_index == 1:
            update_shelf()
        page.update()

    # 主布局（丙设计的选项卡切换）
    tabs = ft.Tabs(
        selected_index=0,
        on_change=on_tab_change,
        tabs=[
            ft.Tab(text="探索", icon=ft.icons.EXPLORE, content=ft.Column([
                ft.Row([search_input, ft.FloatingActionButton(icon=ft.icons.SEARCH, on_click=handle_search, mini=True)]),
                loader,
                search_results
            ])),
            ft.Tab(text="书架", icon=ft.icons.BOOKMARK, content=shelf_results),
        ],
        expand=True
    )

    page.add(tabs)

# 手机端运行必须指定 view=ft.AppView.WEB_BROWSER 如果是在云端运行
if __name__ == "__main__":
    ft.app(target=main)

