import os, sys

# Force collection of tkinter submodules
hiddenimports = ['tkinter', 'tkinter.ttk', 'tkinter.font', 'tkinter.filedialog',
                 'tkinter.messagebox', 'tkinter.constants']

# DLLs only - data files handled by spec
binaries = []
tcl_dll = os.path.join(sys.prefix, 'DLLs', 'tcl86t.dll')
tk_dll = os.path.join(sys.prefix, 'DLLs', 'tk86t.dll')
for dll in [tcl_dll, tk_dll]:
    if os.path.exists(dll):
        binaries.append((dll, '.'))
