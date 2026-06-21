import pathlib, os, sys

_orig_resolve = pathlib.Path.resolve
def safe_resolve(self, strict=False):
    try: return _orig_resolve(self, strict)
    except Exception: return self
pathlib.Path.resolve = safe_resolve

_orig_is_dir = pathlib.Path.is_dir
def safe_is_dir(self):
    try: return _orig_is_dir(self)
    except Exception: return False
pathlib.Path.is_dir = safe_is_dir

_orig_stat = pathlib.Path.stat
def safe_stat(self):
    try: return _orig_stat(self)
    except Exception: return os.stat_result((0,)*10)
pathlib.Path.stat = safe_stat

_orig_exists = pathlib.Path.exists
def safe_exists(self):
    try: return _orig_exists(self)
    except Exception: return False
pathlib.Path.exists = safe_exists

_orig_is_file = pathlib.Path.is_file
def safe_is_file(self):
    try: return _orig_is_file(self)
    except Exception: return False
pathlib.Path.is_file = safe_is_file

from PyInstaller.__main__ import run as run_pyi
sys.argv = [
    "pyinstaller",
    "--onefile", "--windowed",
    "--name", "NovelFactory",
    "--add-data", r"D:\项目\小说工厂\v2\core;core",
    "--add-data", r"D:\项目\小说工厂\v2\prompts.py;.",
    "--add-data", r"D:\项目\小说工厂\v2\tomato.py;.",
    "--hidden-import", "customtkinter",
    "--hidden-import", "tkinter",
    "--hidden-import", "PIL",
    "--hidden-import", "requests",
    "--hidden-import", "bs4",
    "--hidden-import", "ebooklib",
    "--hidden-import", "docx",
    "--hidden-import", "urllib.parse",
    "--hidden-import", "json",
    "--additional-hooks-dir", r"D:\项目\小说工厂\v2\hooks",
    "--noconfirm", "--clean",
    "--distpath", r"D:\项目\小说工厂\v2\dist",
    "--workpath", r"D:\项目\小说工厂\v2\build",
    "--specpath", r"D:\项目\小说工厂\v2",
    r"D:\项目\小说工厂\v2\main.py",
]
run_pyi()