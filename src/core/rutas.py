"""Resolución de rutas de la aplicación.

Separa dos cosas que el código original mezclaba:

* **Recursos**: archivos que vienen con la aplicación (manual, iconos). Al
  empaquetar con PyInstaller viven en un directorio temporal (``sys._MEIPASS``).
* **Datos del usuario**: historial y configuración. Deben guardarse en el perfil
  del usuario, no junto al ejecutable, porque ``Program Files`` es de sólo
  lectura y porque el directorio de trabajo cambia según cómo se lance la app.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

NOMBRE_APP = "Axioma"


def _empaquetado() -> bool:
    """True si estamos corriendo dentro de un ejecutable de PyInstaller."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def raiz_recursos() -> Path:
    """Directorio donde viven los archivos que acompañan a la aplicación."""
    if _empaquetado():
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    # src/core/rutas.py -> src/core -> src -> raíz del proyecto
    return Path(__file__).resolve().parent.parent.parent


def recurso(*partes: str) -> Path:
    """Ruta a un recurso empaquetado, p. ej. ``recurso("docs", "manual.html")``."""
    return raiz_recursos().joinpath(*partes)


def dir_datos() -> Path:
    """Directorio de datos del usuario, creado si no existe."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming"
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share"

    destino = Path(base) / NOMBRE_APP
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def archivo_datos(nombre: str) -> Path:
    """Ruta a un archivo dentro del directorio de datos del usuario."""
    return dir_datos() / nombre
