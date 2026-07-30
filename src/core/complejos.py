"""Números complejos: aritmética, forma polar y raíces.

Se admiten las notaciones habituales en clase:

* binómica: ``3+4i``, ``-2i``, ``5``
* polar en grados: ``5∠53.13`` o ``5<53.13``
* polar en radianes: ``5∠0.927rad``
"""

from __future__ import annotations

import cmath
import math
import re

from .formato import formatear

__all__ = [
    "ErrorComplejo",
    "analizar_complejo",
    "binomica",
    "polar",
    "ficha",
    "operar",
    "raices",
    "potencia",
    "OPERACIONES",
]


class ErrorComplejo(ValueError):
    """El número complejo o la operación no son válidos."""


# 5∠53.13  |  5<53.13  |  5∠0.927rad
_POLAR = re.compile(
    r"^\s*([+-]?[\d.]+(?:[eE][+-]?\d+)?)\s*[∠<@]\s*([+-]?[\d.]+(?:[eE][+-]?\d+)?)\s*(rad|r)?\s*$"
)


def analizar_complejo(texto: str, nombre: str = "el número") -> complex:
    """Convierte texto en un ``complex`` de Python."""
    limpio = texto.strip()
    if not limpio:
        raise ErrorComplejo(f"Introduzca {nombre}")

    coincidencia = _POLAR.match(limpio)
    if coincidencia:
        modulo = float(coincidencia.group(1))
        angulo = float(coincidencia.group(2))
        if not coincidencia.group(3):
            angulo = math.radians(angulo)
        return cmath.rect(modulo, angulo)

    # Notación binómica: se normaliza a la sintaxis de Python (j en vez de i).
    normalizado = (
        limpio.replace(" ", "")
        .replace(",", ".")
        .replace("I", "i")
        .replace("*", "")
    )
    # `3+4i` -> `3+4j`;  `i` suelto -> `1j`;  `-i` -> `-1j`
    normalizado = re.sub(r"(?<![\d.])i", "1i", normalizado)
    normalizado = normalizado.replace("i", "j")

    if not re.fullmatch(r"[\d.+\-jeE]*", normalizado):
        raise ErrorComplejo(
            f"No se entiende {nombre}: «{texto.strip()}». "
            f"Use la forma 3+4i o la polar 5∠53.13"
        )

    try:
        return complex(normalizado)
    except ValueError:
        raise ErrorComplejo(
            f"No se entiende {nombre}: «{texto.strip()}». "
            f"Use la forma 3+4i o la polar 5∠53.13"
        ) from None


def binomica(z: complex, decimales: int = 6) -> str:
    """Forma binómica ``a + bi``."""
    real = formatear(z.real, decimales)
    if abs(z.imag) < 1e-14:
        return real
    if abs(z.real) < 1e-14:
        return f"{formatear(z.imag, decimales)}i"
    signo = "−" if z.imag < 0 else "+"
    return f"{real} {signo} {formatear(abs(z.imag), decimales)}i"


def polar(z: complex, decimales: int = 6, grados: bool = True) -> str:
    """Forma polar ``r∠θ``."""
    modulo, angulo = cmath.polar(z)
    if grados:
        return f"{formatear(modulo, decimales)} ∠ {formatear(math.degrees(angulo), decimales)}°"
    return f"{formatear(modulo, decimales)} ∠ {formatear(angulo, decimales)} rad"


def ficha(z: complex, decimales: int = 6) -> list[tuple[str, str]]:
    """Todas las representaciones y propiedades de un complejo."""
    modulo, angulo = cmath.polar(z)
    filas = [
        ("Forma binómica", binomica(z, decimales)),
        ("Parte real", formatear(z.real, decimales)),
        ("Parte imaginaria", formatear(z.imag, decimales)),
        ("", ""),
        ("Módulo |z|", formatear(modulo, decimales)),
        ("Argumento (grados)", formatear(math.degrees(angulo), decimales) + "°"),
        ("Argumento (radianes)", formatear(angulo, decimales)),
        ("Forma polar", polar(z, decimales)),
        ("Forma trigonométrica",
         f"{formatear(modulo, decimales)}·(cos {formatear(math.degrees(angulo), 4)}° "
         f"+ i·sen {formatear(math.degrees(angulo), 4)}°)"),
        ("Forma exponencial", f"{formatear(modulo, decimales)}·e^({formatear(angulo, decimales)}i)"),
        ("", ""),
        ("Conjugado z̄", binomica(z.conjugate(), decimales)),
        ("Opuesto −z", binomica(-z, decimales)),
    ]

    if modulo > 0:
        filas.append(("Inverso 1/z", binomica(1 / z, decimales)))
        filas.append(("Normalizado z/|z|", binomica(z / modulo, decimales)))
    else:
        filas.append(("Inverso 1/z", "no existe: el módulo es 0"))

    filas.append(("|z|²  (z·z̄)", formatear(modulo ** 2, decimales)))

    cuadrante = _cuadrante(z)
    if cuadrante:
        filas.append(("Cuadrante", cuadrante))
    return filas


def _cuadrante(z: complex) -> str:
    if abs(z.real) < 1e-14 and abs(z.imag) < 1e-14:
        return "origen"
    if abs(z.imag) < 1e-14:
        return "eje real positivo" if z.real > 0 else "eje real negativo"
    if abs(z.real) < 1e-14:
        return "eje imaginario positivo" if z.imag > 0 else "eje imaginario negativo"
    if z.real > 0:
        return "primero" if z.imag > 0 else "cuarto"
    return "segundo" if z.imag > 0 else "tercero"


def operar(clave: str, z1: complex, z2: complex, decimales: int = 6) -> list[tuple[str, str]]:
    """Operación entre dos complejos, con el resultado en todas sus formas."""
    operaciones = {
        "sumar": ("z₁ + z₂", lambda: z1 + z2),
        "restar": ("z₁ − z₂", lambda: z1 - z2),
        "multiplicar": ("z₁ · z₂", lambda: z1 * z2),
        "dividir": ("z₁ / z₂", lambda: _dividir(z1, z2)),
    }
    if clave not in operaciones:
        raise ErrorComplejo(f"Operación desconocida: {clave!r}")

    etiqueta, funcion = operaciones[clave]
    resultado = funcion()

    filas = [
        ("z₁", binomica(z1, decimales) + "   =   " + polar(z1, decimales)),
        ("z₂", binomica(z2, decimales) + "   =   " + polar(z2, decimales)),
        ("", ""),
        (etiqueta, binomica(resultado, decimales)),
        ("En forma polar", polar(resultado, decimales)),
        ("Módulo", formatear(abs(resultado), decimales)),
        ("Argumento", formatear(math.degrees(cmath.phase(resultado)), decimales) + "°"),
    ]

    # En producto y cociente conviene recordar la regla de módulos y argumentos.
    if clave == "multiplicar":
        filas.append(("Regla", "los módulos se multiplican y los argumentos se suman"))
    elif clave == "dividir":
        filas.append(("Regla", "los módulos se dividen y los argumentos se restan"))
    return filas


def _dividir(z1: complex, z2: complex) -> complex:
    if z2 == 0:
        raise ErrorComplejo("No se puede dividir entre cero")
    return z1 / z2


def potencia(z: complex, exponente: float, decimales: int = 6) -> list[tuple[str, str]]:
    """Potencia mediante la fórmula de De Moivre."""
    if abs(exponente) > 1000:
        raise ErrorComplejo("El exponente debe estar entre −1000 y 1000")
    if z == 0 and exponente <= 0:
        raise ErrorComplejo("0 elevado a un exponente no positivo no está definido")

    modulo, angulo = cmath.polar(z)
    resultado = z ** exponente

    return [
        ("z", binomica(z, decimales) + "   =   " + polar(z, decimales)),
        ("Exponente n", formatear(exponente, decimales)),
        ("", ""),
        ("De Moivre", "zⁿ = |z|ⁿ · (cos nθ + i·sen nθ)"),
        ("|z|ⁿ", formatear(modulo ** exponente, decimales)),
        ("n·θ", formatear(math.degrees(angulo * exponente), decimales) + "°"),
        ("", ""),
        ("Resultado", binomica(resultado, decimales)),
        ("En forma polar", polar(resultado, decimales)),
    ]


def raices(z: complex, indice: int, decimales: int = 6) -> list[tuple[str, str]]:
    """Las ``indice`` raíces n-ésimas de un complejo.

    Un complejo no nulo tiene exactamente n raíces n-ésimas, repartidas por
    igual sobre una circunferencia de radio |z|^(1/n).
    """
    if not 1 <= indice <= 60:
        raise ErrorComplejo("El índice debe estar entre 1 y 60")
    if z == 0:
        return [("Raíces", "todas las raíces de 0 son 0")]

    modulo, angulo = cmath.polar(z)
    radio = modulo ** (1 / indice)

    filas = [
        ("z", binomica(z, decimales) + "   =   " + polar(z, decimales)),
        ("Índice n", str(indice)),
        ("", ""),
        ("Módulo de las raíces", formatear(radio, decimales)),
        ("Separación angular", formatear(360 / indice, decimales) + "°"),
        ("", ""),
    ]

    for k in range(indice):
        angulo_k = (angulo + 2 * math.pi * k) / indice
        raiz = cmath.rect(radio, angulo_k)
        filas.append((
            f"Raíz w{_subindice(k)}",
            f"{binomica(raiz, decimales)}      ∠ {formatear(math.degrees(angulo_k), 4)}°",
        ))

    return filas


def lista_raices(z: complex, indice: int) -> list[complex]:
    """Las raíces n-ésimas como lista, para dibujarlas en el plano."""
    if z == 0 or not 1 <= indice <= 60:
        return []
    modulo, angulo = cmath.polar(z)
    radio = modulo ** (1 / indice)
    return [cmath.rect(radio, (angulo + 2 * math.pi * k) / indice) for k in range(indice)]


_SUBINDICES = "₀₁₂₃₄₅₆₇₈₉"


def _subindice(numero: int) -> str:
    return "".join(_SUBINDICES[int(d)] for d in str(numero))


#: (clave, título, cuántos operandos y parámetro extra)
OPERACIONES = [
    ("ficha", "Analizar un número", 1, None),
    ("sumar", "Suma  z₁ + z₂", 2, None),
    ("restar", "Resta  z₁ − z₂", 2, None),
    ("multiplicar", "Producto  z₁ · z₂", 2, None),
    ("dividir", "Cociente  z₁ / z₂", 2, None),
    ("potencia", "Potencia  zⁿ (De Moivre)", 1, "exponente"),
    ("raices", "Raíces n-ésimas", 1, "índice"),
]
