# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['pst_to_mbox.py'],
    pathex=[],
    binaries=[],
    datas=[('README.md', '.')],
    hiddenimports=[
        'libratom.lib.pff',
        'email.mime.multipart',
        'email.mime.text',
        'email.mime.base',
        'email.encoders',
        'email.header',
        'mailbox',
        'pathlib',
        'argparse',
        'logging',
        'time',
        'datetime',
        'base64'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='pst-to-mbox',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)