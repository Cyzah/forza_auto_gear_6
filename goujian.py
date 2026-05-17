#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
huo - Forza Auto Gear 一键构建脚本
用法: py goujian.py
"""

import os
import sys
import glob
import shutil
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
PYTHON = sys.executable
OUTPUT = os.path.join(ROOT, 'output')
BUILD_TMP = os.path.join(ROOT, 'build_tmp')
DIST = os.path.join(OUTPUT, 'Forza Auto Gear')
ENTRY = os.path.join(ROOT, 'gui.py')
ICON = os.path.join(ROOT, 'package', 'FAG.ico')
EXAMPLE_SRC = os.path.join(ROOT, 'example')

SITE_PACKAGES = os.path.join(
    os.path.dirname(PYTHON), 'Lib', 'site-packages'
)
if not os.path.isdir(SITE_PACKAGES):
    SITE_PACKAGES = os.path.join(
        os.path.dirname(os.path.dirname(PYTHON)), 'Lib', 'site-packages'
    )


def run(cmd):
    print(f'>>> {" ".join(cmd)}')
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f'[ERROR] exit code {result.returncode}')
        sys.exit(1)


def main():
    print('=' * 50)
    print('  Forza Auto Gear - Build')
    print('=' * 50)
    print(f'  Python : {PYTHON}')
    print(f'  Output : {DIST}')
    print('=' * 50)

    # 1. check pyinstaller
    print('\n[1/5] Checking PyInstaller...')
    try:
        import PyInstaller
        print(f'  PyInstaller {PyInstaller.__version__}')
    except ImportError:
        print('  Installing PyInstaller...')
        run([PYTHON, '-m', 'pip', 'install', 'pyinstaller', '-q'])

    # 2. clean
    print('\n[2/5] Cleaning...')
    for d in [BUILD_TMP, DIST, OUTPUT]:
        if os.path.isdir(d):
            shutil.rmtree(d)
            print(f'  Removed {d}')

    # 3. PyInstaller
    print('\n[3/5] Building...')

    # Create version info file
    version_content = """VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(6, 0, 0, 0),
    prodvers=(6, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'080904B0',
          [StringStruct(u'CompanyName', u'Forza Auto Gear'),
           StringStruct(u'FileDescription', u'Forza Auto Gear - Automatic Shifting Tool'),
           StringStruct(u'FileVersion', u'6.0.0.0'),
           StringStruct(u'InternalName', u'ForzaAutoGear'),
           StringStruct(u'OriginalFilename', u'Forza Auto Gear.exe'),
           StringStruct(u'ProductName', u'Forza Auto Gear'),
           StringStruct(u'ProductVersion', u'6.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)"""
    version_path = os.path.join(BUILD_TMP, 'version_info.txt')
    os.makedirs(BUILD_TMP, exist_ok=True)
    with open(version_path, 'w', encoding='utf-8') as f:
        f.write(version_content)

    run([
        PYTHON, '-m', 'PyInstaller',
        '--noconfirm',
        '--clean',
        '--distpath', OUTPUT,
        '--workpath', BUILD_TMP,
        '--specpath', BUILD_TMP,
        '--name', 'Forza Auto Gear',
        '--icon', ICON,
        '--noconsole',
        '--version-file', version_path,
        '--paths', os.path.join(ROOT, 'forza_motorsport'),
        '--hidden-import', 'fdp',
        '--hidden-import', 'yaml',
        '--hidden-import', 'win32api',
        '--hidden-import', 'win32con',
        '--hidden-import', 'win32gui',
        '--hidden-import', 'win32process',
        '--hidden-import', 'pywintypes',
        '--hidden-import', 'pythoncom',
        '--add-data', f'{EXAMPLE_SRC}{os.pathsep}example',
        ENTRY,
    ])

    # 4. copy pywin32 DLLs, .pyd files, and Python runtime DLLs
    print('\n[4/5] Copying runtime files...')

    # Create _bin folder for DLLs and PYDs
    bin_dst = os.path.join(DIST, '_bin')
    os.makedirs(bin_dst, exist_ok=True)

    copy_dirs = [
        ('pywin32', os.path.join(SITE_PACKAGES, 'win32')),
        ('pywin32_system32', os.path.join(SITE_PACKAGES, 'pywin32_system32')),
        ('Python DLLs', os.path.join(os.path.dirname(PYTHON), 'DLLs')),
        ('Library bin', os.path.join(os.path.dirname(PYTHON), 'Library', 'bin')),
    ]

    for label, src_dir in copy_dirs:
        if not os.path.isdir(src_dir):
            print(f'  [WARN] {label} ({src_dir}) not found, skipping')
            continue
        count = 0
        for f in os.listdir(src_dir):
            if f.endswith(('.dll', '.pyd')):
                shutil.copy2(os.path.join(src_dir, f), os.path.join(bin_dst, f))
                count += 1
        print(f'  {label}: {count} files')

    # also copy pythonXX.dll from Python install root
    python_root = os.path.dirname(PYTHON)
    for f in os.listdir(python_root):
        if f.startswith('python') and f.endswith('.dll'):
            shutil.copy2(os.path.join(python_root, f), os.path.join(bin_dst, f))
            print(f'  {f}')

    print(f'  _bin/')

    # 5. copy extra files
    print('\n[5/5] Copying extra files...')
    # example
    example_dst = os.path.join(DIST, 'example')
    if not os.path.isdir(example_dst):
        shutil.copytree(EXAMPLE_SRC, example_dst)
    print(f'  example/')

    # configs folder
    configs_dst = os.path.join(DIST, 'configs')
    os.makedirs(configs_dst, exist_ok=True)
    print(f'  configs/')

    # config json files
    src_config = os.path.join(ROOT, 'config')
    if os.path.isdir(src_config):
        for f in os.listdir(src_config):
            src_file = os.path.join(src_config, f)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, configs_dst)
        print(f'  config/*.json')

    # settings.json
    settings_src = os.path.join(ROOT, 'settings.json')
    if os.path.isfile(settings_src):
        shutil.copy2(settings_src, DIST)
        print(f'  settings.json')

    # cleanup
    if os.path.isdir(BUILD_TMP):
        shutil.rmtree(BUILD_TMP)

    # done
    print('\n' + '=' * 50)
    print('  BUILD SUCCESS')
    print('=' * 50)
    print(f'  {DIST}')
    print(f'  Run: Forza Auto Gear.exe')
    print('=' * 50)


if __name__ == '__main__':
    main()
