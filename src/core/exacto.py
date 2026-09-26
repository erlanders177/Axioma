"""Resultados exactos: 2√2 en lugar de 2.828427, 3/4 en lugar de 0.75.

Es lo que hacen las calculadoras escolares en modo matemático, y lo que pide un
ejercicio de clase: «simplifique √72» no se contesta con 8.485281.

Por qué sin sympy
-----------------
sympy lo sabe hacer, pero cuesta cargarlo: en el navegador, entre 5 y 25
segundos cada vez que se abre la aplicación, con la pantalla congelada. Y lo que
enseña una calculadora escolar cabe en una familia pequeña de números: sumas de
términos como ``c · √n · πᵏ · eʲ``, con ``c`` una fracción y raíces cuadradas o
cúbicas. Con :class:`fractions.Fraction` y un poco de álgebra eso se hace al
instante y en las tres versiones. sympy queda para el paso a paso, las
ecuaciones y el cálculo, que sí lo necesitan.

Cómo se decide
--------------
La expresión se calcula **dos veces**: aquí, en exacto, y con el evaluador de
siempre, en coma flotante. El resultado exacto sólo se enseña si:

* la cuenta cabe en esa familia de números (``sin(1°)`` o ``ln 3`` no caben, y
  en exacto no le sirven a nadie);
* no es enorme de escribir;
* **y da lo mismo que el decimal**. Si no coinciden, se enseña el decimal. Un
  resultado exacto equivocado sería peor que no tenerlo.

Los errores (dividir entre cero, la raíz de un negativo…) siguen saliendo del
evaluador de siempre, con sus mensajes de siempre.
"""

from __future__ import annotations

import ast
import math
import re
from dataclasses import dataclass
from fractions import Fraction

from .evaluador import ErrorExpresion, _preparar, evaluar
from .formato import formatear

__all__ = ["Resultado", "calcular"]


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
    #: La forma exacta en sintaxis de Python («1/3 + 2*sqrt(2)»), para
    #: guardarla en Ans y seguir calculando sin perder la exactitud.
    simbolico: str | None

    @property
    def tiene_exacto(self) -> bool:
        """¿Tiene sentido la tecla S⇔D? Para un entero, las dos formas son iguales."""
        return self.exacto is not None and self.exacto != self.decimal


class _SinExacto(Exception):
    """La cuenta se sale de lo que se sabe escribir exacto: queda el decimal."""


# Límites. Por encima, el exacto deja de ser más legible que el decimal, o la
# cuenta se haría larga sin necesidad.
_MAXIMO_TERMINOS = 6
_MAXIMO_ENTERO = 10 ** 40
_MAXIMO_EXPONENTE = 512
_MAXIMO_FACTORIZABLE = 10 ** 10
_MAXIMO_CARACTERES = 90
#: En pantalla, fracciones de números razonables: 1/100000000000000000000 no
#: le dice nada a nadie que no diga ya 1e-20.
_MAXIMO_NUMERADOR = 10 ** 30
_MAXIMO_DENOMINADOR = 10 ** 12


# --------------------------------------------------------------------------- #
# Los números
# --------------------------------------------------------------------------- #

#: Un término es un coeficiente racional por unos factores irracionales. La
#: clave de esos factores es (raíces, potencia de π, potencia de e), donde
#: raíces es una tupla ordenada de (primo, exponente) con el exponente entre 0 y
#: 1: √12 se guarda como 2·3^(1/2). Así cada número tiene una sola forma, y dos
#: términos con la misma clave se suman sin más.
_UNO = ((), 0, 0)


def _normalizar(coeficiente: Fraction, raices: dict, pi, e) -> tuple:
    """Un término en su forma canónica: lo entero de cada raíz, fuera."""
    c = Fraction(coeficiente)
    limpias = []
    for primo, exponente in raices.items():
        entero = math.floor(exponente)
        resto = exponente - entero
        if entero:
            c *= Fraction(primo) ** entero
        if resto:
            limpias.append((primo, resto))
    if abs(pi) > 12 or abs(e) > 60:
        raise _SinExacto
    return c, (tuple(sorted(limpias)), int(pi), int(e))


def _factorizar(n: int) -> dict:
    """Los primos de n con sus exponentes: 72 → {2: 3, 3: 2}."""
    if n > _MAXIMO_FACTORIZABLE:
        raise _SinExacto
    factores: dict = {}
    for primo in (2, 3):
        while n % primo == 0:
            factores[primo] = factores.get(primo, 0) + 1
            n //= primo
    divisor = 5
    while divisor * divisor <= n:
        for primo in (divisor, divisor + 2):
            while n % primo == 0:
                factores[primo] = factores.get(primo, 0) + 1
                n //= primo
        divisor += 6
    if n > 1:
        factores[n] = factores.get(n, 0) + 1
    return factores


class _Numero:
    """Una suma de términos exactos."""

    __slots__ = ("terminos",)

    def __init__(self, terminos: dict | None = None) -> None:
        self.terminos = {k: c for k, c in (terminos or {}).items() if c}
        if len(self.terminos) > _MAXIMO_TERMINOS:
            raise _SinExacto
        for c in self.terminos.values():
            if abs(c.numerator) > _MAXIMO_ENTERO or c.denominator > _MAXIMO_ENTERO:
                raise _SinExacto

    @classmethod
    def racional(cls, valor) -> _Numero:
        return cls({_UNO: Fraction(valor)})

    @classmethod
    def termino(cls, coeficiente, raices: dict, pi: int = 0, e: int = 0) -> _Numero:
        c, clave = _normalizar(Fraction(coeficiente), raices, pi, e)
        return cls({clave: c})

    # ------------------------------------------------------------ preguntas -- #

    def es_cero(self) -> bool:
        return not self.terminos

    def es_racional(self) -> bool:
        return all(clave == _UNO for clave in self.terminos)

    def como_racional(self) -> Fraction:
        if not self.es_racional():
            raise _SinExacto
        return self.terminos.get(_UNO, Fraction(0))

    def __eq__(self, otro) -> bool:
        return isinstance(otro, _Numero) and self.terminos == otro.terminos

    def __hash__(self) -> int:                                   # pragma: no cover
        return hash(frozenset(self.terminos.items()))

    def __float__(self) -> float:
        total = 0.0
        try:
            for (raices, pi, e), c in self.terminos.items():
                valor = float(c)
                for primo, exponente in raices:
                    valor *= primo ** float(exponente)
                total += valor * math.pi ** pi * math.e ** e
        except OverflowError:
            raise _SinExacto from None
        return total

    # ---------------------------------------------------------- operaciones -- #

    def __add__(self, otro: _Numero) -> _Numero:
        suma = dict(self.terminos)
        for clave, c in otro.terminos.items():
            suma[clave] = suma.get(clave, 0) + c
        return _Numero(suma)

    def __neg__(self) -> _Numero:
        return _Numero({clave: -c for clave, c in self.terminos.items()})

    def __sub__(self, otro: _Numero) -> _Numero:
        return self + (-otro)

    def __mul__(self, otro: _Numero) -> _Numero:
        producto: dict = {}
        for (r1, pi1, e1), c1 in self.terminos.items():
            for (r2, pi2, e2), c2 in otro.terminos.items():
                raices = dict(r1)
                for primo, exponente in r2:
                    raices[primo] = raices.get(primo, 0) + exponente
                c, clave = _normalizar(c1 * c2, raices, pi1 + pi2, e1 + e2)
                producto[clave] = producto.get(clave, 0) + c
        return _Numero(producto)

    def inverso(self) -> _Numero:
        """1/x. Con dos términos, por el conjugado: 1/(1 + √2) = √2 − 1."""
        if len(self.terminos) == 1:
            ((raices, pi, e), c), = self.terminos.items()
            return _Numero.termino(1 / c, {p: -x for p, x in raices}, -pi, -e)
        if len(self.terminos) == 2:
            a, b = (_Numero({clave: c}) for clave, c in self.terminos.items())
            denominador = a * a - b * b
            if len(denominador.terminos) == 1:
                return (a - b) * denominador.inverso()
        raise _SinExacto

    def __truediv__(self, otro: _Numero) -> _Numero:
        return self * otro.inverso()

    def potencia(self, exponente: Fraction) -> _Numero:
        if exponente.denominator == 1:
            n = exponente.numerator
            if abs(n) > _MAXIMO_EXPONENTE:
                raise _SinExacto
            base = self.inverso() if n < 0 else self
            n = abs(n)
            resultado = _Numero.racional(1)
            while n:
                if n & 1:
                    resultado = resultado * base
                n >>= 1
                if n:
                    base = base * base
            return resultado

        # Una raíz. Sólo de un término: √(3 + 2√2) = 1 + √2, pero eso ya es
        # otra liga.
        if self.es_cero() and exponente > 0:
            return self
        if len(self.terminos) != 1 or exponente.denominator > 12:
            raise _SinExacto
        ((raices, pi, e), c), = self.terminos.items()
        nuevo_pi, nuevo_e = pi * exponente, e * exponente
        if nuevo_pi.denominator != 1 or nuevo_e.denominator != 1:
            raise _SinExacto
        signo = 1
        if c < 0:
            if exponente.denominator % 2 == 0:
                raise _SinExacto                  # raíz par de un negativo
            signo = -1 if exponente.numerator % 2 else 1
            c = -c
        nuevas = {primo: x * exponente for primo, x in raices}
        for parte, sentido in ((c.numerator, 1), (c.denominator, -1)):
            for primo, veces in _factorizar(parte).items():
                nuevas[primo] = nuevas.get(primo, 0) + sentido * veces * exponente
        return _Numero.termino(signo, nuevas, nuevo_pi, nuevo_e)


def _raiz(numero: _Numero, indice: int) -> _Numero:
    return numero.potencia(Fraction(1, indice))


_PI = _Numero.termino(1, {}, 1, 0)
_E = _Numero.termino(1, {}, 0, 1)


# --------------------------------------------------------------------------- #
# Trigonometría: los valores notables
# --------------------------------------------------------------------------- #

def _r(n) -> _Numero:
    return _Numero.racional(n)


def _tabla_de_senos() -> dict:
    """sin de los ángulos del primer cuadrante que tienen forma exacta sencilla."""
    raiz2, raiz3, raiz5, raiz6 = (_raiz(_r(n), 2) for n in (2, 3, 5, 6))
    cuarto = _r(Fraction(1, 4))
    return {
        0: _r(0),
        15: (raiz6 - raiz2) * cuarto,
        18: (raiz5 - _r(1)) * cuarto,
        30: _r(Fraction(1, 2)),
        45: raiz2 * _r(Fraction(1, 2)),
        54: (raiz5 + _r(1)) * cuarto,
        60: raiz3 * _r(Fraction(1, 2)),
        75: (raiz6 + raiz2) * cuarto,
        90: _r(1),
    }


_SENOS = _tabla_de_senos()


def _seno_en_grados(grados: Fraction) -> _Numero:
    if grados.denominator != 1:
        raise _SinExacto
    angulo = grados.numerator % 360
    signo = 1
    if angulo >= 180:
        angulo -= 180
        signo = -1
    if angulo > 90:
        angulo = 180 - angulo
    if angulo not in _SENOS:
        raise _SinExacto
    return _SENOS[angulo] if signo == 1 else -_SENOS[angulo]


def _coseno_en_grados(grados: Fraction) -> _Numero:
    return _seno_en_grados(90 - grados)


# --------------------------------------------------------------------------- #
# Calcular
# --------------------------------------------------------------------------- #

class _Cuenta(ast.NodeVisitor):
    """Recorre la expresión (ya validada por el evaluador) en exacto."""

    def __init__(self, modo: str, entorno: dict | None) -> None:
        self.modo = modo
        self.entorno = entorno or {}

    def generic_visit(self, nodo):
        raise _SinExacto

    def visit_Expression(self, nodo):
        return self.visit(nodo.body)

    def visit_Constant(self, nodo):
        valor = nodo.value
        if isinstance(valor, bool) or not isinstance(valor, (int, float)):
            raise _SinExacto
        if isinstance(valor, int):
            return _r(valor)
        if not math.isfinite(valor):
            raise _SinExacto
        # repr y no el float tal cual: 0.1 es 1/10, no 3602879701896397/2^55.
        return _r(Fraction(repr(valor)))

    def visit_Name(self, nodo):
        nombre = nodo.id
        if nombre in self.entorno:
            return _desde_entorno(self.entorno[nombre])
        constantes = {
            "pi": lambda: _PI,
            "e": lambda: _E,
            "tau": lambda: _r(2) * _PI,
            "phi": lambda: (_raiz(_r(5), 2) + _r(1)) * _r(Fraction(1, 2)),
        }
        if nombre in constantes:
            return constantes[nombre]()
        raise _SinExacto

    def visit_UnaryOp(self, nodo):
        valor = self.visit(nodo.operand)
        if isinstance(nodo.op, ast.USub):
            return -valor
        if isinstance(nodo.op, ast.UAdd):
            return valor
        raise _SinExacto

    def visit_BinOp(self, nodo):
        izquierda = self.visit(nodo.left)
        derecha = self.visit(nodo.right)
        operador = nodo.op
        if isinstance(operador, ast.Add):
            return izquierda + derecha
        if isinstance(operador, ast.Sub):
            return izquierda - derecha
        if isinstance(operador, ast.Mult):
            return izquierda * derecha
        if isinstance(operador, ast.Div):
            return izquierda / derecha
        if isinstance(operador, ast.Pow):
            return izquierda.potencia(derecha.como_racional())
        if isinstance(operador, (ast.Mod, ast.FloorDiv)):
            a, b = izquierda.como_racional(), derecha.como_racional()
            if not b:
                raise _SinExacto
            cociente = a // b
            return _r(cociente) if isinstance(operador, ast.FloorDiv) else _r(a - b * cociente)
        raise _SinExacto

    def visit_Call(self, nodo):
        if not isinstance(nodo.func, ast.Name) or nodo.keywords:
            raise _SinExacto
        nombre = nodo.func.id
        argumentos = [self.visit(a) for a in nodo.args]
        funcion = getattr(self, "_f_" + nombre, None)
        if funcion is None:
            raise _SinExacto
        try:
            return funcion(*argumentos)
        except TypeError:
            raise _SinExacto from None

    # -------------------------------------------------------------- ángulos -- #

    def _a_grados(self, x: _Numero) -> Fraction:
        if self.modo == "DEG":
            return x.como_racional()
        if self.modo == "GRAD":
            return x.como_racional() * Fraction(9, 10)
        if x.es_cero():
            return Fraction(0)
        # En radianes, sólo los múltiplos racionales de π: π/4, 2π/3…
        if len(x.terminos) == 1:
            (clave, c), = x.terminos.items()
            if clave == ((), 1, 0):
                return c * 180
        raise _SinExacto

    def _desde_grados(self, grados: Fraction) -> _Numero:
        if self.modo == "DEG":
            return _r(grados)
        if self.modo == "GRAD":
            return _r(grados * Fraction(10, 9))
        return _r(grados / 180) * _PI

    def _angulo_de(self, funcion, valor: _Numero, desde: int, hasta: int) -> _Numero:
        """El ángulo notable entre `desde` y `hasta` grados cuya función da `valor`."""
        for grados in range(desde, hasta + 1, 3):
            try:
                if funcion(Fraction(grados)) == valor:
                    return self._desde_grados(Fraction(grados))
            except _SinExacto:
                continue
        raise _SinExacto

    def _f_sin(self, x):
        return _seno_en_grados(self._a_grados(x))

    def _f_cos(self, x):
        return _coseno_en_grados(self._a_grados(x))

    def _f_tan(self, x):
        grados = self._a_grados(x)
        return _seno_en_grados(grados) / _coseno_en_grados(grados)

    def _f_sec(self, x):
        return _coseno_en_grados(self._a_grados(x)).inverso()

    def _f_csc(self, x):
        return _seno_en_grados(self._a_grados(x)).inverso()

    def _f_cot(self, x):
        grados = self._a_grados(x)
        return _coseno_en_grados(grados) / _seno_en_grados(grados)

    def _f_asin(self, x):
        return self._angulo_de(_seno_en_grados, x, -90, 90)

    def _f_acos(self, x):
        return self._angulo_de(_coseno_en_grados, x, 0, 180)

    def _f_atan(self, x):
        def tangente(grados):
            return _seno_en_grados(grados) / _coseno_en_grados(grados)
        return self._angulo_de(tangente, x, -87, 87)

    # ---------------------------------------------------- raíces y potencias -- #

    def _f_sqrt(self, x):
        return _raiz(x, 2)

    def _f_cbrt(self, x):
        return _raiz(x, 3)

    def _f_raiz(self, x, n):
        indice = n.como_racional()
        if indice.denominator != 1 or indice < 2:
            raise _SinExacto
        return _raiz(x, int(indice))

    def _f_exp(self, x):
        return _E.potencia(x.como_racional())

    def _f_ln(self, x):
        if x == _r(1):
            return _r(0)
        if len(x.terminos) == 1:
            ((raices, pi, e), c), = x.terminos.items()
            if not raices and not pi and c == 1:
                return _r(e)
        raise _SinExacto

    def _f_log(self, x, base=None):
        base = _r(10) if base is None else base
        if base == _E:
            return self._f_ln(x)
        return _r(_logaritmo_exacto(x.como_racional(), base.como_racional()))

    def _f_log10(self, x):
        return self._f_log(x)

    def _f_log2(self, x):
        return self._f_log(x, _r(2))

    # --------------------------------------------------------------- varios -- #

    def _f_abs(self, x):
        return -x if float(x) < 0 else x

    def _f_sign(self, x):
        if x.es_cero():
            return _r(0)
        return _r(1 if float(x) > 0 else -1)

    def _entero_de(self, x, redondeo) -> _Numero:
        if x.es_racional():
            return _r(redondeo(x.como_racional()))
        valor = float(x)
        if abs(valor - round(valor)) < 1e-9:     # demasiado justo para fiarse
            raise _SinExacto
        return _r(redondeo(valor))

    def _f_floor(self, x):
        return self._entero_de(x, math.floor)

    def _f_ceil(self, x):
        return self._entero_de(x, math.ceil)

    def _f_trunc(self, x):
        return self._entero_de(x, math.trunc)

    def _f_factorial(self, x):
        n = x.como_racional()
        if n.denominator != 1 or n < 0 or n > 200:
            raise _SinExacto
        return _r(math.factorial(int(n)))

    def _f_gamma(self, x):
        n = x.como_racional()
        if n.denominator != 1 or n < 1 or n > 201:
            raise _SinExacto
        return _r(math.factorial(int(n) - 1))

    def _f_mod(self, a, b):
        a, b = a.como_racional(), b.como_racional()
        if not b:
            raise _SinExacto
        return _r(a - b * math.floor(a / b))

    def _f_hypot(self, a, b):
        return _raiz(a * a + b * b, 2)

    def _f_gcd(self, *numeros):
        return _r(math.gcd(*(_entero(n) for n in numeros)))

    def _f_lcm(self, *numeros):
        return _r(math.lcm(*(_entero(n) for n in numeros)))

    def _f_min(self, *numeros):
        return min(numeros, key=float)

    def _f_max(self, *numeros):
        return max(numeros, key=float)

    def _f_degrees(self, x):
        return x * _r(180) * _PI.inverso()

    def _f_radians(self, x):
        return x * _PI * _r(Fraction(1, 180))

    _f_grados = _f_degrees
    _f_radianes = _f_radians


def _entero(numero: _Numero) -> int:
    valor = numero.como_racional()
    if valor.denominator != 1:
        raise _SinExacto
    return int(valor)


def _logaritmo_exacto(x: Fraction, base: Fraction) -> Fraction:
    """log_base(x) si es racional: log₂ 8 = 3, log₄ 2 = 1/2, log 0.01 = −2."""
    if x <= 0 or base <= 0 or base == 1:
        raise _SinExacto
    if x == 1:
        return Fraction(0)
    # base^(p/q) = x  ⇔  base^p = x^q. Se prueban exponentes pequeños.
    for q in range(1, 7):
        for p in range(1, 61):
            for signo in (1, -1):
                if base ** (signo * p) == x ** q:
                    return Fraction(signo * p, q)
    raise _SinExacto


def _desde_entorno(valor) -> _Numero:
    """Una variable o Ans, en exacto si se puede saber sin adivinar.

    Un float que viene de una cuenta con π no se puede recuperar exacto sin
    adivinar, y adivinar es justo lo que no se quiere: el resultado que lo use
    saldrá en decimal, que es lo honrado. Ans, en cambio, llega en texto
    exacto («2*sqrt(2)») y sigue siendo exacto.
    """
    if isinstance(valor, _Numero):
        return valor
    if isinstance(valor, str):
        return _Cuenta("RAD", None).visit(ast.parse(_preparar(valor), mode="eval"))
    if isinstance(valor, bool):
        raise _SinExacto
    if isinstance(valor, int):
        return _r(valor)
    if isinstance(valor, float):
        if not math.isfinite(valor):
            raise _SinExacto
        # 2.5 viene de escribir 2.5, y es 5/2. 3.3333333333333335 no es 10/3:
        # es un float que ya perdió la exactitud por el camino.
        fraccion = Fraction(repr(valor))
        if fraccion.denominator <= 10_000:
            return _r(fraccion)
    raise _SinExacto


def _a_decimal(valor) -> float:
    if isinstance(valor, (int, float)):
        return valor
    return float(_desde_entorno(valor))


def calcular(texto: str, modo: str = "DEG", entorno: dict | None = None,
             decimales: int = 6) -> Resultado:
    """Calcula en las dos formas. Los errores salen del evaluador de siempre."""
    # Primero el decimal: es el que da los errores con los mensajes de siempre,
    # y el que tiene la última palabra si las dos formas no coinciden.
    entorno_decimal = {}
    for nombre, v in (entorno or {}).items():
        try:
            entorno_decimal[nombre] = _a_decimal(v)
        except (_SinExacto, SyntaxError, ValueError, ErrorExpresion):
            continue
    valor = evaluar(texto, modo, entorno_decimal)
    decimal = formatear(valor, decimales)
    sin_exacto = Resultado(valor, decimal, None, None, None)

    try:
        arbol_python = ast.parse(_preparar(texto), mode="eval")
        exacto = _Cuenta(modo, entorno).visit(arbol_python)
        if not _presentable(exacto):
            return sin_exacto
        aproximado = float(exacto)
    except Exception:                                             # noqa: BLE001
        # Cualquier cosa que no salga en exacto sale en decimal, que ya está
        # calculado y comprobado. Nunca un error por intentar lo exacto.
        return sin_exacto

    if not math.isclose(aproximado, valor, rel_tol=1e-9, abs_tol=1e-12):
        return sin_exacto
    texto_exacto = _texto(exacto)
    if len(texto_exacto) > _MAXIMO_CARACTERES:
        return sin_exacto
    return Resultado(valor, decimal, texto_exacto, _arbol(exacto), _python(exacto))


# --------------------------------------------------------------------------- #
# Escribirlo
# --------------------------------------------------------------------------- #

def _presentable(numero: _Numero) -> bool:
    """Raíces cuadradas y cúbicas, y números que se puedan leer."""
    for (raices, _, _), c in numero.terminos.items():
        if abs(c.numerator) > _MAXIMO_NUMERADOR or c.denominator > _MAXIMO_DENOMINADOR:
            return False
        if any(exponente.denominator not in (2, 3) for _, exponente in raices):
            return False
    return len(numero.terminos) <= 4


_SUPERINDICES = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def _superindice(numero: int) -> str:
    return str(numero).translate(_SUPERINDICES)


def _nodo(valor: str) -> dict:
    return {"t": "txt", "v": valor}


def _fusionar(fila: list) -> list:
    """Junta los trozos de texto seguidos en uno, que se dibuja mejor."""
    salida: list = []
    for nodo in fila:
        if nodo["t"] == "txt" and salida and salida[-1]["t"] == "txt":
            salida[-1] = _nodo(salida[-1]["v"] + nodo["v"])
        else:
            salida.append(nodo)
    return salida


def _radicandos(raices: tuple) -> list:
    """[(índice, radicando)]: 2^(1/2)·3^(1/2) → √6; 2^(2/3) → ∛4."""
    por_indice: dict = {}
    for primo, exponente in raices:
        indice = exponente.denominator
        por_indice[indice] = por_indice.get(indice, 1) * primo ** exponente.numerator
    return sorted(por_indice.items())


def _potencia_simbolo(simbolo: str, exponente: int) -> str:
    return simbolo + (_superindice(exponente) if exponente != 1 else "")


def _partes(clave: tuple, c: Fraction):
    """Lo que va arriba y abajo de un término, como filas de nodos.

    Arriba: el coeficiente (si no es 1), π y e con exponente positivo y las
    raíces. Abajo: el denominador y lo que tenga exponente negativo.
    """
    raices, pi, e = clave
    arriba: list = []
    abajo: list = []
    trascendentes_arriba = ""
    trascendentes_abajo = ""
    if pi > 0:
        trascendentes_arriba += _potencia_simbolo("π", pi)
    elif pi < 0:
        trascendentes_abajo += _potencia_simbolo("π", -pi)
    if e > 0:
        trascendentes_arriba += _potencia_simbolo("e", e)
    elif e < 0:
        trascendentes_abajo += _potencia_simbolo("e", -e)

    numerador = abs(c.numerator)
    if numerador != 1 or (not raices and not trascendentes_arriba):
        arriba.append(_nodo(str(numerador)))
    if trascendentes_arriba:
        arriba.append(_nodo(trascendentes_arriba))
    for indice, radicando in _radicandos(raices):
        nodo = {"t": "raiz", "r": [_nodo(str(radicando))]}
        if indice != 2:
            nodo["i"] = str(indice)
        arriba.append(nodo)

    if c.denominator != 1:
        abajo.append(_nodo(str(c.denominator)))
    if trascendentes_abajo:
        abajo.append(_nodo(trascendentes_abajo))
    return _fusionar(arriba), _fusionar(abajo)


def _fila_a_texto(fila: list) -> str:
    partes = []
    for nodo in fila:
        if nodo["t"] == "txt":
            partes.append(nodo["v"])
        elif nodo["t"] == "raiz":
            signo = {"3": "∛"}.get(nodo.get("i", "2"), "√")
            partes.append(signo + _fila_a_texto(nodo["r"]))
        elif nodo["t"] == "frac":
            arriba, abajo = _fila_a_texto(nodo["n"]), _fila_a_texto(nodo["d"])
            if any(n["t"] == "txt" and (" + " in n["v"] or " − " in n["v"])
                   for n in nodo["n"]):
                arriba = f"({arriba})"
            if not (abajo.isdigit() or abajo in ("π", "e") or re.fullmatch(r"[√∛]\d+", abajo)):
                abajo = f"({abajo})"
            partes.append(f"{arriba}/{abajo}")
    return "".join(partes)


def _ordenados(numero: _Numero) -> list:
    """Los términos en el orden en que se escriben en clase.

    Primero lo que lleva raíces o π, y el número suelto al final: «2√2 + 1/3»,
    «√2 − 1». Y si el primero sale negativo y hay alguno positivo, empieza éste.
    """
    def orden(par):
        (raices, pi, e), _ = par
        return (not raices and not pi and not e, -pi, -e, _radicandos(raices))

    terminos = sorted(numero.terminos.items(), key=orden)
    if terminos and terminos[0][1] < 0:
        for i, (_, c) in enumerate(terminos):
            if c > 0:
                terminos.insert(0, terminos.pop(i))
                break
    return terminos


def _fila_de_termino(clave, c) -> list:
    arriba, abajo = _partes(clave, c)
    return arriba if not abajo else [{"t": "frac", "n": arriba, "d": abajo}]


def _arbol(numero: _Numero) -> list:
    if numero.es_cero():
        return [_nodo("0")]
    terminos = _ordenados(numero)

    # Si todos comparten denominador, se juntan: «(√5 + 1)/2», no «√5/2 + 1/2».
    denominadores = {c.denominator for _, c in terminos}
    sin_trascendentes_abajo = all(pi >= 0 and e >= 0 for (_, pi, e), _ in terminos)
    if len(terminos) > 1 and len(denominadores) == 1 and denominadores != {1} \
            and sin_trascendentes_abajo:
        comun = denominadores.pop()
        # Todo negativo: el signo fuera, «−(√5 + 1)/2» y no «(−√5 − 1)/2».
        signo = -1 if all(c < 0 for _, c in terminos) else 1
        arriba = _suma(_ordenados(_Numero({clave: c * comun * signo
                                           for clave, c in terminos})))
        fraccion = {"t": "frac", "n": _fusionar(arriba), "d": [_nodo(str(comun))]}
        return [_nodo("−"), fraccion] if signo < 0 else [fraccion]
    return _fusionar(_suma(terminos))


def _suma(terminos: list) -> list:
    fila: list = []
    for i, (clave, c) in enumerate(terminos):
        if i == 0:
            if c < 0:
                fila.append(_nodo("−"))
        else:
            fila.append(_nodo(" − " if c < 0 else " + "))
        fila += _fila_de_termino(clave, c)
    return fila


def _texto(numero: _Numero) -> str:
    """La forma exacta en una línea: «2√2 + 1/3», «√2/2», «3π/4»."""
    return _fila_a_texto(_arbol(numero))


def _python(numero: _Numero) -> str:
    """En sintaxis de Python, para guardarlo en Ans: «(1/3) + (2)*sqrt(2)»."""
    if numero.es_cero():
        return "0"
    partes = []
    for (raices, pi, e), c in numero.terminos.items():
        factores = [f"({c.numerator}/{c.denominator})"]
        for indice, radicando in _radicandos(raices):
            factores.append(f"sqrt({radicando})" if indice == 2 else f"cbrt({radicando})")
        if pi:
            factores.append(f"pi**({pi})")
        if e:
            factores.append(f"exp({e})")
        partes.append("*".join(factores))
    return " + ".join(partes)
