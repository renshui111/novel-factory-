import os
import sys

# 相对脚本所在目录计算路径，避免硬编码绝对路径（中文路径换机器即失效）
ROOT = os.path.dirname(os.path.abspath(__file__))
V2 = os.path.join(ROOT, "v2")
SEP = ";" if sys.platform == "win32" else ":"

from PyInstaller.__main__ import run as run_pyi
sys.argv = [
    "pyinstaller",
    "--onefile", "--windowed",
    "--name", "NovelFactory",
    "--add-data", os.path.join(V2, "core") + SEP + "core",
    "--add-data", os.path.join(V2, "prompts.py") + SEP + ".",
    "--add-data", os.path.join(V2, "tomato.py") + SEP + ".",
    "--hidden-import", "customtkinter",
    "--hidden-import", "tkinter",
    "--hidden-import", "PIL",
    "--hidden-import", "requests",
    "--hidden-import", "bs4",
    "--hidden-import", "ebooklib",
    "--hidden-import", "docx",
    "--hidden-import", "urllib.parse",
    "--hidden-import", "json",
    "--additional-hooks-dir", os.path.join(V2, "hooks"),
    "--noconfirm", "--clean",
    "--distpath", os.path.join(V2, "dist"),
    "--workpath", os.path.join(V2, "build"),
    "--specpath", V2,
    os.path.join(V2, "main.py"),
]
run_pyi()
