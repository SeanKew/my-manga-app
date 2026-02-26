import flet as ft
import random
import asyncio
import os
import platform

# ================= 1. 数据库管理 =================
class ShelfDB:
    def __init__(self):
        # 手机端路径适配
        db_dir = os.environ.get("FLET_APP_DATA", ".")
        db_path = os.path.join(db_dir, "manga_shelf.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False) if "sqlite3" in globals() else None
        # 为简化，手机端如果sqlite3没加载则跳过
        try:
            import sqlite3
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.cursor().execute('CREATE TABLE IF NOT EXISTS shelf (id INTEGER PRIMARY KEY, title TEXT, img TEXT, url TEXT UNIQUE)')
            self.conn.commit()
        except: pass

# ================= 2. 爬虫引擎 =================
class MangaEngine:
    async def search_real(self, keyword):
        await asyncio.sleep(1) 
        return [{"title": f"{keyword} 卷{i}", "img": f"https://picsum.photos/seed/{i}/200/300", "url": "#"} for i in range(4)]

# ================= 3. 修复后的加载游戏 (不再使用 UserControl) =================
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
            ft.Text("正在穿越次元壁...", size=16, italic=True),
            self.game_canvas,
            ft.ProgressBar(width=350, color="cyan"),
            ft.Text("点击方块捕捉灵感！", size=12, color="grey")
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    async def spawn_target(self, page):
        while self.game_running:
            x, y = random.randint(20, 300), random.randint(50, 250)
            target = ft.Container(
                width=35, height=35, bgcolor=random.choice(["red", "green", "blue", "yellow"]),
                border_radius=8, left=x, top=y,
                on_click=lambda e: self.handle_tap(e, page)
            )
            self.game_canvas.controls.append(target)
            page.update()
            await asyncio.sleep(0.8)
            if target in self.game_canvas.controls:
                self.game_canvas.controls.remove(target)
                page.update()

    def handle_tap(self, e, page):
        self.score += 1
        self.score_display.value = f"捕捉灵感: {self.score}"
        e.control.visible = False
        page.update()

# ================= 4. 主入口 =================
async def main(page: ft.Page):
    page.title = "次元幻境"
    page.theme_mode = ft.ThemeMode.DARK
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # 启动游戏
    game = LoadingGame()
    page.add(game.get_ui())
    game_task = asyncio.create_task(game.spawn_target(page))

    # 模拟初始化
    await asyncio.sleep(6) 
    
    # 停止游戏
    game.game_running = False
    game_task.cancel()
    
    # 进入主界面
    page.controls.clear()
    page.add(ft.Text(f"捕捉完成！得分: {game.score}", size=20, color="green"))
    await asyncio.sleep(1)
    
    # 这里仅演示进入主页
    page.controls.clear()
    page.add(ft.AppBar(title=ft.Text("次元幻境 - 主页"), bgcolor=ft.colors.SURFACE_VARIANT))
    page.add(ft.Text("欢迎回来，漫画已准备就绪！", size=16))
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
