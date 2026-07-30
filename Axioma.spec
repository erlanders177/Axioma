# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para Axioma.

Generar con:  pyinstaller Axioma.spec
El resultado queda en dist/Axioma.exe
"""

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    # El manual se abre desde la aplicación (F1), así que debe viajar dentro
    # del ejecutable.
    datas=[('docs/manual_usuario.html', 'docs')],
    hiddenimports=[
        # PyInstaller no siempre detecta estos módulos, que se importan de forma
        # indirecta a través de matplotlib y sympy.
        'matplotlib.backends.backend_qt5agg',
        'mpl_toolkits.mplot3d',
        'sympy.parsing.sympy_parser',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Reducen bastante el tamaño y no se usan.
        'tkinter',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtQuick',
        'PyQt5.QtQml',
        'pytest',
        'IPython',
        'notebook',
    ],
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
    name='Axioma',
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
