# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['pypdf', 'openpyxl']
hiddenimports += collect_submodules('PySide6')
hiddenimports += ['reportlab']
hiddenimports += collect_submodules('reportlab')
hiddenimports += collect_submodules('openpyxl')


a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=[('祖师爷/祖师爷.png', '祖师爷'), ('祖师爷/香炉.png', '祖师爷'),
           ('生肖/*.png', '生肖'), ('八卦.png', '.'), ('logo.png', '.'),
           ('龙凤/*.png', '龙凤'), ('图标/*.png', '图标'),
           ('fonts/*.ttf', 'fonts')],   # 内置字体（OFL，保证各设备字形一致）
    hiddenimports=hiddenimports,
    hookspath=[],
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
    name='农历日历',
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
    icon='logo.ico',
)
