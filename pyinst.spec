# -*- mode: python -*-
import os
import sys

app_name = 'AndrillerCE'
block_cipher = None

ONE_FILE = False if sys.platform == 'win32' else True


def get_binaries():
    if sys.platform == 'darwin':
        return [
            ('/Library/Frameworks/Python.framework/Versions/3.7/lib/libtk8.6.dylib', 'tk'),
            ('/Library/Frameworks/Python.framework/Versions/3.7/lib/libtcl8.6.dylib', 'tcl')]
    return []


a = Analysis(
    ['andriller-gui.py'],
    pathex=[os.path.abspath(os.getcwd())],
    binaries=get_binaries(),
    datas=[
        ('andriller/bin/*', 'bin'),
        ('andriller/res/*', 'res'),
        ('andriller/templates/*', 'templates'),
    ],
    hiddenimports=[
        # 'packaging',
        # 'packaging.specifiers',
        # 'packaging.requirements',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)


pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)


def get_icon():
    return {
        'linux': 'icon3.xbm',
        'linux2': 'icon3.xbm',
        'win32': 'icon3.ico',
        'darwin': 'icon3.icns',
    }.get(sys.platform, 'icon3.ico')


if ONE_FILE:
    # One file
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='andriller',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        runtime_tmpdir=None,
        console=False,
        icon=os.path.join('andriller', 'res', get_icon()),
    )
    if sys.platform == 'darwin':
        app = BUNDLE(
            exe,
            name=f'{app_name}.app',
            icon='andriller/res/icon3.icns',
            bundle_identifier=None)
else:
    # Many files
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='andriller',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon=os.path.join('andriller', 'res', get_icon()),
    )
    coll = COLLECT(
        exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, name=app_name
    )
