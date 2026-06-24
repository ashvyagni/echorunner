# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for EchoRunner.

Build a single-file executable:

    pip install pyinstaller
    pyinstaller build.spec

Output appears in dist/EchoRunner (one-folder) or dist/EchoRunner.exe.

Notes
-----
* levels/*.json are bundled INTO the executable as read-only data (the game
  reads them from sys._MEIPASS when frozen — handled in src/constants.py).
* saves/ is NOT bundled; the game creates it next to the executable at runtime
  so progress is writable and survives updates. src/constants.py honors the
  _ECHO_ROOT env var / cwd for the writable location when frozen.
"""

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Bundle every level JSON. They live at <root>/levels and are resolved relative
# to the project root in src/constants.py.
level_datas = [
    (os.path.join('levels', f), 'levels')
    for f in os.listdir('levels') if f.endswith('.json')
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=level_datas,
    hiddenimports=['pygame._freetype'],  # used by the font fallback path
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc', 'doctest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EchoRunner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,            # set True to see stdout/stderr while debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',                # drop an icon.ico next to this file to use it
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EchoRunner',
)

app = BUNDLE(
    coll,
    name='EchoRunner.app',
    icon='assets/icon.icns',
    bundle_identifier='com.ashvyagni.echorunner',
    info_plist={
        'NSHighResolutionCapable': 'True',
        'CFBundleShortVersionString': '2.0.0',
    },
)
