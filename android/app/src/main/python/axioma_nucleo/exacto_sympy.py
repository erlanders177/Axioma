"""La forma exacta con sympy, para el paso a paso.

El resultado exacto de la calculadora lo da :mod:`exacto`, sin sympy, que es
instantáneo. El paso a paso sí necesita sympy para las cuentas intermedias, y
estas piezas son las que usa para escribirlas igual que el resultado: «2√2»,
«(√5 + 1)/2», «3π/4».
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import sympy as sp
from sympy.parsing.sympy_parser import (
    auto_number,
    convert_xor,
    factorial_notation,
    implicit_multiplication,
    parse_expr,
    rationalize,
)

from .evaluador import ErrorExpresion, _preparar, evaluar
from .formato import formatear

__all__ = [
    "Resultado",
    "calcular",
    "a_texto",
    "a_arbol",
    "presentable",
]

#: Sin símbolos automáticos: un nombre desconocido es un error, no una incógnita.
_TRANSFORMACIONES = (auto_number, factorial_notation, implicit_multiplication,
                     convert_xor, rationalize)

#: Por encima de esto, el exacto deja de ser más legible que el decimal.
_MAXIMO_OPERACIONES = 30
_MAXIMO_CARACTERES = 90

_NOMBRE = re.compile(r"[A-Za-z_]\w*")


@dataclass(frozen=True)
class Resultado:
    """Lo que sale de una cuenta, en sus dos formas."""

    #: El valor en coma flotante, que es el que se guarda y se reutiliza.
    valor: float
    #: El decimal, ya formateado.
    decimal: str
    #: La forma exacta en una línea («2√2 + 1/3»), o None si no la hay.
    exacto: str | None
    #: La forma exacta como árbol, para dibujar fracciones de verdad.
    arbol: list | None
    #: La expresión exacta en sintaxis de sympy, para guardarla en una variable.
    simbolico: str | None

    @property
    def tiene_exacto(self) -> bool:
        """¿Tiene sentido la tecla S⇔D? Para un entero, las dos formas son iguales."""
        return self.exacto is not None and self.exacto != self.decimal


# --------------------------------------------------------------------------- #
# El diccionario de nombres
# --------------------------------------------------------------------------- #

def _angulo(modo: str):
    """Qué hay que multiplicar a un ángulo para pasarlo a radianes."""
    if modo == "DEG":
        return sp.pi / 180
    if modo == "GRAD":
        return sp.pi / 200
    return sp.Integer(1)


def _nombres(modo: str, entorno: dict | None) -> dict:
    """Todo lo que se puede nombrar en una expresión, en versión exacta."""
    a_rad = _angulo(modo)

    def directa(funcion):
        return lambda x: funcion(x * a_rad)

    def inversa(funcion):
        return lambda x: funcion(x) / a_rad

    def factorial(x):
        if x.is_integer and x > 10_000:
            raise ErrorExpresion("El factorial está limitado a 10000!")
        return sp.factorial(x)

    nombres = {
        "sin": directa(sp.sin), "cos": directa(sp.cos), "tan": directa(sp.tan),
        "asin": inversa(sp.asin), "acos": inversa(sp.acos), "atan": inversa(sp.atan),
        "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
        "asinh": sp.asinh, "acosh": sp.acosh, "atanh": sp.atanh,
        "sqrt": sp.sqrt,
        "cbrt": lambda x: sp.real_root(x, 3),
        "raiz": lambda x, n: sp.real_root(x, n),
        "exp": sp.exp,
        "ln": sp.log,
        "log": lambda x, base=10: sp.log(x, base),
        "log10": lambda x: sp.log(x, 10),
        "log2": lambda x: sp.log(x, 2),
        "abs": sp.Abs, "sign": sp.sign,
        "floor": sp.floor, "ceil": sp.ceiling,
        "factorial": factorial, "gamma": sp.gamma,
        "mod": sp.Mod,
        "gcd": sp.gcd, "lcm": sp.lcm,
        "min": sp.Min, "max": sp.Max,
        "hypot": lambda a, b: sp.sqrt(a ** 2 + b ** 2),
        "degrees": lambda x: x * 180 / sp.pi, "grados": lambda x: x * 180 / sp.pi,
        "radians": lambda x: x * sp.pi / 180, "radianes": lambda x: x * sp.pi / 180,
        "pi": sp.pi, "e": sp.E, "tau": 2 * sp.pi, "phi": sp.GoldenRatio,
        # Lo que construyen las transformaciones al leer los números.
        "Integer": sp.Integer, "Float": sp.Float, "Rational": sp.Rational,
    }
    for nombre, valor in (entorno or {}).items():
        nombres[nombre] = _a_exacto(valor)
    return nombres


def _a_exacto(valor):
    """Un valor guardado (variable, ans) en su forma exacta si la tiene.

    Un float que viene de una cuenta con π no se puede recuperar exacto sin
    adivinar, y adivinar es justo lo que no se quiere: se queda como float y el
    resultado que lo use saldrá en decimal, que es lo honrado.
    """
    if isinstance(valor, sp.Basic):
        return valor
    if isinstance(valor, str):
        return sp.sympify(valor, rational=True)
    if isinstance(valor, int) or (isinstance(valor, float) and valor.is_integer()
                                  and abs(valor) < 1e15):
        return sp.Integer(int(valor))
    if isinstance(valor, float):
        # 2.5 viene de escribir 2.5, y es 5/2. 3.3333333333333335 no es 10/3:
        # es un float que ya perdió la exactitud por el camino.
        fraccion = sp.Rational(repr(valor))
        if fraccion.q <= 10_000:
            return fraccion
        return sp.Float(valor)
    return sp.sympify(valor)


# --------------------------------------------------------------------------- #
# Calcular
# --------------------------------------------------------------------------- #

def _analizar(texto: str, modo: str, entorno: dict | None, evaluar_ya: bool = True):
    """Convierte el texto en una expresión exacta de sympy, sin salir del cercado."""
    preparado = _preparar(texto)

    if "__" in preparado or re.search(r"[A-Za-z_]\w*\s*\.\s*[A-Za-z_]", preparado):
        raise ErrorExpresion("La expresión contiene algo que no se puede calcular")

    nombres = _nombres(modo, entorno)
    for nombre in _NOMBRE.findall(preparado):
        if nombre not in nombres:
            raise ErrorExpresion(f"No se reconoce «{nombre}»")

    try:
        return parse_expr(preparado, local_dict=nombres, global_dict={},
                          transformations=_TRANSFORMACIONES, evaluate=evaluar_ya)
    except ErrorExpresion:
        raise
    except Exception as e:                                        # noqa: BLE001
        raise ErrorExpresion(f"No se entiende la expresión: {e}") from e


def presentable(expresion) -> bool:
    """¿Merece la pena enseñar esta forma exacta en vez del decimal?"""
    if not isinstance(expresion, sp.Basic) or not expresion.is_number:
        return False
    if expresion.has(sp.zoo, sp.oo, -sp.oo, sp.nan, sp.I):
        return False
    for nodo in sp.preorder_traversal(expresion):
        if isinstance(nodo, (sp.Add, sp.Mul)):
            continue
        if isinstance(nodo, sp.Pow):
            if not nodo.exp.is_Rational:
                return False
            continue
        if isinstance(nodo, sp.Float):
            return False
        if nodo.is_Rational or nodo in (sp.pi, sp.E, sp.GoldenRatio):
            continue
        if _exponencial(nodo) is not None:
            continue
        return False
    if sp.count_ops(expresion) > _MAXIMO_OPERACIONES:
        return False
    return len(a_texto(expresion)) <= _MAXIMO_CARACTERES


def _mas_legible(expresion):
    """Entre la forma que da sympy y la racionalizada, la más corta.

    Y si todos los términos de una suma comparten denominador, se juntan:
    «(1 + √5)/2» y no «√5/2 + 1/2», que es como lo escribiría nadie.
    """
    candidatas = [expresion]
    try:
        candidatas.append(sp.radsimp(expresion))
    except Exception:                                             # noqa: BLE001
        pass
    elegida = min(candidatas, key=lambda e: (sp.count_ops(e), len(sp.sstr(e))))

    if isinstance(elegida, sp.Add):
        denominadores = {sp.fraction(termino)[1] for termino in elegida.args}
        if len(denominadores) == 1 and denominadores != {1}:
            return sp.together(elegida)
    return elegida


def calcular(texto: str, modo: str = "DEG", entorno: dict | None = None,
             decimales: int = 6) -> Resultado:
    """Calcula en las dos formas. Los errores salen del evaluador de siempre."""
    # Primero el decimal: es el que da los errores con los mensajes de siempre,
    # y el que tiene la última palabra si las dos formas no coinciden.
    entorno_decimal = {n: v if isinstance(v, (int, float)) else float(sp.sympify(v))
                       for n, v in (entorno or {}).items()}
    valor = evaluar(texto, modo, entorno_decimal)
    decimal = formatear(valor, decimales)

    try:
        exacta = _mas_legible(_analizar(texto, modo, entorno))
    except Exception:                                             # noqa: BLE001
        return Resultado(valor, decimal, None, None, None)

    if not presentable(exacta):
        return Resultado(valor, decimal, None, None, None)

    try:
        aproximada = float(exacta.evalf(30))
    except (TypeError, ValueError):
        return Resultado(valor, decimal, None, None, None)
    if not math.isclose(aproximada, valor, rel_tol=1e-9, abs_tol=1e-12):
        return Resultado(valor, decimal, None, None, None)

    return Resultado(valor, decimal, a_texto(exacta), a_arbol(exacta), sp.sstr(exacta))


# --------------------------------------------------------------------------- #
# Escribirlo
# --------------------------------------------------------------------------- #

_SIMBOLOS = {sp.pi: "π", sp.E: "e", sp.GoldenRatio: "φ"}


def _terminos(suma) -> list:
    """Los términos de una suma en el orden en que se escriben en clase.

    Primero lo que lleva raíces o π, y el número suelto al final: «2√2 + 1/3»,
    «√2 − 1». sympy pone el número delante, y «−1 + √2» se lee peor.
    """
    terminos = suma.as_ordered_terms()
    sueltos = [t for t in terminos if t.is_Rational]
    resto = [t for t in terminos if not t.is_Rational]
    ordenados = resto + sueltos
    # Si el primero queda negativo y hay alguno positivo, que empiece éste.
    if ordenados[0].could_extract_minus_sign():
        for i, termino in enumerate(ordenados):
            if not termino.could_extract_minus_sign():
                ordenados.insert(0, ordenados.pop(i))
                break
    return ordenados


def _exponencial(expresion):
    """e elevado a un entero, que sympy guarda como exp(n) y no como potencia."""
    if isinstance(expresion, sp.exp) and expresion.args[0].is_Integer:
        return int(expresion.args[0])
    return None


def _es_atomico(expresion) -> bool:
    """¿Se puede escribir sin paréntesis alrededor?"""
    return (expresion.is_Atom and not (expresion.is_Rational and expresion.q != 1)
            and not (expresion.is_Number and expresion < 0))


def a_texto(expresion) -> str:
    """La forma exacta en una línea: «2√2 + 1/3», «√2/2», «3π/4»."""
    if expresion in _SIMBOLOS:
        return _SIMBOLOS[expresion]
    if (n := _exponencial(expresion)) is not None and n > 0:
        return "e" + _superindice(n)
    if expresion.is_Integer:
        return str(expresion).replace("-", "−")
    if expresion.is_Rational:
        signo = "−" if expresion < 0 else ""
        return f"{signo}{abs(expresion.p)}/{expresion.q}"

    if isinstance(expresion, sp.Add):
        terminos = _terminos(expresion)
        partes = [a_texto(terminos[0])]
        for termino in terminos[1:]:
            if termino.could_extract_minus_sign():
                partes.append(" − " + a_texto(-termino))
            else:
                partes.append(" + " + a_texto(termino))
        return "".join(partes)

    if expresion.could_extract_minus_sign():
        interior = a_texto(-expresion)
        return "−" + (f"({interior})" if isinstance(-expresion, sp.Add) else interior)

    numerador, denominador = sp.fraction(expresion)
    if denominador != 1:
        arriba = a_texto(numerador)
        abajo = a_texto(denominador)
        if isinstance(numerador, sp.Add):
            arriba = f"({arriba})"
        if not _es_atomico(denominador) and not _es_raiz(denominador):
            abajo = f"({abajo})"
        return f"{arriba}/{abajo}"

    if isinstance(expresion, sp.Mul):
        coeficiente, resto = expresion.as_coeff_Mul()
        factores = sp.Mul.make_args(resto)
        texto_resto = "·".join(_factor_texto(f) for f in factores)
        if coeficiente == 1:
            return texto_resto
        return a_texto(coeficiente) + texto_resto

    if isinstance(expresion, sp.Pow):
        return _factor_texto(expresion)
    return sp.sstr(expresion)


def _es_raiz(expresion) -> bool:
    return (isinstance(expresion, sp.Pow) and expresion.exp.is_Rational
            and expresion.exp.q > 1)


def _factor_texto(factor) -> str:
    if isinstance(factor, sp.Pow) and factor.exp.is_Rational:
        base, exponente = factor.base, factor.exp
        if exponente.q > 1:
            radicando = base ** exponente.p if exponente.p != 1 else base
            interior = a_texto(radicando)
            if not _es_atomico(radicando):
                interior = f"({interior})"
            indice = {2: "√", 3: "∛", 4: "∜"}.get(exponente.q)
            return (indice or f"{exponente.q}√") + interior
        base_texto = a_texto(base)
        if not _es_atomico(base):
            base_texto = f"({base_texto})"
        return base_texto + _superindice(int(exponente))
    if isinstance(factor, sp.Add):
        return f"({a_texto(factor)})"
    return a_texto(factor)


_SUPERINDICES = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def _superindice(numero: int) -> str:
    return str(numero).translate(_SUPERINDICES)


# --------------------------------------------------------------------------- #
# Dibujarlo
# --------------------------------------------------------------------------- #

def _texto(valor: str) -> dict:
    return {"t": "txt", "v": valor}


def a_arbol(expresion) -> list:
    """La forma exacta como árbol, para que cada interfaz la dibuje igual.

    Es el mismo formato que usa el editor de fracciones: una fila de nodos, y
    cada nodo es texto, una fracción (con su fila de arriba y la de abajo) o
    una raíz (con la fila de dentro).
    """
    return _fusionar(_arbol(expresion))


def _fusionar(fila: list) -> list:
    """Junta los trozos de texto seguidos en uno, que se dibuja mejor."""
    salida: list = []
    for nodo in fila:
        if nodo["t"] == "txt" and salida and salida[-1]["t"] == "txt":
            salida[-1] = _texto(salida[-1]["v"] + nodo["v"])
        else:
            salida.append(nodo)
    return salida


def _arbol(expresion) -> list:
    if expresion in _SIMBOLOS:
        return [_texto(_SIMBOLOS[expresion])]
    if (n := _exponencial(expresion)) is not None and n > 0:
        return [_texto("e" + _superindice(n))]
    if expresion.is_Integer:
        return [_texto(str(expresion).replace("-", "−"))]
    if expresion.is_Rational:
        fraccion = {"t": "frac", "n": [_texto(str(abs(expresion.p)))],
                    "d": [_texto(str(expresion.q))]}
        return ([_texto("−")] if expresion < 0 else []) + [fraccion]

    if isinstance(expresion, sp.Add):
        terminos = _terminos(expresion)
        fila = _arbol(terminos[0])
        for termino in terminos[1:]:
            if termino.could_extract_minus_sign():
                fila += [_texto(" − ")] + _arbol(-termino)
            else:
                fila += [_texto(" + ")] + _arbol(termino)
        return fila

    if expresion.could_extract_minus_sign():
        interior = _arbol(-expresion)
        if isinstance(-expresion, sp.Add):
            interior = [_texto("(")] + interior + [_texto(")")]
        return [_texto("−")] + interior

    numerador, denominador = sp.fraction(expresion)
    if denominador != 1:
        return [{"t": "frac", "n": _fusionar(_arbol(numerador)),
                 "d": _fusionar(_arbol(denominador))}]

    if isinstance(expresion, sp.Mul):
        coeficiente, resto = expresion.as_coeff_Mul()
        fila = [] if coeficiente == 1 else _arbol(coeficiente)
        for i, factor in enumerate(sp.Mul.make_args(resto)):
            if i:
                fila.append(_texto("·"))
            fila += _arbol_factor(factor)
        return fila

    if isinstance(expresion, sp.Pow):
        return _arbol_factor(expresion)
    return [_texto(sp.sstr(expresion))]


def _arbol_factor(factor) -> list:
    if isinstance(factor, sp.Pow) and factor.exp.is_Rational:
        base, exponente = factor.base, factor.exp
        if exponente.q > 1:
            radicando = base ** exponente.p if exponente.p != 1 else base
            nodo = {"t": "raiz", "r": _fusionar(_arbol(radicando))}
            if exponente.q != 2:
                nodo["i"] = str(exponente.q)
            return [nodo]
        interior = _arbol(base)
        if not _es_atomico(base):
            interior = [_texto("(")] + interior + [_texto(")")]
        return interior + [_texto(_superindice(int(exponente)))]
    if isinstance(factor, sp.Add):
        return [_texto("(")] + _arbol(factor) + [_texto(")")]
    return _arbol(factor)
