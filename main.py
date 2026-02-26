import flet as ft
import asyncio
import os
import platform
import random
import re
from bs4 import BeautifulSoup
import aiohttp

# ================= 1. 适配 MagicOS 的路径管理 =================
class MangaStore:
    def __init__(self):
        # 优先使用应用私有目录，避免权限拦截
        db_dir = os.environ.get("FLET_APP_DATA", ".")
        self.db_path = os.path.join(db_dir, "manga_magic.db")
        self.init_db()

    def init_db(self):
        try:
            import sqlite3
            conn = sqlite3.connect(self.db_path)
            conn.execute('CREATE TABLE IF NOT EXISTS manga (id INTEGER PRIMARY KEY, title TEXT, url TEXT)')
            conn.commit()
            conn.close()
        except: pass

# ================= 2. 净网爬虫模块 =================
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
                    return [img.get('data-src') or img.get('src') for img in content.find_all('img') if img.get('src')]
        except: return []

# ================= 3. UI 主逻辑 (强制渲染架构) =================
async def main(page: ft.Page):
    # 【核心适配】立即设置背景颜色和初始文字，强制 MagicOS 渲染 UI 帧
    page.bgcolor = ft.colors.BLACK
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    
    status_text = ft.Text("次元幻境：内核启动中...", color="cyan", size=16)
    loading_icon = ft.ProgressBar(width=200, color="cyan")
    page.add(status_text, loading_icon)
    page.update()

    # 模拟系统初始化延迟
    await asyncio.sleep(1.5)
    
    # 初始化组件
    spider = ManwaSpider()
    image_list = ft.ListView(expand=True, spacing=10)
    url_input = ft.TextField(
        label="输入 Manwa 章节链接", 
        value="https://manwa.me/chapter/31290275",
        expand=True,
        border_color="cyan"
    )

    async def on_load_click(e):
        status_text.visible = True
        status_text.value = "正在净化网页并提取内容..."
        page.update()
        
        imgs = await spider.fetch_images(url_input.value)
        image_list.controls.clear()
        
        if not imgs:
            page.snack_bar = ft.SnackBar(ft.Text("抓取失败，请检查网络权限"))
            page.snack_bar.open = True
        else:
            for img_url in imgs:
                image_list.controls.append(ft.Image(src=img_url, fit=ft.ImageFit.WIDTH))
        
        status_text.visible = False
        page.update()

    # 4. 替换为正式主界面
    page.controls.clear()
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.add(
        ft.Container(height=20), # 状态栏间距
        ft.Row([url_input, ft.IconButton(ft.icons.PLAY_ARROW_ROUNDED, on_click=on_load_click, icon_color="cyan")]),
        status_text,
        image_list
    )
    status_text.visible = False
    page.update()

if __name__ == "__main__":
    ft.app(target=main)
