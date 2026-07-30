"""Base común para todo lo que trabaja con expresiones simbólicas (sympy).

Los módulos de ecuaciones, sistemas, cálculo y el graficador compartían la misma
configuración del analizador y las mismas comprobaciones. Aquí están una sola
vez, con dos objetivos:

* aceptar la notación que la gente escribe de verdad (``2x^2`` en vez de
  ``2*x**2``);
* no dejar que ``parse_expr`` reciba texto sin filtrar. sympy evalúa el código
  que se le pasa, así que se rechazan de antemano los nombres que no son
  matemáticos (``__import__``, ``open``, atributos con punto…).
"""

from __future__ import annotations

import re

import sympy as sp
from sympy.parsing.sympy_parser import (
    convert_xor, implicit_multiplication_application, parse_expr,
    standard_transformations,
)

__all__ = [
    "ErrorSimbolico",
    "TRANSFORMACIONES",
    "analizar",
    "analizar_igualdad",
    "incognitas",
    "a_funcion",
    "texto",
    "aproximar",
    "FUNCIONES_CONOCIDAS",
]

TRANSFORMACIONES = standard_transformations + (
    implicit_multiplication_application,  # 2x  ->  2*x
    convert_xor,                          # x^2 ->  x**2
)


class ErrorSimbolico(ValueError):
    """La expresión no se puede interpretar."""


#: Funciones que se aceptan dentro de una expresión.
FUNCIONES_CONOCIDAS = frozenset({
    "sin", "cos", "tan", "cot", "sec", "csc",
    "asin", "acos", "atan", "acot", "asec", "acsc", "atan2",
    "sinh", "cosh", "tanh", "coth", "asinh", "acosh", "atanh",
    "exp", "log", "ln", "sqrt", "cbrt", "root", "Abs", "abs", "sign",
    "floor", "ceiling", "ceil", "factorial", "gamma", "binomial",
    "Max", "Min", "max", "min", "re", "im", "arg", "conjugate",
    "Sum", "Product", "Piecewise", "Heaviside", "erf",
})

#: Nombres reservados que sympy entiende como constantes.
CONSTANTES_CONOCIDAS = frozenset({"pi", "E", "e", "I", "oo", "zoo", "nan", "phi", "tau"})

# Cualquier cosa que parezca acceso a atributos, subrayados dobles o llamadas a
# funciones que no estén en la lista blanca se rechaza antes de llegar a sympy.
_PROHIBIDO = re.compile(r"__|\bimport\b|\bopen\b|\beval\b|\bexec\b|\blambda\b|;|\bclass\b|\bdef\b")
_ATRIBUTO = re.compile(r"[A-Za-z_]\w*\s*\.\s*[A-Za-z_]")
_LLAMADA = re.compile(r"([A-Za-z_]\w*)\s*\(")

_LONGITUD_MAXIMA = 500


def _validar_texto(expresion: str) -> str:
    limpio = expresion.strip()
    if not limpio:
        raise ErrorSimbolico("Introduzca una expresión")
    if len(limpio) > _LONGITUD_MAXIMA:
        raise ErrorSimbolico(
            f"La expresión es demasiado larga (máximo {_LONGITUD_MAXIMA} caracteres)"
        )
    if _PROHIBIDO.search(limpio) or _ATRIBUTO.search(limpio):
        raise ErrorSimbolico("La expresión contiene elementos no permitidos")

    for nombre in _LLAMADA.findall(limpio):
        if nombre not in FUNCIONES_CONOCIDAS:
            raise ErrorSimbolico(
                f"Función desconocida: «{nombre}». "
                f"Consulte el manual para ver las funciones disponibles."
            )
    return limpio


def analizar(expresion: str) -> sp.Expr:
    """Convierte texto en una expresión de sympy.

    >>> analizar("2x^2 - 4")
    2*x**2 - 4
    """
    limpio = _validar_texto(expresion)
    try:
        resultado = parse_expr(limpio, transformations=TRANSFORMACIONES, evaluate=True)
    except (SyntaxError, TypeError, ValueError, AttributeError, RecursionError) as e:
        raise ErrorSimbolico(f"No se entiende la expresión: {e}") from e

    if not isinstance(resultado, sp.Basic):
        raise ErrorSimbolico("La expresión no es matemática")
    return resultado


def analizar_igualdad(texto_ecuacion: str, *, igualar_a_cero: bool = True) -> tuple[sp.Expr, sp.Expr]:
    """Separa «izquierda = derecha». Si no hay «=», se supone «= 0»."""
    limpio = texto_ecuacion.strip()
    if limpio.count("=") > 1:
        raise ErrorSimbolico("La expresión sólo puede tener un signo «=»")

    izquierda, signo, derecha = limpio.partition("=")
    if not signo:
        derecha = "0" if igualar_a_cero else ""
    if not derecha.strip():
        derecha = "0"
    return analizar(izquierda), analizar(derecha)


def incognitas(*expresiones: sp.Expr) -> list[sp.Symbol]:
    """Símbolos libres de las expresiones, ordenados por nombre.

    Se ordenan poniendo primero las letras habituales (x, y, z, t) para que la
    variable «natural» de una función quede la primera.
    """
    simbolos: set[sp.Symbol] = set()
    for expresion in expresiones:
        simbolos |= expresion.free_symbols

    preferidas = ["x", "y", "z", "t", "u", "v", "w", "n", "k"]

    def clave(simbolo: sp.Symbol) -> tuple[int, str]:
        nombre = simbolo.name
        return (preferidas.index(nombre) if nombre in preferidas else len(preferidas), nombre)

    return sorted(simbolos, key=clave)


def variable_principal(expresion: sp.Expr, preferida: str = "") -> sp.Symbol:
    """La variable respecto a la que tiene sentido derivar, integrar o graficar."""
    libres = incognitas(expresion)
    if preferida:
        for simbolo in libres:
            if simbolo.name == preferida:
                return simbolo
        return sp.Symbol(preferida)
    if not libres:
        return sp.Symbol("x")
    return libres[0]


def a_funcion(expresion: sp.Expr, variable: sp.Symbol):
    """Compila la expresión a una función de numpy para poder representarla."""
    try:
        return sp.lambdify(variable, expresion, ["numpy"])
    except Exception as e:  # sympy lanza tipos muy variados
        raise ErrorSimbolico(f"Esta expresión no se puede representar: {e}") from e


def texto(expresion) -> str:
    """Representación legible de una expresión."""
    try:
        return sp.sstr(expresion)
    except Exception:
        return str(expresion)


def aproximar(valor, decimales: int = 6) -> str:
    """Valor numérico de una expresión, o su forma simbólica si no es numérica."""
    try:
        numero = sp.N(valor, max(2, decimales))
    except (TypeError, ValueError):
        return texto(valor)
    return texto(numero)


def es_real(valor) -> bool:
    """True si el valor es un número real (o casi, salvo ruido numérico)."""
    try:
        complejo = complex(sp.N(valor))
    except (TypeError, ValueError):
        return bool(getattr(valor, "is_real", False))
    return abs(complejo.imag) < 1e-12
