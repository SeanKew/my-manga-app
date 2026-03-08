import flet as ft
import sys
import traceback
import threading

# 1. 物理级错误监控
def main(page: ft.Page):
    # 强制设置页面配置，适配安卓全面屏
    page.title = "Manga Purifier v6.0"
    page.theme_mode = ft.ThemeMode.DARK
    page.window_full_screen = True
    page.padding = 10
    page.spacing = 10

    # 定义错误显示函数（如果后台卡死，直接在页面顶层强刷）
    def show_critical_error(msg):
        page.clean()
        page.add(ft.Text(f"CRITICAL ERROR:\n{msg}", color="red", weight="bold"))
        page.update()

    sys.excepthook = lambda t, v, tb: show_critical_error("".join(traceback.format_exception(t, v, tb)))

    # 2. 构造 UI 组件
    url_input = ft.TextField(
        label="输入漫画地址", 
        hint_text="https://...", 
        border_color="cyan",
        expand=True
    )
    
    status_text = ft.Text("系统就绪...", color="grey")
    results_list = ft.ListView(expand=True, spacing=10)

    # 3. 核心功能函数
    def start_process(e):
        target = url_input.value.strip()
        if not target:
            status_text.value = "请输入有效地址！"
            page.update()
            return
        
        status_text.value = "🚀 正在启动引擎..."
        status_text.color = "cyan"
        page.update()

        # 使用简易测试逻辑：先不运行 scraper，确认 UI 能动
        def test_logic():
            try:
                import time
                time.sleep(1)
                status_text.value = f"正在解析: {target[:20]}..."
                page.update()
                
                # 模拟加载
                for i in range(3):
                    results_list.controls.append(ft.Text(f"测试条目 {i+1}: 引擎连接中..."))
                    page.update()
                
                status_text.value = "解析完成 (演示模式)"
                page.update()
            except Exception as ex:
                show_critical_error(str(ex))

        threading.Thread(target=test_logic, daemon=True).start()

    # 4. 显式添加 View (关键：解决安卓多视图空白问题)
    page.views.clear()
    page.views.append(
        ft.View(
            "/",
            [
                ft.AppBar(title=ft.Text("漫画净化器"), bgcolor=ft.colors.SURFACE_VARIANT),
                ft.Container(
                    content=ft.Column([
                        ft.Row([url_input, ft.IconButton(ft.icons.PLAY_ARROW, on_click=start_process)]),
                        status_text,
                        ft.Divider(),
                        results_list
                    ], expand=True),
                    expand=True
                )
            ]
        )
    )
    page.go("/") # 强制路由跳转
    page.update() # 强制初始刷新

if __name__ == "__main__":
    ft.app(target=main)
