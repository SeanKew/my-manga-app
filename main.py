import flet as ft
import asyncio
import httpx  # 建议替换 aiohttp，httpx 在移动端更稳

async def main(page: ft.Page):
    page.title = "次元幻境"
    page.bgcolor = ft.colors.BLACK
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 20
    
    # 状态变量
    manga_source = "https://manwa.me" # 示例源

    # --- 核心 UI 逻辑 ---
    async def go_read(e):
        target_url = url_input.value
        if not target_url:
            page.snack_bar = ft.SnackBar(ft.Text("请输入链接！"))
            page.snack_bar.open = True
            page.update()
            return

        loading_screen.visible = True
        search_screen.visible = False
        page.update()
        
        # 模拟净化加载过程 (甲建议：此处后期接入 BeautifulSoup)
        await asyncio.sleep(2) 
        
        loading_screen.visible = False
        content_screen.visible = True
        content_screen.controls.append(ft.Text(f"已净化资源：{target_url}", color="green"))
        page.update()

    # --- 界面层级 ---
    loading_screen = ft.Column([
        ft.ProgressRing(),
        ft.Text("正在穿透广告层，请稍后...", color="white")
    ], visible=False, horizontal_alignment="center")

    search_screen = ft.Column([
        ft.Text("次元幻境 - MagicOS 适配版", size=24, weight="bold"),
        ft.Container(height=20),
        url_input := ft.TextField(
            label="粘贴漫画链接 (如 Manwa)", 
            border_color="blue", 
            focused_border_color="cyan",
            prefix_icon=ft.icons.LINK
        ),
        ft.ElevatedButton(
            "开始净化阅读", 
            icon=ft.icons.CLEAN_HANDS,
            on_click=go_read,
            style=ft.ButtonStyle(color="white", bgcolor="blue")
        )
    ], horizontal_alignment="center")

    content_screen = ft.Column(scroll=ft.ScrollMode.ALWAYS, expand=True, visible=False)

    # 首次加载的心跳修正 (丙建议)
    page.add(search_screen, loading_screen, content_screen)
    
    for i in range(3):
        page.update()
        await asyncio.sleep(0.3)

if __name__ == "__main__":
    # 关键：在移动端有时需要指定渲染模式
    ft.app(target=main)
