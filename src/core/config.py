"""Preferencias persistentes de la aplicación."""

from __future__ import annotations

import json
import logging
from typing import Any

from .rutas import archivo_datos

log = logging.getLogger(__name__)

ARCHIVO = "config.json"

PREDETERMINADOS: dict[str, Any] = {
    "tema": "oscuro",            # "oscuro" | "claro"
    "modo_angulo": "DEG",        # "DEG" | "RAD" | "GRAD"
    "decimales": 6,              # dígitos significativos al mostrar resultados
    "max_historial": 500,        # entradas guardadas por módulo
    "modulo_inicial": "calculadora",
    "ventana": {},               # geometría de la ventana principal
    "disposicion": {},           # apartados abiertos y dónde estaba cada uno
    "max_paneles": 0,            # apartados a la vez; 0 = sin tope
}


class Config:
    """Diccionario de preferencias con carga y guardado en disco."""

    def __init__(self) -> None:
        self._datos: dict[str, Any] = dict(PREDETERMINADOS)
        self.cargar()

    def cargar(self) -> None:
        ruta = archivo_datos(ARCHIVO)
        if not ruta.exists():
            return
        try:
            with ruta.open(encoding="utf-8") as f:
                guardado = json.load(f)
            if isinstance(guardado, dict):
                # Sólo aceptamos claves conocidas para que un archivo viejo o
                # corrupto no introduzca basura en la configuración.
                for clave in PREDETERMINADOS:
                    if clave in guardado:
                        self._datos[clave] = guardado[clave]
        except (OSError, ValueError) as e:
            log.warning("No se pudo leer la configuración: %s", e)

    def guardar(self) -> None:
        ruta = archivo_datos(ARCHIVO)
        try:
            temporal = ruta.with_suffix(".tmp")
            with temporal.open("w", encoding="utf-8") as f:
                json.dump(self._datos, f, indent=2, ensure_ascii=False)
            temporal.replace(ruta)
        except OSError as e:
            log.warning("No se pudo guardar la configuración: %s", e)

    def get(self, clave: str, defecto: Any = None) -> Any:
        return self._datos.get(clave, defecto if defecto is not None else PREDETERMINADOS.get(clave))

    def set(self, clave: str, valor: Any) -> None:
        self._datos[clave] = valor

    def __getitem__(self, clave: str) -> Any:
        return self.get(clave)

    def __setitem__(self, clave: str, valor: Any) -> None:
        self.set(clave, valor)


# Instancia compartida por toda la aplicación.
config = Config()
