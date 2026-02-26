import flet as ft
import asyncio

async def main(page: ft.Page):
    # 1. 极简初始化：完全放弃复杂的 AppBar，防止渲染层级过多导致崩溃
    page.bgcolor = ft.colors.BLACK
    page.window_full_screen = True  # 强行占领全屏
    
    # 2. 暴力渲染：先放一个巨大的亮色方块，强迫 GPU 响应
    test_rect = ft.Container(
        content=ft.Text("INITIALIZING...", color="black", size=40, weight="bold"),
        bgcolor="white",
        width=200,
        height=200,
        alignment=ft.alignment.center,
    )
    
    main_container = ft.Container(
        expand=True,
        content=ft.Column([
            ft.Text("次元幻境 - MagicOS 强载模式", size=24, color="white"),
            test_rect,
            ft.Text("如果能看到白色方块，请等待 3 秒...", color="grey"),
            ft.ProgressBar(width=300, color="blue")
        ], alignment="center", horizontal_alignment="center")
    )
    
    page.add(main_container)
    
    # 3. 核心修正：连续 5 次强制刷新 (Heartbeat)
    for i in range(5):
        page.update()
        await asyncio.sleep(0.5)

    # 4. 只有亮屏后才加载真实逻辑
    test_rect.bgcolor = "cyan"
    test_rect.content = ft.Text("READY!", color="black", size=40)
    page.update()
    
    # --- 真实的搜索入口 ---
    url_input = ft.TextField(label="粘贴漫画链接", border_color="blue", width=300)
    
    async def go_read(e):
        page.clean()
        page.add(ft.Text("正在净化并加载，请稍后...", size=20))
        page.update()
        # 这里可以放之前的抓取逻辑
        
    page.add(url_input, ft.ElevatedButton("开始净化阅读", on_click=go_read))
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
