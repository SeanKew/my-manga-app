import flet as ft
import asyncio
import httpx
from bs4 import BeautifulSoup
import os

# ==========================================
# 核心逻辑类：Manwa 净化解析器
# ==========================================
class ManwaPurifier:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14; Honor Magic 6 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
        }

    async def fetch_manga_pages(self, url: str):
        """
        核心净化逻辑：抓取 HTML -> 剔除广告节点 -> 提取图片 URL
        """
        async with httpx.AsyncClient(headers=self.headers, verify=False, timeout=15.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None, f"请求失败: {resp.status_code}"
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # 1. 净化逻辑：寻找漫画图片容器 (假设 Manwa 使用了 common-content 类的 div)
            # 提示：实际开发中需根据具体页面结构微调选择器
            img_tags = soup.find_all('img')
            
            image_urls = []
            for img in img_tags:
                # 过滤掉头像、广告图标、或是过小的图片 (丙建议)
                src = img.get('data-src') or img.get('src')
                if src and "logo" not in src.lower() and "ad" not in src.lower():
                    if not src.startswith('http'):
                        src = "https:" + src if src.startswith('//') else src
                    image_urls.append(src)
            
            return image_urls, None

# ==========================================
# UI 逻辑：MagicOS 专项优化界面
# ==========================================
async def main(page: ft.Page):
    # 基础配置
    page.title = "次元幻境 MangaNexus"
    page.bgcolor = ft.colors.BLACK
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 10
    
    purifier = ManwaPurifier()

    # --- UI 元素定义 ---
    log_output = ft.Text("系统就绪，等待输入...", color=ft.colors.GREY_400, size=12)
    img_list = ft.ListView(expand=True, spacing=10, padding=10)
    progress_ring = ft.ProgressRing(visible=False, color=ft.colors.BLUE_ACCENT)
    
    def log(msg):
        log_output.value = f"> {msg}"
        page.update()

    # --- 核心交互逻辑 ---
    async def start_purification(e):
        target_url = url_input.value.strip()
        if not target_url.startswith("http"):
            log("错误：请输入有效的 http/https 链接")
            return

        # 切换 UI 状态
        img_list.controls.clear()
        progress_ring.visible = True
        btn_start.disabled = True
        log("正在连接并净化广告资源...")
        page.update()

        try:
            pages, error = await purifier.fetch_manga_pages(target_url)
            
            if error:
                log(f"净化失败: {error}")
            elif not pages:
                log("未能提取到有效图片，可能结构已变化")
            else:
                log(f"净化成功！发现 {len(pages)} 张图片")
                # 乙建议：分批加载防止内存溢出
                for url in pages:
                    img_list.controls.append(
                        ft.Image(
                            src=url,
                            fit=ft.ImageFit.FIT_WIDTH,
                            loading_indicator=ft.ProgressBar(),
                            error_content=ft.Icon(ft.icons.BROKEN_IMAGE, color="red")
                        )
                    )
                # 自动滚动到顶部
                img_list.scroll_to(offset=0, duration=500)
        except Exception as ex:
            log(f"运行时崩溃: {str(ex)}")
        finally:
            progress_ring.visible = False
            btn_start.disabled = False
            page.update()

    # --- 布局组装 ---
    url_input = ft.TextField(
        hint_text="粘贴 Manwa 链接...",
        prefix_icon=ft.icons.LINK,
        border_radius=15,
        bgcolor=ft.colors.GREY_900,
        expand=True
    )
    
    btn_start = ft.ElevatedButton(
        "开始阅读",
        icon=ft.icons.AUTO_FIX_HIGH,
        on_click=start_purification,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10))
    )

    page.add(
        ft.Row([url_input, btn_start], alignment=ft.MainAxisAlignment.CENTER),
        ft.Row([progress_ring, log_output], alignment=ft.MainAxisAlignment.CENTER),
        ft.Divider(height=1, color=ft.colors.GREY_800),
        img_list
    )

    # MagicOS 渲染心跳补丁
    async def heartbeat():
        while True:
            page.title = "次元幻境" if page.title != "次元幻境 " else "次元幻境"
            page.update()
            await asyncio.sleep(1)

    page.run_task(heartbeat)

if __name__ == "__main__":
    ft.app(target=main)
