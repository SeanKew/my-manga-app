import flet as ft
import asyncio
import os
import re
from bs4 import BeautifulSoup
import aiohttp

# ================= 1. 净网爬虫模块 =================
class ManwaSpider:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
            "Referer": "https://manwa.me/"
        }

    async def fetch_images(self, url):
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=10) as resp:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    content = soup.find('div', class_=re.compile(r'chapter-content|read-content'))
                    if not content: return []
                    return [img.get('data-src') or img.get('src') for img in content.find_all('img') if (img.get('data-src') or img.get('src'))]
        except: return []

# ================= 2. UI 主逻辑 (MagicOS 适配版) =================
async def main(page: ft.Page):
    # 强制开启硬件渲染优化
    page.title = "次元幻境"
    page.bgcolor = ft.colors.BLACK
    page.theme_mode = ft.ThemeMode.DARK
    
    # 立即渲染首屏，证明应用存活
    init_screen = ft.Container(
        expand=True,
        content=ft.Column([
            ft.Text("Honor MagicOS 适配版启动中", color="cyan", size=20, weight="bold"),
            ft.ProgressBar(width=250, color="cyan"),
            ft.Text("正在初始化渲染管线...", color="grey", size=12)
        ], alignment="center", horizontal_alignment="center")
    )
    page.add(init_screen)
    page.update()

    # 延迟加载核心逻辑
    await asyncio.sleep(2)
    spider = ManwaSpider()
    image_list = ft.ListView(expand=True, spacing=10)
    
    url_input = ft.TextField(
        label="漫画章节链接", 
        value="https://manwa.me/chapter/31290275",
        expand=True,
        border_color="cyan",
        text_size=14
    )

    async def on_load_click(e):
        page.snack_bar = ft.SnackBar(ft.Text("正在净化网页并抓取图片..."), open=True)
        page.update()
        
        imgs = await spider.fetch_images(url_input.value)
        image_list.controls.clear()
        
        if not imgs:
            page.snack_bar = ft.SnackBar(ft.Text("抓取失败，请检查网络权限或链接"))
            page.snack_bar.open = True
        else:
            for img_url in imgs:
                # 增加图片自适应显示
                image_list.controls.append(
                    ft.Image(src=img_url, fit=ft.ImageFit.WIDTH, border_radius=5)
                )
        page.update()

    # 切换到主界面
    page.controls.clear()
    page.add(
        ft.AppBar(title=ft.Text("次元幻境"), bgcolor=ft.colors.SURFACE_VARIANT, center_title=True),
        ft.Row([url_input, ft.IconButton(ft.icons.BOLT, on_click=on_load_click, icon_color="cyan")], padding=10),
        image_list
    )
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
