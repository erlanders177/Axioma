"""Persistencia del historial de operaciones.

Cambios importantes respecto a la versión anterior:

* Cada entrada tiene un **id** propio. Antes se borraba por posición en el
  ``QListWidget``, lo que borraba la entrada equivocada en cuanto la lista y el
  archivo dejaban de estar sincronizados (por ejemplo con dos ventanas abiertas).
* Los archivos se escriben de forma **atómica** (temporal + ``replace``), así un
  cierre inesperado no deja el JSON a medias.
* El módulo **no muestra diálogos**. La lógica de negocio no debería depender de
  Qt; los errores se registran y se propagan como ``ErrorHistorial``.
* El historial se guarda en el perfil del usuario, no junto al ejecutable: el
  directorio de trabajo cambia según cómo se lance la aplicación, y la carpeta de
  instalación puede ser de sólo lectura.
"""

from __future__ import annotations

import csv
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

from .config import config
from .rutas import dir_datos

log = logging.getLogger(__name__)

# Identificadores de módulo -> nombre de archivo.
MODULOS = {
    "calculadora": "calculadora.json",
    "graficador": "graficador.json",
    "ecuaciones": "ecuaciones.json",
    "sistemas": "sistemas.json",
    "calculo": "calculo.json",
    "matrices": "matrices.json",
    "estadistica": "estadistica.json",
    "complejos": "complejos.json",
    "geometria": "geometria.json",
    "conversiones": "conversiones.json",
    "bases": "bases.json",
    "combinatoria": "combinatoria.json",
}


class ErrorHistorial(Exception):
    """El historial no se pudo leer o escribir."""


def _ruta(modulo: str) -> Path:
    try:
        return dir_datos() / MODULOS[modulo]
    except KeyError:
        raise ErrorHistorial(f"Módulo de historial desconocido: {modulo!r}") from None


def _escribir(ruta: Path, datos: list[dict[str, Any]]) -> None:
    temporal = ruta.with_suffix(".tmp")
    try:
        with temporal.open("w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
        temporal.replace(ruta)
    except OSError as e:
        log.error("Error al escribir %s: %s", ruta, e)
        raise ErrorHistorial(f"No se pudo escribir el historial: {e}") from e


def cargar(modulo: str) -> list[dict[str, Any]]:
    """Devuelve las entradas del módulo, de la más reciente a la más antigua."""
    ruta = _ruta(modulo)
    if not ruta.exists():
        return []
    try:
        with ruta.open(encoding="utf-8") as f:
            datos = json.load(f)
    except (OSError, ValueError) as e:
        # Un archivo corrupto no debe impedir usar la aplicación: lo apartamos
        # y empezamos de cero.
        log.error("Historial ilegible en %s: %s", ruta, e)
        try:
            ruta.replace(ruta.with_suffix(".json.corrupto"))
        except OSError:
            pass
        return []

    if not isinstance(datos, list):
        return []

    # Normalizamos: las entradas de la v1 no tenían id.
    # Se descartan las entradas mal formadas en vez de dejarlas romper la lista.
    normalizadas: list[dict[str, Any]] = []
    for entrada in datos:
        if not isinstance(entrada, dict) or "operacion" not in entrada:
            continue
        entrada.setdefault("id", uuid.uuid4().hex)
        entrada.setdefault("datos", {})
        entrada.setdefault("timestamp", int(time.time()))
        normalizadas.append(entrada)
    return normalizadas


def guardar(modulo: str, operacion: str, datos: dict[str, Any] | None = None) -> dict[str, Any]:
    """Añade una entrada al principio del historial y devuelve la entrada creada."""
    entrada = {
        "id": uuid.uuid4().hex,
        "operacion": operacion,
        "datos": datos or {},
        "timestamp": int(time.time()),
    }
    historial = cargar(modulo)
    historial.insert(0, entrada)

    limite = int(config.get("max_historial") or 500)
    if len(historial) > limite:
        del historial[limite:]

    _escribir(_ruta(modulo), historial)
    return entrada


def borrar(modulo: str, ids: list[str]) -> int:
    """Borra las entradas cuyos ids se indican. Devuelve cuántas se borraron."""
    if not ids:
        return 0
    objetivo = set(ids)
    historial = cargar(modulo)
    restantes = [e for e in historial if e.get("id") not in objetivo]
    borradas = len(historial) - len(restantes)
    if borradas:
        _escribir(_ruta(modulo), restantes)
    return borradas


def limpiar(modulo: str) -> None:
    """Vacía por completo el historial del módulo."""
    _escribir(_ruta(modulo), [])


def exportar(modulo: str, destino: Path | str) -> int:
    """Exporta el historial a ``.csv`` o ``.txt``. Devuelve las líneas escritas."""
    destino = Path(destino)
    historial = cargar(modulo)
    try:
        if destino.suffix.lower() == ".csv":
            with destino.open("w", encoding="utf-8-sig", newline="") as f:
                escritor = csv.writer(f, delimiter=";")
                escritor.writerow(["Fecha", "Operación"])
                for e in historial:
                    escritor.writerow([_fecha(e.get("timestamp")), e.get("operacion", "")])
        else:
            with destino.open("w", encoding="utf-8") as f:
                for e in historial:
                    f.write(f"[{_fecha(e.get('timestamp'))}] {e.get('operacion', '')}\n")
    except OSError as e:
        raise ErrorHistorial(f"No se pudo exportar: {e}") from e
    return len(historial)


def _fecha(timestamp: Any) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(timestamp)))
    except (TypeError, ValueError):
        return "-"


def fecha_legible(entrada: dict[str, Any]) -> str:
    """Fecha corta para mostrar junto a la operación en la interfaz."""
    try:
        return time.strftime("%d/%m %H:%M", time.localtime(int(entrada.get("timestamp", 0))))
    except (TypeError, ValueError, OSError):
        return ""


def ubicacion() -> Path:
    """Carpeta donde se guarda el historial, para mostrarla en «Acerca de»."""
    return dir_datos()
