"""Transformadas de Laplace y de Fourier, y series de Fourier.

Laplace convierte ecuaciones diferenciales en algebraicas, y por eso se enseña
junto a ellas. Fourier descompone una señal en las frecuencias que la componen.
Ambas tienen su tabla de pares conocidos, que aquí se incluye porque es lo que
se consulta constantemente al estudiarlas.
"""

from __future__ import annotations

import sympy as sp

from .simbolico import ErrorSimbolico, analizar, texto

__all__ = [
    "ErrorTransformada",
    "laplace",
    "laplace_inversa",
    "fourier",
    "fourier_inversa",
    "serie_fourier",
    "coeficientes_fourier",
    "TABLA_LAPLACE",
    "OPERACIONES",
]


class ErrorTransformada(ErrorSimbolico):
    """La transformada no se pudo calcular."""


#: Pares habituales, para consultar sin tener que calcularlos.
TABLA_LAPLACE = [
    ("1", "1/s", "s > 0"),
    ("t", "1/s²", "s > 0"),
    ("tⁿ", "n! / s^(n+1)", "s > 0"),
    ("e^(at)", "1/(s − a)", "s > a"),
    ("sen(at)", "a / (s² + a²)", "s > 0"),
    ("cos(at)", "s / (s² + a²)", "s > 0"),
    ("senh(at)", "a / (s² − a²)", "s > |a|"),
    ("cosh(at)", "s / (s² − a²)", "s > |a|"),
    ("t·e^(at)", "1 / (s − a)²", "s > a"),
    ("e^(at)·sen(bt)", "b / ((s−a)² + b²)", "s > a"),
    ("e^(at)·cos(bt)", "(s−a) / ((s−a)² + b²)", "s > a"),
    ("δ(t)  (delta de Dirac)", "1", "toda s"),
    ("u(t)  (escalón unitario)", "1/s", "s > 0"),
    ("f′(t)", "s·F(s) − f(0)", "—"),
    ("f″(t)", "s²·F(s) − s·f(0) − f′(0)", "—"),
    ("∫₀ᵗ f(τ)dτ", "F(s) / s", "—"),
]

#: Tiempo máximo razonable: algunas transformadas se cuelgan en sympy.
_ORDEN_MAXIMO_SERIE = 30


def _simbolos(origen: str, destino: str) -> tuple[sp.Symbol, sp.Symbol]:
    if len(origen) != 1 or len(destino) != 1:
        raise ErrorTransformada("Las variables deben ser una sola letra")
    if origen == destino:
        raise ErrorTransformada("Las dos variables no pueden llamarse igual")
    # `positive=True` en la variable temporal ayuda mucho a sympy a simplificar.
    return sp.Symbol(origen, positive=True), sp.Symbol(destino)


def laplace(expresion_texto: str, variable_t: str = "t",
            variable_s: str = "s") -> list[tuple[str, str]]:
    """Transformada de Laplace  F(s) = ∫₀^∞ f(t)·e^(−st) dt."""
    t, s = _simbolos(variable_t, variable_s)
    expresion = analizar(expresion_texto, frozenset({variable_t}), {variable_t: t})

    if not expresion.has(t) and expresion.is_number:
        # Una constante también tiene transformada; se avisa por si es un error.
        pass

    try:
        resultado = sp.laplace_transform(expresion, t, s, noconds=True)
    except Exception as e:
        raise ErrorTransformada(
            f"No se pudo calcular la transformada ({type(e).__name__}: {e})"
        ) from None

    if resultado.has(sp.LaplaceTransform):
        raise ErrorTransformada(
            "sympy no sabe calcular esta transformada en forma cerrada."
        )

    filas = [
        ("Función", f"f({t}) = {texto(expresion)}"),
        ("", ""),
        ("Transformada", f"F({s}) = {texto(sp.simplify(resultado))}"),
    ]

    factorizada = sp.factor(sp.simplify(resultado))
    if texto(factorizada) != texto(sp.simplify(resultado)):
        filas.append(("Factorizada", texto(factorizada)))

    try:
        vuelta = sp.inverse_laplace_transform(resultado, s, t, noconds=True)
        if not vuelta.has(sp.InverseLaplaceTransform):
            coincide = sp.simplify(vuelta - expresion) == 0
            filas.append((
                "Comprobación (antitransformar)",
                "correcta: se recupera f(t)" if coincide else texto(vuelta),
            ))
    except Exception:
        pass

    return filas


def laplace_inversa(expresion_texto: str, variable_s: str = "s",
                    variable_t: str = "t") -> list[tuple[str, str]]:
    """Transformada inversa de Laplace: de F(s) a f(t)."""
    t, s = _simbolos(variable_t, variable_s)
    expresion = analizar(expresion_texto, frozenset({variable_s}), {variable_s: s})

    filas = [("Función en el dominio de s", f"F({s}) = {texto(expresion)}")]

    # Las fracciones se descomponen en fracciones simples, que es como se hace a
    # mano y como se encuentran los pares en la tabla.
    try:
        descompuesta = sp.apart(expresion, s)
        if texto(descompuesta) != texto(expresion):
            filas.append(("Fracciones simples", texto(descompuesta)))
    except (sp.PolynomialError, NotImplementedError, ValueError):
        pass

    try:
        resultado = sp.inverse_laplace_transform(expresion, s, t, noconds=True)
    except Exception as e:
        raise ErrorTransformada(
            f"No se pudo antitransformar ({type(e).__name__}: {e})"
        ) from None

    if resultado.has(sp.InverseLaplaceTransform):
        raise ErrorTransformada(
            "sympy no sabe antitransformar esta expresión en forma cerrada."
        )

    filas.append(("", ""))
    filas.append(("Transformada inversa", f"f({t}) = {texto(sp.simplify(resultado))}"))
    filas.append((
        "Nota",
        "θ(t) es la función escalón de Heaviside: vale 0 antes de t = 0 y 1 después.",
    ))
    return filas


def fourier(expresion_texto: str, variable_x: str = "x",
            variable_k: str = "k") -> list[tuple[str, str]]:
    """Transformada de Fourier."""
    x, k = _simbolos(variable_x, variable_k)
    # La variable de Fourier recorre toda la recta real, no sólo los positivos.
    x = sp.Symbol(variable_x, real=True)
    expresion = analizar(expresion_texto, frozenset({variable_x}), {variable_x: x})

    try:
        resultado = sp.fourier_transform(expresion, x, k)
    except Exception as e:
        raise ErrorTransformada(
            f"No se pudo calcular la transformada ({type(e).__name__}: {e})"
        ) from None

    if resultado.has(sp.FourierTransform):
        raise ErrorTransformada(
            "sympy no sabe calcular esta transformada en forma cerrada. "
            "Las funciones que no decaen en el infinito (senos, constantes) "
            "sólo tienen transformada en el sentido de las distribuciones."
        )

    return [
        ("Función", f"f({x}) = {texto(expresion)}"),
        ("", ""),
        ("Transformada", f"F({k}) = {texto(sp.simplify(resultado))}"),
        ("Convenio", "F(k) = ∫ f(x)·e^(−2πikx) dx"),
    ]


def fourier_inversa(expresion_texto: str, variable_k: str = "k",
                    variable_x: str = "x") -> list[tuple[str, str]]:
    """Transformada inversa de Fourier."""
    k = sp.Symbol(variable_k, real=True)
    x = sp.Symbol(variable_x, real=True)
    expresion = analizar(expresion_texto, frozenset({variable_k}), {variable_k: k})

    try:
        resultado = sp.inverse_fourier_transform(expresion, k, x)
    except Exception as e:
        raise ErrorTransformada(f"No se pudo antitransformar ({e})") from None

    if resultado.has(sp.InverseFourierTransform):
        raise ErrorTransformada("sympy no sabe antitransformar esta expresión.")

    return [
        ("Función en el dominio de k", f"F({k}) = {texto(expresion)}"),
        ("", ""),
        ("Transformada inversa", f"f({x}) = {texto(sp.simplify(resultado))}"),
    ]


def coeficientes_fourier(expresion_texto: str, inicio: str, fin: str,
                         orden: int = 5,
                         variable_x: str = "x") -> tuple[sp.Expr, list[tuple[str, str]]]:
    """Serie de Fourier de una función en un intervalo.

    Devuelve el desarrollo truncado y la tabla de coeficientes aₙ y bₙ.
    """
    if not 1 <= orden <= _ORDEN_MAXIMO_SERIE:
        raise ErrorTransformada(f"El orden debe estar entre 1 y {_ORDEN_MAXIMO_SERIE}")

    x = sp.Symbol(variable_x, real=True)
    expresion = analizar(expresion_texto, frozenset({variable_x}), {variable_x: x})
    a = analizar(inicio)
    b = analizar(fin)

    if sp.simplify(b - a) == 0:
        raise ErrorTransformada("El intervalo no puede ser vacío")

    periodo = sp.simplify(b - a)
    mitad = periodo / 2

    filas: list[tuple[str, str]] = [
        ("Función", f"f({x}) = {texto(expresion)}"),
        ("Intervalo", f"[{texto(a)}, {texto(b)}]   ·   periodo T = {texto(periodo)}"),
        ("", ""),
    ]

    try:
        a0 = sp.simplify(sp.integrate(expresion, (x, a, b)) / periodo)
    except Exception as e:
        raise ErrorTransformada(f"No se pudo calcular a₀ ({e})") from None

    filas.append(("a₀ (término constante)", texto(a0)))

    serie = a0
    for n in range(1, orden + 1):
        argumento = 2 * sp.pi * n * x / periodo
        try:
            an = sp.simplify(sp.integrate(expresion * sp.cos(argumento), (x, a, b)) / mitad)
            bn = sp.simplify(sp.integrate(expresion * sp.sin(argumento), (x, a, b)) / mitad)
        except Exception:
            filas.append((f"n = {n}", "no se pudo calcular"))
            continue

        serie += an * sp.cos(argumento) + bn * sp.sin(argumento)
        if an != 0 or bn != 0:
            filas.append((f"n = {n}", f"aₙ = {texto(an)}    bₙ = {texto(bn)}"))

    filas.append(("", ""))
    par = sp.simplify(expresion.subs(x, -x) - expresion) == 0
    impar = sp.simplify(expresion.subs(x, -x) + expresion) == 0
    if par:
        filas.append(("Simetría", "función par: sólo hay términos en coseno (bₙ = 0)"))
    elif impar:
        filas.append(("Simetría", "función impar: sólo hay términos en seno (aₙ = 0)"))

    return sp.simplify(serie), filas


def serie_fourier(expresion_texto: str, inicio: str, fin: str, orden: int = 5,
                  variable_x: str = "x") -> list[tuple[str, str]]:
    """Serie de Fourier presentada como filas para la interfaz."""
    serie, filas = coeficientes_fourier(expresion_texto, inicio, fin, orden, variable_x)
    filas.append(("", ""))
    filas.append((f"Serie truncada (orden {orden})", texto(serie)))
    return filas


#: (clave, título, campos que pide el panel)
OPERACIONES = [
    ("laplace", "Transformada de Laplace", ["expresion"]),
    ("laplace_inversa", "Transformada inversa de Laplace", ["expresion"]),
    ("fourier", "Transformada de Fourier", ["expresion"]),
    ("fourier_inversa", "Transformada inversa de Fourier", ["expresion"]),
    ("serie", "Serie de Fourier", ["expresion", "desde", "hasta", "orden"]),
    ("tabla", "Tabla de transformadas de Laplace", []),
]
