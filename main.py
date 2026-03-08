import base64
import hashlib
import threading
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlparse

import cloudscraper
import flet as ft
from bs4 import BeautifulSoup

# ==============================
# 全局错误捕获 (解决黑屏无提示问题)
# ==============================
def create_exception_handler(page: ft.Page):
    def handle_exception(exc_type, exc_value, exc_traceback):
        err_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        # 弹窗报警，确保在手机端能看到报错
        page.dialog = ft.AlertDialog(
            title=ft.Text("Fatal Error", color="red"),
            content=ft.Column([ft.Text(err_msg, size=10)], scroll=ft.ScrollMode.ALWAYS),
            actions=[ft.TextButton("Copy", on_click=lambda _: page.set_clipboard(err_msg))]
        )
        page.dialog.open = True
        page.update()
    return handle_exception

# ==============================
# 核心逻辑
# ==============================
class Engine:
    def __init__(self):
        # 增加超时限制，防止安卓主线程被 scraper 锁死
        self.scraper = cloudscraper.create_scraper(
            browser={'browser': 'chrome','platform': 'windows','desktop': True},
            delay=10
        )
        self.cache_dir = Path("manga_cache")
        self.cache_dir.mkdir(exist_ok=True)

    def get_html(self, url: str):
        headers = {"Referer": "https://18comic.vip/"} if "18comic" in url else {"Referer": url}
        try:
            r = self.scraper.get(url, headers=headers, timeout=15)
            return r.text if r.status_code == 200 else None
        except Exception as e:
            return f"Error: {str(e)}"

# ==============================
# UI 界面 - 安卓适配版
# ==============================
def main(page: ft.Page):
    # 挂载异常处理器
    sys.excepthook = create_exception_handler(page)
    
    page.title = "Manga Purifier V5.2"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#000000"
    page.padding = 0
    
    # UI 状态定义
    url_input = ft.TextField(hint_text="URL...", expand=True, bgcolor="#1A1C23", text_size=14)
    log = ft.Text("System Standby", color="blue200", size=11)
    pb = ft.ProgressBar(visible=False, color="cyan")
    img_list = ft.ListView(expand=True, spacing=0, padding=0)

    # 异步安全渲染
    def safe_update():
        try: page.update()
        except: pass

    def on_run_click(e):
        target = url_input.value.strip()
        if not target: return
        
        img_list.controls.clear()
        pb.visible = True
        log.value = "⚡ Initializing Scraper..."; safe_update()

        def background_task():
            try:
                api = Engine()
                html = api.get_html(target)
                if not html or html.startswith("Error"):
                    log.value = f"Failed: {html}"; pb.visible = False; safe_update(); return

                soup = BeautifulSoup(html, "html.parser")
                # 兼容性提取逻辑
                raw_urls = [img.get("data-original") or img.get("src") for img in soup.find_all("img")]
                urls = [urljoin(target, u) for u in raw_urls if u and "logo" not in u.lower()]
                
                log.value = f"Found {len(urls)} images. Loading..."; safe_update()

                # 分批渲染，每 5 张刷新一次 UI，防止安卓渲染卡死
                with ThreadPoolExecutor(max_workers=4) as exe:
                    for i, url in enumerate(urls):
                        try:
                            # 简化逻辑，这里直接演示 placeholder
                            img_obj = ft.Image(src=url, fit=ft.ImageFit.FIT_WIDTH, width=page.window_width)
                            img_list.controls.append(img_obj)
                            if i % 5 == 0: safe_update()
                        except: pass
                
                log.value = "Task Finished"; pb.visible = False; safe_update()
            except Exception as ex:
                sys.excepthook(*sys.exc_info())

        threading.Thread(target=background_task, daemon=True).start()

    # 布局构造
    page.add(
        ft.Column([
            ft.Container(
                padding=ft.padding.only(top=40, left=15, right=15, bottom=10),
                content=ft.Column([
                    ft.Row([url_input, ft.IconButton(ft.icons.BOLT, on_click=on_run_click, bgcolor="blue")]),
                    pb, log
                ])
            ),
            img_list
        ], expand=True)
    )

if __name__ == "__main__":
    ft.app(target=main)
