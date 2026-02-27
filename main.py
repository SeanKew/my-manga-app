import flet as ft
import asyncio

async def main(page: ft.Page):
    page.title = "次元幻境"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = ft.colors.BLACK
    
    # Debug 日志区：直接显示在手机屏幕上
    debug_log = ft.Text("系统日志已启动...\n", color="green", size=10)
    
    def log(msg):
        debug_log.value += f"> {msg}\n"
        page.update()

    # 1. 强力心跳
    async def heartbeat():
        while True:
            dot.opacity = 0.01 if dot.opacity == 0 else 0
            dot.update()
            await asyncio.sleep(0.5)

    dot = ft.Container(width=1, height=1, opacity=0)
    
    # 2. 搜索逻辑
    async def go_read(e):
        log(f"开始尝试访问: {url_input.value}")
        try:
            # 引入测试：模拟一个请求
            import httpx
            async with httpx.AsyncClient(verify=False) as client:
                log("正在测试网络连通性...")
                resp = await client.get("https://www.google.com", timeout=5.0)
                log(f"网络测试成功，状态码: {resp.status_code}")
        except Exception as ex:
            log(f"网络异常: {str(ex)}")

    url_input = ft.TextField(label="漫画链接", border_color="blue")
    
    page.add(
        dot,
        ft.Text("MangaNexus v1.0", size=20, weight="bold"),
        url_input,
        ft.ElevatedButton("执行净化", on_click=go_read),
        ft.Divider(),
        ft.Text("实时调试终端:", size=12, color="grey"),
        ft.Container(
            content=debug_log,
            bgcolor="#111111",
            padding=10,
            border_radius=10,
            expand=True
        )
    )
    
    page.run_task(heartbeat)
    log("MagicOS 渲染引擎已就绪")

if __name__ == "__main__":
    ft.app(target=main)
