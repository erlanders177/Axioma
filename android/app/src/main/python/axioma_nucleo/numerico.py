"""Métodos numéricos: raíces, integración, interpolación y EDOs aproximadas.

Lo que se usa cuando no hay solución exacta. Todos los métodos devuelven la
**tabla de iteraciones**, no sólo el resultado: ver cómo converge (o cómo no lo
hace) es la mitad de lo que se estudia en la asignatura.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import sympy as sp

from .simbolico import a_funcion, analizar, variable_principal

__all__ = [
    "ErrorNumerico",
    "Iteracion",
    "biseccion",
    "newton_raphson",
    "secante",
    "trapecio",
    "simpson",
    "interpolar",
    "euler",
    "runge_kutta_4",
    "METODOS_RAICES",
    "METODOS_INTEGRACION",
    "METODOS_EDO",
]

MAX_ITERACIONES = 200
MAX_SUBINTERVALOS = 100_000


class ErrorNumerico(ValueError):
    """El método no se pudo aplicar con esos datos."""


@dataclass(frozen=True)
class Iteracion:
    """Una fila de la tabla de convergencia."""

    n: int
    valores: dict
    error: float | None = None


def _compilar(expresion_texto: str, variable_texto: str = "x"):
    """Devuelve (función evaluable, expresión sympy, símbolo)."""
    expresion = analizar(expresion_texto)
    variable = variable_principal(expresion, variable_texto)
    return a_funcion(expresion, variable), expresion, variable


def _evaluar(funcion, x: float) -> float:
    try:
        valor = float(funcion(x))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as e:
        raise ErrorNumerico(f"La función no se puede evaluar en x = {x:g} ({e})") from None
    if not math.isfinite(valor):
        raise ErrorNumerico(f"La función no está definida en x = {x:g}")
    return valor


# --------------------------------------------------------------------------- #
# Raíces
# --------------------------------------------------------------------------- #


def biseccion(expresion: str, a: float, b: float, tolerancia: float = 1e-10,
              max_iter: int = 100, variable: str = "x") -> tuple[float, list[Iteracion], str]:
    """Método de bisección en el intervalo [a, b].

    Exige que f(a) y f(b) tengan signos opuestos: por el teorema de Bolzano,
    entonces hay al menos una raíz dentro y el método converge siempre.
    """
    funcion, _, _ = _compilar(expresion, variable)
    if a >= b:
        raise ErrorNumerico("El extremo izquierdo debe ser menor que el derecho")

    fa, fb = _evaluar(funcion, a), _evaluar(funcion, b)
    if fa == 0:
        return a, [], "el extremo izquierdo ya es raíz"
    if fb == 0:
        return b, [], "el extremo derecho ya es raíz"
    if fa * fb > 0:
        raise ErrorNumerico(
            f"f({a:g}) y f({b:g}) tienen el mismo signo, así que no se garantiza "
            f"que haya una raíz en el intervalo. Pruebe con otro."
        )

    iteraciones: list[Iteracion] = []
    izquierda, derecha = a, b
    medio = (a + b) / 2

    for n in range(1, min(max_iter, MAX_ITERACIONES) + 1):
        medio = (izquierda + derecha) / 2
        fm = _evaluar(funcion, medio)
        error = (derecha - izquierda) / 2

        iteraciones.append(Iteracion(n, {
            "a": izquierda, "b": derecha, "c": medio, "f(c)": fm,
        }, error))

        if fm == 0 or error < tolerancia:
            return medio, iteraciones, f"convergió en {n} iteraciones"

        if _evaluar(funcion, izquierda) * fm < 0:
            derecha = medio
        else:
            izquierda = medio

    return medio, iteraciones, f"no alcanzó la tolerancia en {len(iteraciones)} iteraciones"


def newton_raphson(expresion: str, x0: float, tolerancia: float = 1e-12,
                   max_iter: int = 60,
                   variable: str = "x") -> tuple[float, list[Iteracion], str]:
    """Método de Newton-Raphson: xₙ₊₁ = xₙ − f(xₙ)/f′(xₙ).

    Converge muy rápido (cuadráticamente) cerca de la raíz, pero puede
    divergir si la derivada se anula o el punto de partida está lejos.
    """
    funcion, expr, var = _compilar(expresion, variable)
    derivada = a_funcion(sp.diff(expr, var), var)

    iteraciones: list[Iteracion] = []
    x = x0

    for n in range(1, min(max_iter, MAX_ITERACIONES) + 1):
        fx = _evaluar(funcion, x)
        dfx = _evaluar(derivada, x)

        if abs(dfx) < 1e-14:
            raise ErrorNumerico(
                f"La derivada se anula en x = {x:g}: el método no puede continuar "
                f"(la recta tangente es horizontal). Pruebe otro punto de partida."
            )

        siguiente = x - fx / dfx
        error = abs(siguiente - x)
        iteraciones.append(Iteracion(n, {
            "xₙ": x, "f(xₙ)": fx, "f'(xₙ)": dfx, "xₙ₊₁": siguiente,
        }, error))

        if not math.isfinite(siguiente):
            raise ErrorNumerico("El método diverge: pruebe otro punto de partida")

        x = siguiente
        if error < tolerancia:
            return x, iteraciones, f"convergió en {n} iteraciones"

    return x, iteraciones, f"no alcanzó la tolerancia en {len(iteraciones)} iteraciones"


def secante(expresion: str, x0: float, x1: float, tolerancia: float = 1e-12,
            max_iter: int = 60, variable: str = "x") -> tuple[float, list[Iteracion], str]:
    """Método de la secante: como Newton, pero sin necesitar la derivada."""
    funcion, _, _ = _compilar(expresion, variable)
    if x0 == x1:
        raise ErrorNumerico("Los dos puntos de partida deben ser distintos")

    iteraciones: list[Iteracion] = []
    anterior, actual = x0, x1
    f_anterior, f_actual = _evaluar(funcion, anterior), _evaluar(funcion, actual)

    for n in range(1, min(max_iter, MAX_ITERACIONES) + 1):
        denominador = f_actual - f_anterior
        if abs(denominador) < 1e-15:
            raise ErrorNumerico(
                "Los dos últimos valores de la función son casi iguales: la "
                "secante es horizontal y el método no puede continuar."
            )

        siguiente = actual - f_actual * (actual - anterior) / denominador
        error = abs(siguiente - actual)
        iteraciones.append(Iteracion(n, {
            "xₙ₋₁": anterior, "xₙ": actual, "f(xₙ)": f_actual, "xₙ₊₁": siguiente,
        }, error))

        if not math.isfinite(siguiente):
            raise ErrorNumerico("El método diverge: pruebe otros puntos de partida")

        anterior, f_anterior = actual, f_actual
        actual = siguiente
        f_actual = _evaluar(funcion, actual)

        if error < tolerancia:
            return actual, iteraciones, f"convergió en {n} iteraciones"

    return actual, iteraciones, f"no alcanzó la tolerancia en {len(iteraciones)} iteraciones"


# --------------------------------------------------------------------------- #
# Integración
# --------------------------------------------------------------------------- #


def _preparar_integracion(expresion: str, a: float, b: float, n: int, variable: str):
    if a >= b:
        raise ErrorNumerico("El límite inferior debe ser menor que el superior")
    if n < 1:
        raise ErrorNumerico("El número de subintervalos debe ser al menos 1")
    if n > MAX_SUBINTERVALOS:
        raise ErrorNumerico(f"Demasiados subintervalos (máximo {MAX_SUBINTERVALOS})")
    funcion, expr, var = _compilar(expresion, variable)
    return funcion, expr, var


def trapecio(expresion: str, a: float, b: float, n: int = 100,
             variable: str = "x") -> tuple[float, list[Iteracion], str]:
    """Regla del trapecio compuesta.

    Aproxima el área sustituyendo la curva por segmentos rectos.
    """
    funcion, expr, var = _preparar_integracion(expresion, a, b, n, variable)
    h = (b - a) / n

    total = (_evaluar(funcion, a) + _evaluar(funcion, b)) / 2
    puntos: list[Iteracion] = []
    for i in range(1, n):
        x = a + i * h
        y = _evaluar(funcion, x)
        total += y
        if len(puntos) < 50:  # la tabla no debe crecer sin límite
            puntos.append(Iteracion(i, {"xᵢ": x, "f(xᵢ)": y}))

    aproximado = total * h
    return aproximado, puntos, _comparar_con_exacta(expr, var, a, b, aproximado)


def simpson(expresion: str, a: float, b: float, n: int = 100,
            variable: str = "x") -> tuple[float, list[Iteracion], str]:
    """Regla de Simpson compuesta (parábolas). Necesita n par."""
    if n % 2:
        n += 1  # se ajusta en silencio: es un requisito del método, no un error
    funcion, expr, var = _preparar_integracion(expresion, a, b, n, variable)
    h = (b - a) / n

    total = _evaluar(funcion, a) + _evaluar(funcion, b)
    puntos: list[Iteracion] = []
    for i in range(1, n):
        x = a + i * h
        y = _evaluar(funcion, x)
        total += y * (4 if i % 2 else 2)
        if len(puntos) < 50:
            puntos.append(Iteracion(i, {"xᵢ": x, "f(xᵢ)": y,
                                        "peso": 4 if i % 2 else 2}))

    aproximado = total * h / 3
    return aproximado, puntos, _comparar_con_exacta(expr, var, a, b, aproximado)


def _comparar_con_exacta(expr: sp.Expr, var: sp.Symbol, a: float, b: float,
                         aproximado: float) -> str:
    """Compara con el valor exacto si sympy sabe calcularlo."""
    try:
        exacta = sp.integrate(expr, (var, a, b))
        if exacta.has(sp.Integral):
            return "sympy no encuentra la primitiva: no hay valor exacto con el que comparar"
        valor = float(sp.N(exacta))
    except Exception:
        return "no se pudo calcular el valor exacto para comparar"

    if not math.isfinite(valor):
        return "el valor exacto no es finito"
    error = abs(valor - aproximado)
    relativo = error / abs(valor) if valor else error
    return (f"valor exacto {valor:.12g} · error absoluto {error:.3e} · "
            f"error relativo {relativo:.3e}")


# --------------------------------------------------------------------------- #
# Interpolación
# --------------------------------------------------------------------------- #


def interpolar(puntos: list[tuple[float, float]],
               metodo: str = "lagrange") -> tuple[sp.Expr, list[Iteracion], str]:
    """Polinomio que pasa exactamente por todos los puntos dados."""
    if len(puntos) < 2:
        raise ErrorNumerico("Hacen falta al menos 2 puntos")
    if len(puntos) > 20:
        raise ErrorNumerico(
            "Más de 20 puntos: el polinomio oscilaría de forma salvaje entre "
            "ellos (fenómeno de Runge). Use el módulo de ajuste de curvas."
        )

    xs = [p[0] for p in puntos]
    if len(set(xs)) != len(xs):
        raise ErrorNumerico("Hay dos puntos con la misma x: no define una función")

    x = sp.Symbol("x")

    if metodo == "lagrange":
        polinomio = sp.Integer(0)
        detalles: list[Iteracion] = []
        for i, (xi, yi) in enumerate(puntos):
            base = sp.Integer(1)
            for j, (xj, _) in enumerate(puntos):
                if i != j:
                    base *= (x - sp.Rational(str(xj))) / (sp.Rational(str(xi)) - sp.Rational(str(xj)))
            polinomio += sp.Rational(str(yi)) * base
            detalles.append(Iteracion(i, {
                "xᵢ": xi, "yᵢ": yi, "Lᵢ(x)": sp.sstr(sp.expand(base)),
            }))
        nota = "polinomio de Lagrange: cada término vale 1 en su punto y 0 en los demás"
    else:  # diferencias divididas de Newton
        n = len(puntos)
        tabla = [[sp.Rational(str(p[1])) for p in puntos]]
        for nivel in range(1, n):
            fila = []
            for i in range(n - nivel):
                numerador = tabla[nivel - 1][i + 1] - tabla[nivel - 1][i]
                denominador = sp.Rational(str(xs[i + nivel])) - sp.Rational(str(xs[i]))
                fila.append(numerador / denominador)
            tabla.append(fila)

        polinomio = sp.Integer(0)
        producto = sp.Integer(1)
        detalles = []
        for nivel in range(n):
            coeficiente = tabla[nivel][0]
            polinomio += coeficiente * producto
            detalles.append(Iteracion(nivel, {
                "orden": nivel, "coeficiente": sp.sstr(coeficiente),
            }))
            producto *= (x - sp.Rational(str(xs[nivel])))
        nota = "diferencias divididas de Newton: añade un punto sin rehacer el resto"

    return sp.expand(sp.simplify(polinomio)), detalles, nota


# --------------------------------------------------------------------------- #
# Ecuaciones diferenciales por aproximación
# --------------------------------------------------------------------------- #


def _compilar_edo(expresion: str, variable_x: str = "x", variable_y: str = "y"):
    """Compila y′ = f(x, y) a una función de dos variables."""
    expr = analizar(expresion)
    x, y = sp.Symbol(variable_x), sp.Symbol(variable_y)
    try:
        return sp.lambdify((x, y), expr, "numpy"), expr
    except Exception as e:
        raise ErrorNumerico(f"No se pudo interpretar f(x, y): {e}") from None


def _paso_valido(f, x: float, y: float) -> float:
    try:
        valor = float(f(x, y))
    except (TypeError, ValueError, ZeroDivisionError, OverflowError) as e:
        raise ErrorNumerico(f"f({x:g}, {y:g}) no se puede evaluar ({e})") from None
    if not math.isfinite(valor):
        raise ErrorNumerico(f"f({x:g}, {y:g}) no está definida")
    return valor


def euler(expresion: str, x0: float, y0: float, h: float, pasos: int,
          variable_x: str = "x", variable_y: str = "y") -> tuple[list[Iteracion], str]:
    """Método de Euler: yₙ₊₁ = yₙ + h·f(xₙ, yₙ).

    El más sencillo y el menos preciso: el error global es proporcional a h.
    """
    if pasos < 1 or pasos > 10_000:
        raise ErrorNumerico("El número de pasos debe estar entre 1 y 10 000")
    if h == 0:
        raise ErrorNumerico("El paso h no puede ser 0")

    f, _ = _compilar_edo(expresion, variable_x, variable_y)
    iteraciones: list[Iteracion] = []
    x, y = x0, y0

    for n in range(pasos + 1):
        pendiente = _paso_valido(f, x, y) if n < pasos else float("nan")
        iteraciones.append(Iteracion(n, {
            "xₙ": x, "yₙ": y,
            "f(xₙ,yₙ)": pendiente if n < pasos else "",
        }))
        if n < pasos:
            y += h * pendiente
            x += h

    return iteraciones, f"{pasos} pasos de tamaño h = {h:g}; error global del orden de h"


def runge_kutta_4(expresion: str, x0: float, y0: float, h: float, pasos: int,
                  variable_x: str = "x",
                  variable_y: str = "y") -> tuple[list[Iteracion], str]:
    """Runge-Kutta de cuarto orden.

    Promedia cuatro pendientes en cada paso; el error global es del orden de h⁴,
    así que con el mismo h es muchísimo más preciso que Euler.
    """
    if pasos < 1 or pasos > 10_000:
        raise ErrorNumerico("El número de pasos debe estar entre 1 y 10 000")
    if h == 0:
        raise ErrorNumerico("El paso h no puede ser 0")

    f, _ = _compilar_edo(expresion, variable_x, variable_y)
    iteraciones: list[Iteracion] = []
    x, y = x0, y0

    for n in range(pasos + 1):
        if n < pasos:
            k1 = _paso_valido(f, x, y)
            k2 = _paso_valido(f, x + h / 2, y + h * k1 / 2)
            k3 = _paso_valido(f, x + h / 2, y + h * k2 / 2)
            k4 = _paso_valido(f, x + h, y + h * k3)
            iteraciones.append(Iteracion(n, {
                "xₙ": x, "yₙ": y, "k₁": k1, "k₂": k2, "k₃": k3, "k₄": k4,
            }))
            y += h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
            x += h
        else:
            iteraciones.append(Iteracion(n, {"xₙ": x, "yₙ": y}))

    return iteraciones, f"{pasos} pasos de tamaño h = {h:g}; error global del orden de h⁴"


#: (clave, título, campos que pide el panel)
METODOS_RAICES = [
    ("biseccion", "Bisección", ["expresion", "a", "b", "tolerancia"]),
    ("newton", "Newton-Raphson", ["expresion", "x0", "tolerancia"]),
    ("secante", "Secante", ["expresion", "x0", "x1", "tolerancia"]),
]

METODOS_INTEGRACION = [
    ("trapecio", "Regla del trapecio", ["expresion", "a", "b", "n"]),
    ("simpson", "Regla de Simpson", ["expresion", "a", "b", "n"]),
]

METODOS_INTERPOLACION = [
    ("lagrange", "Polinomio de Lagrange"),
    ("newton", "Diferencias divididas de Newton"),
]

METODOS_EDO = [
    ("euler", "Método de Euler", ["expresion", "x0", "y0", "h", "pasos"]),
    ("rk4", "Runge-Kutta de orden 4", ["expresion", "x0", "y0", "h", "pasos"]),
]
