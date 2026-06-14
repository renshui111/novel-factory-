# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[r'D:\项目\小说工厂\v2'],
    binaries=[],
    datas=[
    ('config.json', '.'),
    (r'C:/Users/g/miniconda3/tcl/tcl8.6', 'tcl/tcl8.6'),
    (r'C:/Users/g/miniconda3/tcl/tk8.6', 'tcl/tk8.6'),
],
    hiddenimports=[
        'gui', 'core', 'core.config', 'core.llm', 'core.utils',
        'novel', 'prompts', 'deslop', 'review', 'analyze',
        'batch', 'cover', 'export', 'planner', 'project', 'dashboard', 'context', 'splitter', 'quality', 'bridge',
        'editor', 'reader_sim', 'reverse_engineer', 'downloader',
        'customtkinter', 'PIL', 'PIL._tkinter_finder',
        'openai', 'requests', 'bs4', 'urllib3', '_tkinter', 'tkinter', 'tkinter.ttk', 'tkinter.font', 'tkinter.filedialog', 'tkinter.messagebox', 'tkinter.constants',
    ],
    hookspath=[r'D:\项目\小说工厂\v2\hooks'],
    hooksconfig={},
    runtime_hooks=[r'D:\项目\小说工厂\v2\hooks\rthooks\pyi_rth__tkinter.py', r'D:\项目\小说工厂\v2\hooks\rthooks\pyi_rth_tkinter_fix.py'],
    excludes=['PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'matplotlib', 'scipy', 'pandas'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='NovelFactory',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
