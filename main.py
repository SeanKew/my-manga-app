import flet as ft

def main(page: ft.Page):
    # 1. 强制设置背景色，避免默认黑色干扰判断
    page.bgcolor = ft.colors.BLUE_GREY_900
    page.padding = 0
    
    # 诊断函数：点击按钮切换网址
    def load_test_url(e):
        print("切换到测试网址")
        webview.url = "https://www.bing.com" # 如果 Bing 能显示，说明之前的 HTML 格式有问题
        page.update()

    # 2. 原生诊断组件 (如果你能看到这个按钮，说明 Flet 渲染正常)
    test_button = ft.ElevatedButton(
        "如果看到此按钮，说明 Flet 正常。点我测试 Bing",
        on_click=load_test_url,
        color=ft.colors.WHITE,
        bgcolor=ft.colors.BLUE_700,
    )

    # 3. 增强型 WebView 配置
    webview = ft.WebView(
        url="https://www.google.com", # 先用标准网址测试，排除 HTML 代码干扰
        expand=True, # 关键：强制拉伸填充
        on_page_started=lambda _: print("网页开始加载"),
        on_page_ended=lambda _: print("网页加载完成"),
    )

    # 4. 使用明确的布局结构
    page.add(
        ft.SafeArea(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=test_button,
                        padding=20,
                        alignment=ft.alignment.center
                    ),
                    # WebView 必须放在一个 expand 的容器里
                    ft.Container(
                        content=webview,
                        expand=True,
                        border=ft.border.all(2, ft.colors.RED), # 红色边框：看看 WebView 到底占了多大地方
                    )
                ],
                expand=True,
                spacing=0
            )
        )
    )

    # 5. 最后的唤醒
    page.update()

ft.app(target=main)
