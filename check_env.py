import os
import sys
from pathlib import Path

def fix_environment():
    print("🔍 [Checking Environment...]")
    
    # 1. 确保入口文件存在
    py_files = list(Path('.').glob('*.py'))
    main_file = Path('main.py')
    
    if not main_file.exists():
        if py_files:
            target = py_files[0]
            print(f"⚠️ 未找到 main.py，已将 {target.name} 重命名为 main.py")
            os.rename(target, 'main.py')
        else:
            print("❌ 错误：仓库中没有找到任何 .py 文件！")
            sys.exit(1)
    else:
        print("✅ 找到 main.py")

    # 2. 强制生成 requirements.txt
    deps = ["flet", "cloudscraper", "beautifulsoup4"]
    with open("requirements.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(deps))
    print("✅ 依赖清单 requirements.txt 已强制更新")

    # 3. 创建必要的目录结构
    Path("assets").mkdir(exist_ok=True)
    print("✅ 资源目录 assets 已就绪")

    # 4. 验证 Flet 安装情况
    try:
        import flet
        print(f"✅ Flet 库已安装 (Version: {flet.__version__})")
    except ImportError:
        print("⚠️ Flet 尚未安装，将由 YAML 流程处理")

if __name__ == "__main__":
    fix_environment()
