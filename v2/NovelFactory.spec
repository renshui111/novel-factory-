# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\项目\\小说工厂\\v2\\main.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\项目\\小说工厂\\v2\\core', 'core'), ('D:\\项目\\小说工厂\\v2\\prompts.py', '.'), ('D:\\项目\\小说工厂\\v2\\tomato.py', '.'), ('D:\\项目\\小说工厂\\v2\\stylist.py', '.'), ('D:\\项目\\小说工厂\\v2\\charset.json', '.')],
    hiddenimports=['customtkinter', 'tkinter', 'PIL', 'requests', 'bs4', 'ebooklib', 'docx'],
    hookspath=['D:\\项目\\小说工厂\\v2\\hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
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
