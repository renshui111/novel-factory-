# Custom hook: force tkinter inclusion even if TclTkInfo thinks it is broken
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os, sys

tcl_path = os.path.join(sys.prefix, "tcl", "tcl8.6")
tk_path = os.path.join(sys.prefix, "tcl", "tk8.6")

hiddenimports = collect_submodules("tkinter")

datas = []
# Use _tcl_data and _tk_data to match PyInstaller standard runtime hook
if os.path.exists(tcl_path):
    datas.append((tcl_path, "_tcl_data"))
if os.path.exists(tk_path):
    datas.append((tk_path, "_tk_data"))

binaries = []
for dll_name in ["tcl86t.dll", "tk86t.dll"]:
    dll_path = os.path.join(sys.prefix, "DLLs", dll_name)
    if os.path.exists(dll_path):
        binaries.append((dll_path, "."))