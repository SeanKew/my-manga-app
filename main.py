import flet as ft
import asyncio
import httpx
from bs4 import BeautifulSoup

# ==========================================
# 核心逻辑类：漫画净化解析器
# ==========================================
class MangaPurifier:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://manwa.me/"
        }

    async def fetch_images(self, url: str):
        """抓取并净化漫画图片"""
        try:
            async with httpx.AsyncClient(headers=self.headers, verify=False, timeout=20.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    return None, f"请求失败，状态码: {resp.status_code}"
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                img_tags = soup.find_all('img')
                image_urls = []
                
                for img in img_tags:
                    src = img.get('data-src') or img.get('src') or img.get('data-original') or img.get('data-lazy-src')
                    if src:
                        if src.startswith('//'): src = "https:" + src
                        elif src.startswith('/'):
                            base_url = "/".join(url.split('/')[:3])
                            src = base_url + src
                        
                        src_lower = src.lower()
                        if any(x in src_lower for x in ["logo", "ad", "banner", "icon", "loading"]):
                            continue
                            
                        image_urls.append(src)
                
                image_urls = list(dict.fromkeys(image_urls))
                return image_urls, None
        except Exception as e:
            return None, f"运行异常: {str(e)}"

# ==========================================
# UI 逻辑：Flet 界面
# ==========================================
async def main(page: ft.Page):
    # 1. 窗口基础配置 - 全部使用字符串常量以防报错
    page.title = "次元幻境 MangaNexus V3.2"
    page.theme_mode = "dark" 
    page.bgcolor = "#0F111A"
    page.window_width = 550
    page.window_height = 900
    page.padding = 20
    
    purifier = MangaPurifier()

    # --- UI 组件定义 ---
    # 使用字符串 "grey" 代替 ft.colors.GREY
    log_text = ft.Text("系统就绪，等待输入链接...", color="grey", size=13)
    img_list = ft.ListView(expand=True, spacing=15, padding=10)
    loading_bar = ft.ProgressBar(visible=False, color="blue")
    
    def log(msg, is_error=False):
        log_text.value = f"> {msg}"
        log_text.color = "red" if is_error else "green"
        page.update()

    # --- 核心交互逻辑 ---
    async def start_process(e):
        url = url_input.value.strip()
        if not url.startswith("http"):
            log("请输入有效的链接 (需以 http 开头)", True)
            return

        img_list.controls.clear()
        loading_bar.visible = True
        btn_go.disabled = True
        log("解析中，正在穿透广告层...")
        page.update()

        images, error = await purifier.fetch_images(url)
        
        if error:
            log(error, True)
        elif not images:
            log("未能提取到漫画图片，请检查链接是否正确", True)
        else:
            log(f"净化完成！已提取 {len(images)} 张高清图片")
            for img_url in images:
                img_list.controls.append(
                    ft.Image(
                        src=img_url,
                        fit="fitWidth", 
                        border_radius=10,
                        loading_indicator=ft.ProgressRing(),
                        error_content=ft.Icon(name="broken_image", color="grey")
                    )
                )
            img_list.scroll_to(offset=0, duration=500)
        
        loading_bar.visible = False
        btn_go.disabled = False
        page.update()

    # --- 布局组装 ---
    url_input = ft.TextField(
        hint_text="粘贴 Manwa/拷贝 等漫画章节链接",
        border_color="blue",
        expand=True,
        on_submit=start_process,
        text_size=14
    )
    
    btn_go = ft.ElevatedButton(
        "开始净化", 
        icon="auto_fix_normal", 
        on_click=start_process
    )

    page.add(
        ft.Row([url_input, btn_go], alignment="center"),
        loading_bar,
        log_text,
        ft.Divider(height=1, color="white10"),
        img_list
    )

# 启动应用
if __name__ == "__main__":
    ft.app(target=main)
