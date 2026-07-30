"""Ajuste de curvas: encontrar la función que mejor describe unos datos.

A diferencia de la interpolación, la curva **no** pasa por todos los puntos: se
busca la que menos se aleja del conjunto. Es lo que se hace con datos
experimentales, que siempre traen error de medida.

Los modelos no lineales se ajustan linealizándolos (tomando logaritmos), que es
el método clásico y el que se explica en clase. Se indica cuando eso ocurre,
porque el resultado minimiza el error de la versión linealizada, no el de la
curva original.
"""

from __future__ import annotations

import math

import sympy as sp

from .estadistica import ErrorEstadistica

__all__ = [
    "ErrorAjuste",
    "Ajuste",
    "ajustar",
    "comparar",
    "MODELOS",
]

MAX_GRADO = 10


class ErrorAjuste(ErrorEstadistica):
    """Los datos no permiten ese ajuste."""


class Ajuste:
    """Resultado de un ajuste: la función, su calidad y cómo evaluarla."""

    def __init__(self, clave: str, nombre: str, expresion: sp.Expr,
                 formula: str, r2: float, linealizado: bool = False) -> None:
        self.clave = clave
        self.nombre = nombre
        self.expresion = expresion
        self.formula = formula
        self.r2 = r2
        self.linealizado = linealizado

    def evaluar(self, x: float) -> float:
        variable = sp.Symbol("x")
        try:
            return float(self.expresion.subs(variable, x))
        except (TypeError, ValueError):
            return float("nan")

    def funcion(self):
        """Versión evaluable con numpy, para dibujar la curva."""
        return sp.lambdify(sp.Symbol("x"), self.expresion, "numpy")


def _validar(x: list[float], y: list[float]) -> None:
    if len(x) != len(y):
        raise ErrorAjuste(
            f"Las dos series deben tener el mismo número de datos "
            f"(X tiene {len(x)} e Y tiene {len(y)})"
        )
    if len(x) < 3:
        raise ErrorAjuste("Hacen falta al menos 3 pares de datos para ajustar una curva")
    if len(set(x)) < 2:
        raise ErrorAjuste("Todos los valores de X son iguales: no hay nada que ajustar")


def _r2(y: list[float], predichos: list[float]) -> float:
    """Coeficiente de determinación sobre los datos **originales**.

    Se calcula siempre contra los datos sin transformar, aunque el ajuste se
    haya hecho linealizando: si no, los modelos no lineales saldrían
    artificialmente favorecidos al compararlos.
    """
    media = math.fsum(y) / len(y)
    total = math.fsum((v - media) ** 2 for v in y)
    residual = math.fsum((v - p) ** 2 for v, p in zip(y, predichos))
    if total == 0:
        return 1.0 if residual == 0 else 0.0
    return max(0.0, 1 - residual / total)


def _minimos_cuadrados(x: list[float], y: list[float], grado: int) -> list[float]:
    """Coeficientes del polinomio de mínimos cuadrados, de mayor a menor grado.

    Resuelve el sistema de ecuaciones normales con sympy para no depender de
    numpy.polyfit, y así mantener el núcleo con las mismas dependencias.
    """
    n = grado + 1
    # Sumas de potencias: Σxⁱ hasta i = 2·grado
    potencias = [math.fsum(v ** i for v in x) for i in range(2 * grado + 1)]
    momentos = [math.fsum(v ** i * w for v, w in zip(x, y)) for i in range(n)]

    matriz = sp.Matrix(n, n, lambda i, j: potencias[i + j])
    vector = sp.Matrix(n, 1, lambda i, _j: momentos[i])

    try:
        solucion = matriz.LUsolve(vector)
    except Exception:
        raise ErrorAjuste(
            f"El sistema de grado {grado} no tiene solución única con estos "
            f"datos. Pruebe con un grado menor o añada más puntos."
        ) from None

    return [float(solucion[i]) for i in range(n - 1, -1, -1)]


def _polinomico(x: list[float], y: list[float], grado: int) -> Ajuste:
    if not 1 <= grado <= MAX_GRADO:
        raise ErrorAjuste(f"El grado debe estar entre 1 y {MAX_GRADO}")
    if grado >= len(x):
        raise ErrorAjuste(
            f"Con {len(x)} puntos no se puede ajustar un polinomio de grado "
            f"{grado}: haría falta al menos {grado + 1}."
        )

    coeficientes = _minimos_cuadrados(x, y, grado)
    variable = sp.Symbol("x")
    expresion = sum(
        sp.Float(c) * variable ** (grado - i) for i, c in enumerate(coeficientes)
    )

    predichos = [float(expresion.subs(variable, v)) for v in x]
    nombre = {1: "Lineal", 2: "Cuadrático", 3: "Cúbico"}.get(grado,
                                                             f"Polinómico grado {grado}")
    return Ajuste(f"poli{grado}", nombre, expresion,
                  _formula_polinomio(coeficientes, grado), _r2(y, predichos))


def _formula_polinomio(coeficientes: list[float], grado: int) -> str:
    partes = []
    for i, c in enumerate(coeficientes):
        potencia = grado - i
        if abs(c) < 1e-14:
            continue
        if potencia == 0:
            termino = f"{c:.6g}"
        elif potencia == 1:
            termino = f"{c:.6g}·x"
        else:
            termino = f"{c:.6g}·x^{potencia}"
        partes.append(termino if not partes else
                      (f" + {termino}" if c > 0 else f" − {termino.lstrip('-')}"))
    return "y = " + ("".join(partes) or "0")


def _exponencial(x: list[float], y: list[float]) -> Ajuste:
    """y = a·e^(b·x), linealizado como ln y = ln a + b·x."""
    if any(v <= 0 for v in y):
        raise ErrorAjuste(
            "El ajuste exponencial exige que todos los valores de Y sean "
            "positivos, porque se linealiza tomando logaritmos."
        )

    logs = [math.log(v) for v in y]
    b, ln_a = _recta(x, logs)
    a = math.exp(ln_a)

    variable = sp.Symbol("x")
    expresion = sp.Float(a) * sp.exp(sp.Float(b) * variable)
    predichos = [a * math.exp(b * v) for v in x]
    return Ajuste("exponencial", "Exponencial", expresion,
                  f"y = {a:.6g}·e^({b:.6g}·x)", _r2(y, predichos), linealizado=True)


def _logaritmico(x: list[float], y: list[float]) -> Ajuste:
    """y = a + b·ln x."""
    if any(v <= 0 for v in x):
        raise ErrorAjuste(
            "El ajuste logarítmico exige que todos los valores de X sean "
            "positivos: ln(x) no existe para x ≤ 0."
        )

    logs = [math.log(v) for v in x]
    b, a = _recta(logs, y)

    variable = sp.Symbol("x")
    expresion = sp.Float(a) + sp.Float(b) * sp.log(variable)
    predichos = [a + b * math.log(v) for v in x]
    signo = "+" if b >= 0 else "−"
    return Ajuste("logaritmico", "Logarítmico", expresion,
                  f"y = {a:.6g} {signo} {abs(b):.6g}·ln(x)", _r2(y, predichos))


def _potencial(x: list[float], y: list[float]) -> Ajuste:
    """y = a·x^b, linealizado como ln y = ln a + b·ln x."""
    if any(v <= 0 for v in x) or any(v <= 0 for v in y):
        raise ErrorAjuste(
            "El ajuste potencial exige que X e Y sean positivos, porque se "
            "linealiza tomando logaritmos en los dos."
        )

    b, ln_a = _recta([math.log(v) for v in x], [math.log(v) for v in y])
    a = math.exp(ln_a)

    variable = sp.Symbol("x")
    expresion = sp.Float(a) * variable ** sp.Float(b)
    predichos = [a * v ** b for v in x]
    return Ajuste("potencial", "Potencial", expresion,
                  f"y = {a:.6g}·x^{b:.6g}", _r2(y, predichos), linealizado=True)


def _recta(x: list[float], y: list[float]) -> tuple[float, float]:
    """Pendiente y ordenada de la recta de mínimos cuadrados."""
    n = len(x)
    media_x = math.fsum(x) / n
    media_y = math.fsum(y) / n
    sxx = math.fsum((v - media_x) ** 2 for v in x)
    if sxx == 0:
        raise ErrorAjuste("Todos los valores de X son iguales")
    sxy = math.fsum((a - media_x) * (b - media_y) for a, b in zip(x, y))
    pendiente = sxy / sxx
    return pendiente, media_y - pendiente * media_x


#: (clave, título, ¿pide grado?)
MODELOS = [
    ("poli1", "Lineal   y = a·x + b", False),
    ("poli2", "Cuadrático   y = a·x² + b·x + c", False),
    ("poli3", "Cúbico", False),
    ("polinomico", "Polinómico de grado n", True),
    ("exponencial", "Exponencial   y = a·e^(b·x)", False),
    ("logaritmico", "Logarítmico   y = a + b·ln x", False),
    ("potencial", "Potencial   y = a·x^b", False),
]


def ajustar(x: list[float], y: list[float], modelo: str, grado: int = 2) -> Ajuste:
    """Ajusta un modelo concreto a los datos."""
    _validar(x, y)

    if modelo.startswith("poli") and modelo != "polinomico":
        return _polinomico(x, y, int(modelo[4:]))
    if modelo == "polinomico":
        return _polinomico(x, y, grado)
    if modelo == "exponencial":
        return _exponencial(x, y)
    if modelo == "logaritmico":
        return _logaritmico(x, y)
    if modelo == "potencial":
        return _potencial(x, y)
    raise ErrorAjuste(f"Modelo desconocido: {modelo!r}")


def comparar(x: list[float], y: list[float]) -> tuple[list[Ajuste], list[tuple[str, str]]]:
    """Prueba todos los modelos y ordena por bondad del ajuste.

    Devuelve la lista ordenada y las filas listas para mostrar, incluida la
    recomendación de cuál usar.
    """
    _validar(x, y)

    candidatos: list[Ajuste] = []
    descartados: list[tuple[str, str]] = []

    for clave in ("poli1", "poli2", "poli3", "exponencial", "logaritmico", "potencial"):
        try:
            candidatos.append(ajustar(x, y, clave))
        except ErrorAjuste as e:
            nombre = dict((c, t) for c, t, _ in MODELOS).get(clave, clave)
            descartados.append((nombre.split("   ")[0], str(e)))

    if not candidatos:
        raise ErrorAjuste("Ningún modelo se puede aplicar a estos datos")

    candidatos.sort(key=lambda a: a.r2, reverse=True)

    filas: list[tuple[str, str]] = [
        ("Número de pares", str(len(x))),
        ("", ""),
        ("Modelo", "r²  ·  ecuación"),
    ]
    for ajuste in candidatos:
        marca = "  ←  mejor" if ajuste is candidatos[0] else ""
        filas.append((ajuste.nombre, f"{ajuste.r2:.6f}  ·  {ajuste.formula}{marca}"))

    mejor = candidatos[0]
    filas.append(("", ""))
    filas.append(("Recomendado", f"{mejor.nombre}:  {mejor.formula}"))
    filas.append(("Bondad del ajuste", _interpretar_r2(mejor.r2)))

    if mejor.linealizado:
        filas.append((
            "Aviso",
            "Este modelo se ajusta linealizando (tomando logaritmos), así que "
            "minimiza el error de la versión transformada, no el de la curva "
            "original. El r² mostrado sí se calcula sobre los datos reales.",
        ))

    if descartados:
        filas.append(("", ""))
        for nombre, motivo in descartados:
            filas.append((f"{nombre}: no aplicable", motivo))

    return candidatos, filas


def _interpretar_r2(r2: float) -> str:
    if r2 >= 0.99:
        return f"{r2:.4f} — excelente: la curva explica casi toda la variación"
    if r2 >= 0.95:
        return f"{r2:.4f} — muy bueno"
    if r2 >= 0.85:
        return f"{r2:.4f} — aceptable"
    if r2 >= 0.6:
        return f"{r2:.4f} — flojo: puede que el modelo no sea el adecuado"
    return f"{r2:.4f} — malo: estos datos no siguen ese comportamiento"


def predecir(ajuste: Ajuste, valores: list[float]) -> list[tuple[str, str]]:
    """Evalúa el modelo en unos valores de x."""
    filas = [("Modelo", ajuste.formula), ("", "")]
    for x in valores:
        y = ajuste.evaluar(x)
        filas.append((f"x = {x:g}", "no definido" if math.isnan(y) else f"y = {y:.8g}"))
    return filas
