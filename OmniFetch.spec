# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['yt_dlp_gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[('app.ico', '.')],
    hiddenimports=[
        'yt_dlp',
        'yt_dlp.compat._legacy',
        'yt_dlp.compat._deprecated',
        'yt_dlp.utils._legacy',
        'yt_dlp.utils._deprecated',
    ],
    hookspath=['yt_dlp/__pyinstaller'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['youtube_dl', 'youtube_dlc', 'test', 'ytdlp_plugins', 'devscripts'],
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
    name='OmniFetch',
    icon='app.ico',
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
