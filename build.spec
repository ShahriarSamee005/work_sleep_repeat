# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Work•Sleep•Repeat
# Run: pyinstaller build.spec  (or use build.bat)

import os, sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

block_cipher = None

# pyglet uses dynamic imports for platform backends
pyglet_hidden = collect_submodules('pyglet')

# PyOpenGL accelerate (optional C extensions)
opengl_hidden = collect_submodules('OpenGL')

# pystray platform backend
pystray_hidden = collect_submodules('pystray')

hidden_imports = pyglet_hidden + opengl_hidden + pystray_hidden + [
    'PIL._tkinter_finder',
    'requests',
    'certifi',
    'charset_normalizer',
    'idna',
    'urllib3',
]

# pyglet may bundle platform data
pyglet_data = collect_data_files('pyglet')

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=pyglet_data,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'scipy', 'pandas', 'IPython', 'notebook',
              'pytest', 'unittest'],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WorkSleepRepeat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,       # --windowed: no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon='WorkSleepRepeat.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='WorkSleepRepeat',
)
