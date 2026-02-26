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
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; Magic 6 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
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
                    imgs = []
                    for img in content.find_all('img'):
                        src = img.get('data-src') or img.get('src')
                        if src and 'http' in src: imgs.append(src)
                    return imgs
        except: return []

# ================= 2. 核心主逻辑 (MagicOS 适配：暴力重绘模式) =================
async def main(page: ft.Page):
    # 【方案 B】MagicOS 强制重绘：设置非常明显的背景颜色，并在启动时多次刷新
    page.bgcolor = ft.colors.BLACK
    page.padding = 20
    page.window_always_on_top = True # 尝试提升渲染优先级

    # 1. 初始渲染占位
    loading_container = ft.Column([
        ft.Text("次元幻境", size=32, weight="bold", color="cyan"),
        ft.Text("正在针对 MagicOS 进行引擎校准...", size=14, color="grey"),
        ft.ProgressBar(width=250, color="cyan"),
    ], alignment="center", horizontal_alignment="center")
    
    page.add(ft.Container(expand=True, content=loading_container, alignment=ft.alignment.center))
    
    # 【专家戊的绝招】：连续 3 次心跳更新，强迫高刷屏刷新帧缓冲
    for i in range(3):
        page.update()
        await asyncio.sleep(0.5)

    # 2. 功能组件初始化
    spider = ManwaSpider()
    image_list = ft.ListView(expand=True, spacing=15)
    url_input = ft.TextField(
        label="输入章节地址 (Manwa.me)",
        value="https://manwa.me/chapter/31290275",
        expand=True,
        border_color="cyan"
    )

    async def on_load(e):
        page.snack_bar = ft.SnackBar(ft.Text("净化网页并抓取中..."))
        page.snack_bar.open = True
        page.update()
        
        imgs = await spider.fetch_images(url_input.value)
        image_list.controls.clear()
        
        if not imgs:
            page.snack_bar = ft.SnackBar(ft.Text("抓取失败，请检查链接或权限"))
        else:
            for url in imgs:
                image_list.controls.append(ft.Image(src=url, fit=ft.ImageFit.WIDTH))
        page.update()

    # 3. 渲染主界面
    page.controls.clear()
    page.add(
        ft.Row([url_input, ft.IconButton(ft.icons.AUTO_AWESOME, on_click=on_load, icon_color="cyan")]),
        image_list
    )
    page.update()

if __name__ == "__main__":
    # 使用特殊的渲染配置启动
    ft.app(target=main)
