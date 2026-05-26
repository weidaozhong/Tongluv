# -*- mode: python ; coding: utf-8 -*-
"""
蓝色小嗵 — 单文件打包配置
运行方式: python -m PyInstaller tools/build_onefile.spec
输出: dist/xiaotong.exe（单个 exe，用户数据存于 exe 同目录 geren/）
"""

block_cipher = None

import os
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(SPEC)))

a = Analysis(
    [os.path.join(_ROOT, 'main.py')],
    pathex=[_ROOT],
    binaries=[],
    datas=[
        (os.path.join(_ROOT, 'assets/animations'), 'assets/animations'),
        (os.path.join(_ROOT, 'assets/items'),      'assets/items'),
        (os.path.join(_ROOT, 'data/default_persona.txt'), 'data'),
        (os.path.join(_ROOT, 'icons'), 'icons'),
    ] + ([(os.path.join(_ROOT, 'shoukuanma.jpg'), '.')]
         if os.path.isfile(os.path.join(_ROOT, 'shoukuanma.jpg')) else []),
    hiddenimports=[
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.sip',
        'src.pak_loader',
        'src.pet_renderer_sprite',
        'src.pet_animator',
        'src.pet_state',
        'src.chat_service',
        'src.status_panel',
        'src.knowledge_hub',
        'src.game_systems',
        'src.bubble_widget',
        'src.input_monitor',
        'src.web_crawler',
        'src.user_data',
        'src.snap_system',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'matplotlib', 'numpy', 'scipy',
        'PIL', 'cv2', 'test', 'unittest',
        # 项目仅用 QtCore/QtGui/QtWidgets，排除未使用的 Qt 模块
        'PyQt5.QtQuick', 'PyQt5.QtQml', 'PyQt5.QtDesigner',
        'PyQt5.QtWebEngine', 'PyQt5.QtWebEngineCore', 'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtMultimedia', 'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtBluetooth', 'PyQt5.QtNfc', 'PyQt5.QtSensors',
        'PyQt5.QtSerialPort', 'PyQt5.QtSql', 'PyQt5.QtTest',
        'PyQt5.QtXml', 'PyQt5.QtXmlPatterns', 'PyQt5.QtHelp',
        'PyQt5.QtSvg', 'PyQt5.QtOpenGL', 'PyQt5.QtPositioning',
        'PyQt5.QtLocation', 'PyQt5.QtWebSockets', 'PyQt5.QtWebChannel',
        'PyQt5.QtNetwork', 'PyQt5.QtDBus', 'PyQt5.QtPrintSupport',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 剔除未使用的大体积 DLL（项目仅用 QPainter 2D，无需 OpenGL/D3D/QML）
_EXCLUDE_DLLS = {
    'opengl32sw.dll', 'd3dcompiler_47.dll',
    'libGLESv2.dll', 'libEGL.dll',
    'Qt5Quick.dll', 'Qt5Qml.dll', 'Qt5QmlModels.dll',
    'Qt5Designer.dll', 'Qt5Network.dll',
    'Qt5WebSockets.dll', 'Qt5Svg.dll', 'Qt5Pdf.dll',
    'Qt5DBus.dll', 'Qt5PrintSupport.dll',
}
a.binaries = [b for b in a.binaries if b[0].split('\\')[-1].split('/')[-1] not in _EXCLUDE_DLLS]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='xiaotong',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(_ROOT, 'icons/icon.ico'),
    manifest=os.path.join(_ROOT, 'tools/dpi_aware.manifest'),
    version=os.path.join(_ROOT, 'tools/version_info.py'),
)
