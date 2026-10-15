# -*- mode: python ; coding: utf-8 -*-
"""Windows Qt Widgets onefile build; elevation is handled once in main.py."""
import sys
from pathlib import Path

from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo, VarStruct,
    VSVersionInfo,
)

project_root = Path(SPECPATH).resolve().parents[1]
sys.path.insert(0, str(project_root / 'src'))
from metadata import (APP_NAME, COPYRIGHT, EXECUTABLE_NAME, ORGANIZATION,
                      PROJECT_URL, VERSION, WINDOWS_FILE_VERSION)

brand_png = project_root / 'assets/kervan-camel.png'
brand_ico = project_root / 'assets/kervan-camel.ico'
if not brand_png.is_file() or not brand_ico.is_file():
    raise RuntimeError('Approved Kervan camel assets are required for a Windows build')

version_info = VSVersionInfo(
    ffi=FixedFileInfo(filevers=WINDOWS_FILE_VERSION,
                      prodvers=WINDOWS_FILE_VERSION, mask=0x3f, flags=0x0,
                      OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
    kids=[
        StringFileInfo([StringTable('040904B0', [
                        StringStruct('CompanyName', ORGANIZATION),
                        StringStruct('FileDescription', APP_NAME),
                        StringStruct('FileVersion', VERSION),
                        StringStruct('InternalName', APP_NAME),
                        StringStruct('OriginalFilename', EXECUTABLE_NAME + '.exe'),
                        StringStruct('ProductName', APP_NAME),
                        StringStruct('ProductVersion', VERSION),
                        StringStruct('LegalCopyright', COPYRIGHT),
                        StringStruct('Comments', PROJECT_URL)])]),
        VarFileInfo([VarStruct('Translation', [1033, 1200])]),
    ],
)

a = Analysis(
    [str(project_root / 'src/main.py')],
    pathex=[str(project_root / 'src')],
    binaries=[],
    datas=[(str(brand_png), 'assets'),
           (str(project_root / 'bin'), 'bin'),
           (str(project_root / 'LICENSE'), '.'),
           (str(project_root / 'THIRD_PARTY_NOTICES.md'), '.'),
           (str(project_root / 'packaging/licenses'), 'licenses')],
    hiddenimports=[], hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['packaged_smoke'], noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name=EXECUTABLE_NAME, debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=False,
    icon=str(brand_ico), version=version_info,
    uac_admin=False,
)
