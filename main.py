import base64
import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlparse

import cloudscraper
import flet as ft
from bs4 import BeautifulSoup

# ==============================
# 核心逻辑 (保持稳定)
# ==============================
class Engine:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})
        # 安卓存储建议使用用户文档路径，这里使用相对路径在打包时会自动映射
        self.cache_dir = Path("manga_cache")
        self.cache_dir.mkdir(exist_ok=True)

    def get_html(self, url: str):
        headers = {"Referer": "https://18comic.vip/"} if "18comic" in url else {"Referer": url}
        try:
            r = self.scraper.get(url, headers=headers, timeout=15)
            return r.text if r.status_code == 200 else None
        except: return None

    def fetch_img(self, url: str, referer: str, idx: int):
        f_hash = hashlib.md5(url.encode()).hexdigest()
        p = self.cache_dir / f"{f_hash}.tmp"
        data = None
        if p.exists():
            with open(p, "rb") as f: data = f.read()
        else:
            try:
                r = self.scraper.get(url, headers={"Referer": referer}, timeout=10)
                if r.status_code == 200:
                    with open(p, "wb") as f: f.write(r.content)
                    data = r.content
            except: pass
        if data:
            ext = "webp" if b"WEBP" in data[:12] else "jpeg"
            return idx, f"data:image/{ext};base64,{base64.b64encode(data).decode()}"
        return idx, None

# ==============================
# UI 界面 - 安卓沉浸式适配
# ==============================
def main(page: ft.Page):
    # --- 【安卓全屏适配核心设置】 ---
    page.title = "次元幻境 Turbo+"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#000000"
    
    # 1. 移除内边距，利用整块屏幕
    page.padding = 0
    page.spacing = 0
    
    # 2. 窗口设置 (打包 APK 后会生效)
    page.window_full_screen = True
    
    # 3. 针对不同手机屏幕动态计算宽度
    def on_resize(e):
        for img in img_list.controls:
            img.width = page.window_width
        page.update()
    page.on_resize = on_resize

    api = Engine()
    
    # UI 控件
    # 增加输入框高度，方便手机指尖操作
    url_input = ft.TextField(
        hint_text="粘贴漫画链接...", 
        expand=True, 
        border_radius=15, 
        text_size=16,
        content_padding=15,
        bgcolor="#1A1C23",
        border_color="blue700"
    )
    
    log = ft.Text("引擎就绪", color="blue200", size=12)
    img_list = ft.ListView(expand=True, spacing=0, padding=0)
    pb = ft.ProgressBar(visible=False, color="blueAccent")

    def run(_):
        target = url_input.value.strip()
        if not target: return
        
        img_list.controls.clear()
        pb.visible = True
        log.value = "⚡ 正在穿透安全验证..."; page.update()

        def task():
            html = api.get_html(target)
            if not html:
                log.value = "❌ 破盾失败，检查网络"; pb.visible = False; page.update(); return
            
            soup = BeautifulSoup(html, "html.parser")
            origin = f"{urlparse(target).scheme}://{urlparse(target).netloc}"
            urls = []
            for img in soup.find_all("img"):
                src = img.get("data-original") or img.get("data-src") or img.get("src")
                if src:
                    if src.startswith("//"): src = "https:" + src
                    elif src.startswith("/"): src = urljoin(origin, src)
                    if not any(x in src.lower() for x in ["logo", "icon", "ad.", "banner"]):
                        urls.append(src)
            
            urls = list(dict.fromkeys(urls))
            log.value = f"📦 发现 {len(urls)} 张图，正在渲染..."; page.update()

            slots = []
            for _ in urls:
                c = ft.Image(src="", fit=ft.ImageFit.FIT_WIDTH, width=page.window_width, visible=False)
                slots.append(c)
                img_list.controls.append(c)
            page.update()

            # 多线程加载
            with ThreadPoolExecutor(max_workers=6) as exe:
                futures = [exe.submit(api.fetch_img, u, target, i) for i, u in enumerate(urls)]
                for f in futures:
                    idx, b64 = f.result()
                    if b64:
                        slots[idx].src = b64
                        slots[idx].visible = True
                        if idx % 2 == 0: page.update()
            
            log.value = "✅ 净化完成"; pb.visible = False; page.update()

        threading.Thread(target=task, daemon=True).start()

    # 增大按钮点击区域
    btn = ft.Container(
        content=ft.Icon(ft.icons.BOLT, color="white"),
        on_click=run,
        padding=10,
        bgcolor="blue700",
        border_radius=12
    )
    
    # 顶部控制栏 - 增加上内边距以避开手机摄像头/刘海屏
    top_bar = ft.Container(
        padding=ft.padding.only(top=45, left=15, right=15, bottom=10),
        bgcolor="#111318",
        content=ft.Column([
            ft.Row([url_input, btn], spacing=10),
            pb,
            log
        ], spacing=5)
    )

    page.add(
        ft.Column([
            top_bar,
            img_list
        ], expand=True, spacing=0)
    )

if __name__ == "__main__":
    # 如果在手机本地测试，指定端口
    ft.app(target=main)
