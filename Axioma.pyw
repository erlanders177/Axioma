"""Lanzador de Axioma para hacer doble clic.

La extensión ``.pyw`` hace que Windows lo abra con ``pythonw.exe`` en lugar de
``python.exe``: la aplicación arranca **sin la ventana negra de consola** detrás.
En macOS y Linux funciona igual que ``main.py``.

Es el equivalente al ejecutable, pero ejecutando el código fuente: útil mientras
se desarrolla, o si no se quiere generar el `.exe`.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from main import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
