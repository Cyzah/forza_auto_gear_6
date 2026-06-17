import os
import sys
import shutil
import subprocess
import time

PROJECT = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(PROJECT, '.venv', 'Scripts', 'python.exe')
if not os.path.exists(VENV_PYTHON):
    VENV_PYTHON = sys.executable
APP_NAME = 'ForzaAutoGear'
ENTRY = os.path.join(PROJECT, 'gui.py')
OUTPUT = os.path.join(PROJECT, 'output')
DIST = os.path.join(PROJECT, 'dist')
BUILD = os.path.join(PROJECT, 'build')

print('[1/5] Checking PyInstaller...')
result = subprocess.run([VENV_PYTHON, '-c', 'import PyInstaller'], capture_output=True)
if result.returncode != 0:
    subprocess.run([VENV_PYTHON, '-m', 'pip', 'install', 'pyinstaller', '--quiet'], check=True)

print('[2/5] Cleaning old build artifacts...')
for d in [DIST, BUILD, OUTPUT]:
    if os.path.exists(d):
        shutil.rmtree(d)

print('[2.5/5] Ensuring required directories...')
configs_dir = os.path.join(PROJECT, 'configs')
os.makedirs(configs_dir, exist_ok=True)
settings_file = os.path.join(configs_dir, 'settings.json')
if not os.path.exists(settings_file):
    import json
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump({"clutch": "i", "upshift": "e", "downshift": "q", "offroad_rally": False, "enable_clutch": True, "farming": False}, f, indent=4)
example_dir = os.path.join(PROJECT, 'example')
os.makedirs(example_dir, exist_ok=True)

print('[3/5] Building... (first run ~3-5 min, subsequent runs use cache)')
sep = ';'

unused = [
    'tkinter', 'test', 'email', 'pydoc', 'pdb',
    'lib2to3', 'distutils', 'setuptools', 'pkg_resources',
    'PySide6.Qt3DAnimation', 'PySide6.Qt3DCore', 'PySide6.Qt3DExtras',
    'PySide6.Qt3DInput', 'PySide6.Qt3DLogic', 'PySide6.Qt3DRender',
    'PySide6.QtAsyncio', 'PySide6.QtAxContainer', 'PySide6.QtAxBase',
    'PySide6.QtBluetooth', 'PySide6.QtCanvasPainter',
    'PySide6.QtCharts', 'PySide6.QtConcurrent', 'PySide6.QtDBus',
    'PySide6.QtDataVisualization', 'PySide6.QtDesigner',
    'PySide6.QtGraphs', 'PySide6.QtGraphsWidgets',
    'PySide6.QtHelp', 'PySide6.QtHttpServer',
    'PySide6.QtLocation', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
    'PySide6.QtNfc',
    'PySide6.QtOpenGL', 'PySide6.QtOpenGLWidgets',
    'PySide6.QtPdf', 'PySide6.QtPdfWidgets',
    'PySide6.QtPositioning', 'PySide6.QtPrintSupport',
    'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtQuick3D',
    'PySide6.QtQuickControls2', 'PySide6.QtQuickTest', 'PySide6.QtQuickWidgets',
    'PySide6.QtRemoteObjects', 'PySide6.QtScxml',
    'PySide6.QtSensors', 'PySide6.QtSerialBus',
    'PySide6.QtSvg', 'PySide6.QtSvgWidgets',
    'PySide6.QtTest', 'PySide6.QtTextToSpeech',
    'PySide6.QtUiTools', 'PySide6.QtWebChannel',
    'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineQuick',
    'PySide6.QtWebEngineWidgets', 'PySide6.QtWebSockets',
    'IPython', 'notebook', 'scipy', 'pandas',
    'xmlrpc', 'pydoc_data', 'turtledemo',
    'idlelib', 'idlelib.idle_test', 'lib2to3.tests',
    'distutils.command', 'setuptools._vendor',
    'pkg_resources._vendor', 'pkg_resources.extern',
]

exclude_args = []
for mod in unused:
    exclude_args.extend(['--exclude-module', mod])

cmd = [
    VENV_PYTHON, '-m', 'PyInstaller',
    '--noconfirm', '--onedir', '--windowed',
    '--icon', os.path.join(PROJECT, 'icon', '3.ico'),
    '--name', APP_NAME,
    '--paths', os.path.join(PROJECT, 'forza_motorsport'),
    '--hidden-import', 'fdp',
    '--hidden-import', 'numpy',
    '--hidden-import', 'matplotlib.backends.backend_qtagg',
    f'--add-data={os.path.join(PROJECT, "forza_motorsport", "fdp.py")}{sep}forza_motorsport',
    f'--add-data={os.path.join(PROJECT, "configs")}{sep}configs',
    f'--add-data={os.path.join(PROJECT, "example")}{sep}example',
    '--collect-data', 'matplotlib',
    '--distpath', OUTPUT, '--workpath', BUILD, '--specpath', BUILD,
] + exclude_args + [ENTRY]

start = time.time()
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
for line in proc.stdout:
    print(line, end='')
proc.wait()
elapsed = time.time() - start

if proc.returncode != 0:
    print(f'\nBuild failed! ({elapsed:.0f}s)')
    sys.exit(1)

print('[4/5] Cleaning unnecessary files...')
internal = os.path.join(OUTPUT, APP_NAME, '_internal')

# 1. PySide6 translations: keep only English and Chinese
translations_dir = os.path.join(internal, 'PySide6', 'translations')
if os.path.isdir(translations_dir):
    keep_langs = ['qt_en', 'qt_zh_CN', 'qt_zh_TW', 'qtbase_en', 'qtbase_zh_CN', 'qtbase_zh_TW']
    for f in os.listdir(translations_dir):
        name = os.path.splitext(f)[0]
        if name not in keep_langs:
            os.remove(os.path.join(translations_dir, f))

# 2. PySide6 image format plugins: keep only qico (for icon)
img_dir = os.path.join(internal, 'PySide6', 'plugins', 'imageformats')
if os.path.isdir(img_dir):
    for f in os.listdir(img_dir):
        if f != 'qico.dll':
            os.remove(os.path.join(img_dir, f))

# 3. PySide6 plugins: remove unused plugin folders
plugins_dir = os.path.join(internal, 'PySide6', 'plugins')
for sub in ['networkinformation', 'platforminputcontexts', 'tls', 'iconengines', 'generic', 'styles']:
    p = os.path.join(plugins_dir, sub)
    if os.path.isdir(p):
        shutil.rmtree(p)

# 4. PySide6: remove unused DLLs
pyside_dir = os.path.join(internal, 'PySide6')
for f in os.listdir(pyside_dir):
    name_lower = f.lower()
    if name_lower.startswith('qt6qml') or name_lower.startswith('qt6quick') \
            or 'virtualkeyboard' in name_lower or 'network' in name_lower \
            or name_lower.startswith('qt6pdf') or name_lower == 'opengl32sw.dll' \
            or name_lower.startswith('qt6svg') or name_lower.startswith('qt6test') \
            or name_lower.startswith('qt6location') or name_lower.startswith('qt6bluetooth') \
            or name_lower.startswith('qt6nfc') or name_lower.startswith('qt6sensors') \
            or name_lower.startswith('qt6serialbus') or name_lower.startswith('qt6remoteobjects') \
            or name_lower.startswith('qt6scxml') or name_lower.startswith('qt6texttospeech') \
            or name_lower.startswith('qt6webchannel') or name_lower.startswith('qt6websockets') \
            or name_lower.startswith('qt6positioning') or name_lower.startswith('qt6printsupport') \
            or name_lower.startswith('qt6help') or name_lower.startswith('qt6httpserver'):
        os.remove(os.path.join(pyside_dir, f))

# 5. matplotlib: remove unnecessary files
mpl_data = os.path.join(internal, 'matplotlib', 'mpl-data')
for sub in ['sample_data', 'images', 'plot_directive', 'stylelib', 'kpsewhich.lua']:
    p = os.path.join(mpl_data, sub)
    if os.path.isdir(p):
        shutil.rmtree(p)
    elif os.path.isfile(p):
        os.remove(p)

# 6. matplotlib fonts: keep only essential fonts
mpl_fonts = os.path.join(mpl_data, 'fonts')
if os.path.isdir(mpl_fonts):
    keep_font_dirs = ['ttf']
    keep_font_files = ['DejaVuSans.ttf', 'DejaVuSans-Bold.ttf', 'LastResortHE-Regular.ttf']
    for item in os.listdir(mpl_fonts):
        p = os.path.join(mpl_fonts, item)
        if item in keep_font_dirs:
            if os.path.isdir(p):
                for f in os.listdir(p):
                    fp = os.path.join(p, f)
                    if f not in keep_font_files and os.path.isfile(fp):
                        os.remove(fp)
        else:
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)

# 7. Remove example folder from _internal (already copied to app root)
example_dir = os.path.join(internal, 'example')
if os.path.isdir(example_dir):
    shutil.rmtree(example_dir)

# 8. Remove configs from _internal (already copied to app root)
configs_dir = os.path.join(internal, 'configs')
if os.path.isdir(configs_dir):
    shutil.rmtree(configs_dir)

# 9. Remove unnecessary Python files
for f in ['__pycache__', 'LICENSE', 'README.md', 'setup.py', 'setup.cfg', 'pyproject.toml']:
    p = os.path.join(internal, f)
    if os.path.isdir(p):
        shutil.rmtree(p)
    elif os.path.isfile(p):
        os.remove(p)

# 10. Remove numpy dist-info
numpy_dist = os.path.join(internal, 'numpy-*.dist-info')
import glob
for d in glob.glob(numpy_dist):
    if os.path.isdir(d):
        shutil.rmtree(d)

# 11. Remove unused PIL modules
pil_dir = os.path.join(internal, 'PIL')
if os.path.isdir(pil_dir):
    for f in ['_avif.cp313-win_amd64.pyd', '_webp.cp313-win_amd64.pyd']:
        p = os.path.join(pil_dir, f)
        if os.path.isfile(p):
            os.remove(p)

# 12. Remove Qt6OpenGL.dll (not used)
pyside_dir = os.path.join(internal, 'PySide6')
for f in ['Qt6OpenGL.dll']:
    p = os.path.join(pyside_dir, f)
    if os.path.isfile(p):
        os.remove(p)

print('[5/5] Organizing output...')
app_dir = os.path.join(OUTPUT, APP_NAME)
os.makedirs(os.path.join(app_dir, 'log'), exist_ok=True)

print(f'\nBuild complete! ({elapsed:.0f}s)')
# Copy icon to output
icon_src = os.path.join(PROJECT, 'icon', '3.ico')
icon_dst = os.path.join(app_dir, 'icon', '3.ico')
os.makedirs(os.path.join(app_dir, 'icon'), exist_ok=True)
shutil.copy2(icon_src, icon_dst)

print(f'Output: {app_dir}')
