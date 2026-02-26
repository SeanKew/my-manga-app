import flet as ft
import aiohttp
import asyncio
import re
from bs4 import BeautifulSoup
import os
import sqlite3

# ================= 1. 漫画精准抓取器 (Manwa 专项) =================
class ManwaSpider:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.36",
            "Referer": "https://manwa.me/"
        }

    async def fetch_chapter_images(self, url):
        """精准抓取章节图片，无视广告"""
        try:
            async with aiohttp.ClientSession(headers=self.headers) as session:
                async with session.get(url, timeout=10) as response:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 【核心】定位漫画内容容器，跳过所有广告 div
                    # 通常 Manwa 的图片在 id 或 class 包含 'content' 的区域
                    content_div = soup.find('div', class_=re.compile(r'chapter-content|read-content'))
                    
                    images = []
                    if content_div:
                        img_tags = content_div.find_all('img')
                        for img in img_tags:
                            src = img.get('data-src') or img.get('src')
                            if src and 'http' in src:
                                # 排除已知的广告域名或小图标
                                if "ads" not in src and "icon" not in src:
                                    images.append(src)
                    
                    return images if images else ["ERROR: 未找到图片"]
        except Exception as e:
            return [f"连接错误: {str(e)}"]

# ================= 2. 界面逻辑升级 =================
async def main(page: ft.Page):
    page.title = "次元幻境 - 净网版"
    page.theme_mode = ft.ThemeMode.DARK
    
    spider = ManwaSpider()
    
    # 顶部 UI
    url_input = ft.TextField(
        label="输入漫画章节链接", 
        value="https://manwa.me/chapter/31290275",
        expand=True
    )
    
    image_list = ft.ListView(expand=True, spacing=10)
    progress = ft.ProgressBar(visible=False)

    async def start_reading(e):
        if not url_input.value: return
        
        progress.visible = True
        image_list.controls.clear()
        page.add(ft.SnackBar(ft.Text("正在净化网页并提取漫画..."), open=True))
        page.update()

        # 开始抓取
        img_urls = await spider.fetch_chapter_images(url_input.value)
        
        progress.visible = False
        if "ERROR" in img_urls[0]:
            image_list.controls.append(ft.Text(img_urls[0], color="red"))
        else:
            for url in img_urls:
                # 丙的建议：增加图片加载占位符，防止白屏
                image_list.controls.append(
                    ft.Image(
                        src=url,
                        fit=ft.ImageFit.WIDTH,
                        repeat=ft.ImageRepeat.NO_REPEAT,
                        border_radius=5,
                        error_content=ft.Text("图片加载失败(可能已被防盗链)")
                    )
                )
        page.update()

    page.add(
        ft.Row([url_input, ft.IconButton(ft.icons.PLAY_CIRCLE_FILL, on_click=start_reading)]),
        progress,
        image_list
    )

if __name__ == "__main__":
    ft.app(target=main)
