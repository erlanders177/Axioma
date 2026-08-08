"""Variables que define el usuario, compartidas por toda la aplicación.

Si en la calculadora se escribe ``r = 2.5``, ese valor debe servir también en los
campos de Geometría o dentro de una ecuación. Por eso viven aquí y no dentro de
un panel concreto.

No se guardan en disco a propósito: son el borrador de un problema, no una
preferencia. Al cerrar la aplicación desaparecen, igual que la memoria de una
calculadora de bolsillo.
"""

from __future__ import annotations

__all__ = [
    "ErrorVariable",
    "definir",
    "borrar",
    "borrar_todas",
    "valores",
    "resumen",
    "nombre_disponible",
]


class ErrorVariable(ValueError):
    """El nombre de la variable no se puede usar."""


#: Nombre -> valor. Deliberadamente global: es el espacio de trabajo del usuario.
_valores: dict[str, float] = {}

#: Tope para que la barra de variables no crezca sin control.
MAX_VARIABLES = 40


def _reservados() -> set[str]:
    """Nombres que ya significan algo y no se pueden reutilizar."""
    from .evaluador import CONSTANTES, FUNCIONES

    return set(CONSTANTES) | set(FUNCIONES) | {"ans", "mem"}


def nombre_disponible(nombre: str) -> bool:
    return bool(nombre) and nombre.isidentifier() and nombre not in _reservados()


def definir(nombre: str, valor: float) -> None:
    """Guarda una variable. Lanza ``ErrorVariable`` si el nombre no vale."""
    if not nombre or not nombre.isidentifier():
        raise ErrorVariable(f"«{nombre}» no es un nombre válido para una variable")
    if nombre in _reservados():
        raise ErrorVariable(
            f"«{nombre}» es un nombre reservado (una constante o una función): "
            f"elija otro."
        )
    if nombre not in _valores and len(_valores) >= MAX_VARIABLES:
        raise ErrorVariable(
            f"Ya hay {MAX_VARIABLES} variables definidas. Borre alguna antes de "
            f"añadir más."
        )
    _valores[nombre] = float(valor)


def borrar(nombre: str) -> None:
    _valores.pop(nombre, None)


def borrar_todas() -> None:
    _valores.clear()


def valores() -> dict[str, float]:
    """Copia de las variables, para pasarla al evaluador."""
    return dict(_valores)


def resumen(decimales: int = 6) -> str:
    """Texto de una línea con las variables definidas, para la interfaz."""
    if not _valores:
        return ""
    from .formato import formatear

    return "   ".join(f"{n} = {formatear(v, decimales)}" for n, v in _valores.items())
