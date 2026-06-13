# Custom hook: force tkinter inclusion even if TclTkInfo thinks it's broken
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
import sys

# Manually locate Tcl/Tk
tcl_path = os.path.join(sys.prefix, "tcl", "tcl8.6")
tk_path = os.path.join(sys.prefix, "tcl", "tk8.6")

# Collect all tkinter submodules
hiddenimports = collect_submodules("tkinter")

# Collect Tcl/Tk data
datas = []
if os.path.exists(tcl_path):
    datas.append((tcl_path, "tcl/tcl8.6"))
if os.path.exists(tk_path):
    datas.append((tk_path, "tcl/tk8.6"))

# Add DLLs
binaries = []
tcl_dll = os.path.join(sys.prefix, "DLLs", "tcl86t.dll")
tk_dll = os.path.join(sys.prefix, "DLLs", "tk86t.dll")
if os.path.exists(tcl_dll):
    binaries.append((tcl_dll, "."))
if os.path.exists(tk_dll):
    binaries.append((tk_dll, "."))
