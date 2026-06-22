# -*- coding: utf-8 -*-
"""build_exe.py - 一键打包 NovelFactory.exe

在本机 Python 环境运行:
    pip install pyinstaller customtkinter requests Pillow
    python build_exe.py

输出: dist/NovelFactory.exe
"""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))  # v2/
SEP = ";" if os.name == "nt" else ":"

from PyInstaller.__main__ import run as run_pyi

sys.argv = [
    "pyinstaller",
    "--onefile", "--windowed",
    "--name", "NovelFactory",
    "--add-data", os.path.join(ROOT, "core") + SEP + "core",
    "--add-data", os.path.join(ROOT, "prompts.py") + SEP + ".",
    "--add-data", os.path.join(ROOT, "tomato.py") + SEP + ".",
    "--add-data", os.path.join(ROOT, "stylist.py") + SEP + ".",
    "--add-data", os.path.join(ROOT, "charset.json") + SEP + ".",
    "--hidden-import", "customtkinter",
    "--hidden-import", "tkinter",
    "--hidden-import", "PIL",
    "--hidden-import", "requests",
    "--hidden-import", "bs4",
    "--hidden-import", "ebooklib",
    "--hidden-import", "docx",
    "--additional-hooks-dir", os.path.join(ROOT, "hooks"),
    "--noconfirm", "--clean",
    "--distpath", os.path.join(ROOT, "dist"),
    "--workpath", os.path.join(ROOT, "build"),
    "--specpath", ROOT,
    os.path.join(ROOT, "main.py"),
]
run_pyi()
