# -*- mode: python ; coding: utf-8 -*-
import os

# spec 所在目录，避免硬编码绝对路径
_here = os.path.dirname(os.path.abspath(SPECPATH)) if os.path.isabs(SPECPATH) else os.path.abspath(SPECPATH)
_v2 = os.path.dirname(_here) if os.path.basename(_here) != 'v2' else _here
# 兼容：SPECPATH 可能就是 v2 目录本身
if os.path.basename(_v2) != 'v2':
    # 从 spec 文件位置回推
    _v2 = os.path.dirname(os.path.abspath(SPEC))


a = Analysis(
    [os.path.join(_v2, 'main.py')],
    pathex=[_v2],
    binaries=[],
    datas=[
        (os.path.join(_v2, 'core'), 'core'),
        (os.path.join(_v2, 'prompts.py'), '.'),
        (os.path.join(_v2, 'tomato.py'), '.'),
    ],
    hiddenimports=['customtkinter', 'tkinter', 'PIL', 'requests', 'bs4', 'ebooklib', 'docx', 'urllib.parse', 'json'],
    hookspath=[os.path.join(_v2, 'hooks')],
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
