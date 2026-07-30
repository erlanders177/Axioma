# -*- mode: python ; coding: utf-8 -*-
"""Receta de PyInstaller para Axioma.

Generar con:  pyinstaller Axioma.spec
El resultado queda en dist/Axioma.exe
"""

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    # El manual se abre desde la aplicación (F1) y el icono se carga en tiempo
    # de ejecución, así que ambos deben viajar dentro del ejecutable.
    datas=[
        ('docs/manual_usuario.html', 'docs'),
        ('assets/axioma.ico', 'assets'),
        ('assets/axioma.png', 'assets'),
    ],
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
    # Axioma sólo necesita PyQt5, sympy, numpy y matplotlib. Sin esta lista,
    # PyInstaller arrastra cualquier biblioteca pesada que esté instalada en el
    # entorno: sympy.lambdify y sympy.printing nombran backends opcionales
    # (torch, tensorflow…) y matplotlib hace lo propio con los suyos, así que el
    # análisis estático los da por necesarios. En un entorno de desarrollo con
    # torch instalado, el ejecutable pasaba de ~90 MB a 343 MB.
    excludes=[
        # Aprendizaje automático y cálculo numérico pesado: no se usan.
        'torch', 'torchvision', 'torchaudio',
        'tensorflow', 'jax', 'jaxlib',
        'transformers', 'tokenizers', 'safetensors', 'huggingface_hub',
        'onnxruntime', 'onnx',
        'sklearn', 'scipy', 'pandas', 'pyarrow',
        'numba', 'llvmlite',
        'networkx',
        # Herramientas de desarrollo y cuadernos.
        'pytest', 'IPython', 'notebook', 'jupyter', 'jupyter_client',
        'ipykernel', 'nbconvert', 'nbformat',
        # Interfaces alternativas que no se usan.
        'tkinter',
        'PyQt5.QtWebEngineWidgets', 'PyQt5.QtQuick', 'PyQt5.QtQml',
        'PyQt5.QtBluetooth', 'PyQt5.QtNetwork', 'PyQt5.QtMultimedia',
        'PySide2', 'PySide6', 'PyQt6',
        'pyglet', 'wx',
        # Pillow NO se puede excluir aunque parezca que sólo lo usa
        # tools/generar_icono.py: matplotlib.colors lo importa al cargarse, no de
        # forma diferida, y sin él la aplicación no llega ni a abrir la ventana.
        # Varios que entran de rebote.
        'pydantic', 'pydantic_core', 'grpc', 'grpcio',
        'Pythonwin', 'win32com',
        'sqlalchemy', 'cryptography',
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
    icon='assets/axioma.ico',
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
