import flet as ft
import random
import asyncio
import os
import platform

# ================= 数据库与引擎 (保持不变) =================
# ... [此处省略之前的 ShelfDB 和 MangaEngine 类，逻辑同上] ...

# ================= 加载小游戏组件 (丙的设计) =================
class LoadingGame(ft.UserControl):
    def __init__(self, on_finish_text="加载完成！"):
        super().__init__()
        self.score = 0
        self.on_finish_text = on_finish_text
        self.game_running = True

    def build(self):
        self.score_display = ft.Text(f"捕捉灵感: {self.score}", size=20, weight="bold", color="cyan")
        self.game_canvas = ft.Stack(
            controls=[
                ft.Container(expand=True, bgcolor=ft.colors.BLACK12, border_radius=15),
                self.score_display
            ],
            width=350,
            height=300,
        )
        
        return ft.Column([
            ft.Text("正在穿越次元壁...", size=16, italic=True),
            self.game_canvas,
            ft.ProgressBar(width=350, color="cyan"),
            ft.Text("点击随机出现的方块以捕捉灵感！", size=12, color="grey")
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    async def spawn_target(self):
        """随机生成可点击的方块"""
        while self.game_running:
            # 随机位置和颜色
            x = random.randint(20, 300)
            y = random.randint(50, 250)
            colors = ["red", "green", "blue", "yellow", "orange", "purple"]
            
            target = ft.Container(
                width=30, height=30,
                bgcolor=random.choice(colors),
                border_radius=5,
                left=x, top=y,
                animate_opacity=300,
                on_click=self.handle_tap
            )
            
            self.game_canvas.controls.append(target)
            self.update()
            
            # 1秒后消失
            await asyncio.sleep(0.8)
            if target in self.game_canvas.controls:
                self.game_canvas.controls.remove(target)
                self.update()

    def handle_tap(self, e):
        self.score += 1
        self.score_display.value = f"捕捉灵感: {self.score}"
        e.control.visible = False # 点击后消失
        self.update()

    def stop_game(self):
        self.game_running = False

# ================= 3. UI 主入口 (增加游戏切换) =================
async def main(page: ft.Page):
    page.title = "次元幻境"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_width, page.window_height = 400, 800
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    # --- 步骤 1: 显示小游戏 ---
    game = LoadingGame()
    page.add(game)
    # 启动后台生成目标
    game_task = asyncio.create_task(game.spawn_target())

    # --- 步骤 2: 模拟后台加载 (在此处放置真实的初始化逻辑) ---
    # 比如数据库连接、检查网络权限等
    await asyncio.sleep(5) # 强行让老板玩 5 秒游戏
    
    # --- 步骤 3: 加载完成，切换界面 ---
    game.stop_game()
    game_task.cancel() # 停止游戏循环
    
    page.controls.clear()
    page.add(ft.Icon(ft.icons.CHECK_CIRCLE, color="green", size=50))
    page.add(ft.Text(f"加载完毕！最终得分: {game.score}", size=18))
    await asyncio.sleep(1) # 短暂展示得分
    
    # 进入真正的 App 界面 (此处调用之前的 Tabs 逻辑)
    setup_main_app(page)

def setup_main_app(page: ft.Page):
    # 这里放置之前给您的 Tabs、Search、Shelf 等所有 UI 逻辑
    page.controls.clear()
    page.add(ft.Text("进入主界面 - 开启你的漫画之旅"))
    # ... (此处省略重复的界面代码) ...
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
