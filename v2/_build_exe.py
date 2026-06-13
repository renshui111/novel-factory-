import os, sys

# More aggressive monkey-patching for sandbox
import pathlib
_orig_resolve = pathlib.WindowsPath.resolve if hasattr(pathlib, 'WindowsPath') else pathlib.Path.resolve
def _safe_resolve(self, strict=False):
    try:
        return _orig_resolve(self, strict=strict)
    except (PermissionError, OSError):
        return pathlib.Path(str(self))
pathlib.Path.resolve = _safe_resolve

_orig_is_dir = pathlib.Path.is_dir
def _safe_is_dir(self):
    try:
        return _orig_is_dir(self)
    except (PermissionError, OSError):
        return False
pathlib.Path.is_dir = _safe_is_dir

_orig_stat = pathlib.Path.stat
def _safe_stat(self):
    try:
        return _orig_stat(self)
    except (PermissionError, OSError):
        raise FileNotFoundError(f"Cannot access {self}")
pathlib.Path.stat = _safe_stat

_orig_exists = pathlib.Path.exists
def _safe_exists(self):
    try:
        return _orig_exists(self)
    except (PermissionError, OSError):
        return False
pathlib.Path.exists = _safe_exists

os.environ["HOME"] = "D:\\项目\\小说工厂"
os.environ["USERPROFILE"] = "D:\\项目\\小说工厂"

sys.argv = ["pyinstaller", "NovelFactory.spec", "--distpath", "D:\\项目\\小说工厂\\v2\\dist", "--workpath", "D:\\项目\\小说工厂\\v2\\build", "--noconfirm"]
from PyInstaller.__main__ import run
run()
