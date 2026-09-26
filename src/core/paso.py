"""Una línea de un desarrollo paso a paso.

Aparte de :mod:`pasos` porque aquél necesita sympy, y esto no: la calculadora
del navegador describe sus pasos sencillos («escriba una cuenta primero») sin
tener sympy cargado.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Paso:
    """Una línea del desarrollo."""

    titulo: str
    detalle: str = ""
    expresion: str = ""
    #: Sangría, para que las reglas anidadas se vean como tales.
    nivel: int = 0


@dataclass
class _Acumulador:
    pasos: list[Paso] = field(default_factory=list)

    def add(self, titulo: str, detalle: str = "", expresion: str = "",
            nivel: int = 0) -> None:
        self.pasos.append(Paso(titulo, detalle, expresion, nivel))
