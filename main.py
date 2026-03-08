import base64
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Optional, Tuple, List
from urllib.parse import urljoin, urlparse

import cloudscraper
import flet as ft
from bs4 import BeautifulSoup

# ==============================
# 核心逻辑
# ==============================
class MangaPurifier:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
        self.cache_dir = Path("manga_cache")
        self.cache_dir.mkdir(exist_ok=True)

    def fetch_page_content(self, url: str):
        headers = {"Referer": "https://18comic.vip/"} if "18comic" in url else {"Referer": url}
        try:
            resp = self.scraper.get(url, headers=headers, timeout=20)
            return (resp.text, None) if resp.status_code == 200 else (None, f"Status: {resp.status_code}")
        except Exception as e: return None, str(e)

    def get_image_data(self, img_url: str, referer: str, index: int):
        """增加 index 返回，用于精准定位"""
        file_hash = hashlib.md5(img_url.encode()).hexdigest()
        cache_path = self.cache_dir / f"{file_hash}.tmp"
        
        data = None
        if cache_path.exists() and cache_path.stat().st_size > 1024:
            with open(cache_path, "rb") as f: data = f.read()
        else:
            try:
                resp = self.scraper.get(img_url, headers={"Referer": referer}, timeout=15)
                if resp.status_code == 200:
                    with open(cache_path, "wb") as f: f.write(resp.content)
                    data = resp.content
            except: pass
        
        if data:
            return index, self._to_base64(data)
        return index, None

    def _to_base64(self, data: bytes):
        ext = "webp" if b"WEBP" in data[:12] else "jpeg"
        return f"data:image/{ext};base64,{base64.b64encode(data).decode()}"

    def parse_urls(self, html: str, base_url: str):
        soup = BeautifulSoup(html, "html.parser")
        p = urlparse(base_url)
        origin = f"{p.scheme}://{p.netloc}"
        urls = []
        for img in soup.find_all("img"):
            src = img.get("data-original") or img.get("data-src") or img.get("src")
            if src:
                if src.startswith("//"): src = "https:" + src
                elif src.startswith("/"): src = urljoin(origin, src)
                if not any(x in src.lower() for x in ["logo", "icon", "ad.", "banner"]):
                    urls.append(src)
        return list(dict.fromkeys(urls))

# ==============================
# UI 界面 - 排序优化版
# ==============================
def main(page: ft.Page):
    page.title = "次元幻境 V4.9 (Order Sync)"
    page.theme_mode = "dark"
    page.window_width = 500
    page.window_height = 850
    page.padding = 0
    page.bgcolor = "#0B0E14"

    purifier = MangaPurifier()
    img_list = ft.ListView(expand=True, spacing=0, padding=0)
    log_text = ft.Text("内核已就绪", color="cyan", size=12)
    loading_bar = ft.ProgressBar(visible=False, color="cyan")
    url_input = ft.TextField(hint_text="粘贴链接...", expand=True, bgcolor="#1A1C23")

    def start_process(e):
        url = url_input.value.strip()
        if not url: return
        
        img_list.controls.clear()
        loading_bar.visible = True
        btn_go.disabled = True
        log_text.value = "> 正在解析页面内容..."; page.update()

        def task():
            html, err = purifier.fetch_page_content(url)
            if err:
                log_text.value = f"> 报错: {err}"; loading_bar.visible = False; btn_go.disabled = False; page.update(); return
            
            urls = purifier.parse_urls(html, url)
            total = len(urls)
            log_text.value = f"> 发现 {total} 张图，正在按序渲染..."; page.update()

            # 【排序核心】预先创建相同数量的“占位控件”
            # 我们先放一堆空的 ft.Image 占座，此时它们不显示
            placeholders = []
            for _ in range(total):
                img_obj = ft.Image(src="", fit="fitWidth", width=page.window_width, visible=False)
                placeholders.append(img_obj)
                img_list.controls.append(img_obj)
            page.update()

            # 使用线程池下载，但回调时直接修改占位控件
            with ThreadPoolExecutor(max_workers=8) as executor:
                # 提交任务时带上索引 i
                future_tasks = [executor.submit(purifier.get_image_data, u, url, i) for i, u in enumerate(urls)]
                
                # 实时刷新：哪张好了就显现哪张，但位置是死固定的
                from concurrent.futures import as_completed
                for future in as_completed(future_tasks):
                    idx, b64 = future.result()
                    if b64:
                        placeholders[idx].src = b64
                        placeholders[idx].visible = True  # 下载好了才显现
                        page.update()

            log_text.value = "> 全部图片已归位！"; loading_bar.visible = False; btn_go.disabled = False; page.update()

        threading.Thread(target=task, daemon=True).start()

    btn_go = ft.ElevatedButton("开始", on_click=start_process)

    page.add(
        ft.Column([
            ft.Container(
                content=ft.Column([ft.Row([url_input, btn_go]), loading_bar, log_text], spacing=5),
                padding=15, bgcolor="#1A1C23"
            ),
            ft.Divider(height=1, color="white10"),
            img_list
        ], expand=True, spacing=0)
    )

if __name__ == "__main__":
    ft.app(target=main)
