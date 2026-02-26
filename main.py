import flet as ft
import sqlite3
import asyncio
import os
import platform

# ================= 1. 强化版数据库 (支持缓存标记) =================
class MangaStore:
    def __init__(self):
        db_dir = os.environ.get("FLET_APP_DATA", ".")
        self.db_path = os.path.join(db_dir, "manga_v2.db")
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        # 增加 local_path 字段，存储本地图片路径
        conn.execute('''CREATE TABLE IF NOT EXISTS manga 
                     (id INTEGER PRIMARY KEY, title TEXT, img_url TEXT, local_path TEXT, is_cached INTEGER)''')
        conn.commit()
        conn.close()

    def save_manga(self, title, img_url):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("INSERT INTO manga (title, img_url, is_cached) VALUES (?, ?, 0)", (title, img_url))
            conn.commit()
        except: pass
        finally: conn.close()

    def get_all(self):
        conn = sqlite3.connect(self.db_path)
        res = conn.execute("SELECT title, img_url, local_path, is_cached FROM manga").fetchall()
        conn.close()
        return res

# ================= 2. 加载小游戏 (保持不变，略作优化) =================
class LoadingGame:
    def __init__(self):
        self.score = 0
        self.game_running = True
        self.score_display = ft.Text(f"捕捉灵感: {self.score}", size=20, weight="bold", color="cyan")
        self.game_canvas = ft.Stack([
            ft.Container(expand=True, bgcolor=ft.colors.BLACK12, border_radius=15),
            self.score_display
        ], width=350, height=300)

    def get_ui(self):
        return ft.Column([
            ft.Text("正在加载本地仓库...", size=16, italic=True),
            self.game_canvas,
            ft.ProgressBar(width=300, color="cyan"),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    async def spawn_target(self, page):
        while self.game_running:
            target = ft.Container(
                width=40, height=40, bgcolor="orange", border_radius=20,
                left=random.randint(10, 300), top=random.randint(10, 250),
                on_click=lambda _: self.on_tap(page)
            )
            self.game_canvas.controls.append(target)
            page.update()
            await asyncio.sleep(0.7)
            if target in self.game_canvas.controls: self.game_canvas.controls.remove(target)
            page.update()

    def on_tap(self, page):
        self.score += 1
        self.score_display.value = f"捕捉灵感: {self.score}"
        page.update()

import random # 补上缺失的导入

# ================= 3. 主界面逻辑 (离线优先) =================
async def main(page: ft.Page):
    page.title = "次元幻境 - 离线版"
    page.theme_mode = ft.ThemeMode.DARK
    
    store = MangaStore()
    game = LoadingGame()
    
    # --- 启动小游戏 ---
    page.add(game.get_ui())
    game_task = asyncio.create_task(game.spawn_target(page))
    await asyncio.sleep(4) # 加载数据中...
    game.game_running = False
    game_task.cancel()

    # --- 进入主界面 ---
    page.controls.clear()
    
    # 顶部导航栏
    page.appbar = ft.AppBar(title=ft.Text("我的次元仓库"), bgcolor=ft.colors.SURFACE_VARIANT)
    
    grid = ft.GridView(expand=True, runs_count=2, spacing=10)

    def refresh_ui():
        grid.controls.clear()
        data = store.get_all()
        if not data:
            grid.controls.append(ft.Text("仓库空空如也，快去搜索漫画吧！", text_align="center"))
        for title, img, local, cached in data:
            # 离线逻辑：如果有本地路径就用本地的，否则用网络图
            display_img = local if cached == 1 else img
            grid.controls.append(
                ft.Card(ft.Container(padding=10, content=ft.Column([
                    ft.Image(src=display_img, height=150, border_radius=5),
                    ft.Text(title, size=12, weight="bold"),
                    ft.Badge(content=ft.Text("已缓存" if cached else "云端"))
                ])))
            )
        page.update()

    # 搜索功能 (模拟联网并缓存)
    async def on_search(e):
        page.snack_bar = ft.SnackBar(ft.Text("正在联网抓取并缓存..."))
        page.snack_bar.open = True
        page.update()
        
        # 模拟联网抓取
        await asyncio.sleep(2)
        new_title = f"{search_box.value} 连载中"
        new_img = f"https://picsum.photos/seed/{random.random()}/200/300"
        
        store.save_manga(new_title, new_img)
        refresh_ui()

    search_box = ft.TextField(label="搜索并自动缓存", expand=True)
    page.add(
        ft.Row([search_box, ft.IconButton(ft.icons.CLOUD_DOWNLOAD, on_click=on_search)]),
        grid
    )
    
    refresh_ui()
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
