"""Cálculo simbólico: derivadas, integrales, límites y series.

Todo devuelve pares (etiqueta, valor) para que el panel sólo tenga que
mostrarlos, y todo error sale como ``ErrorSimbolico`` con un mensaje en
castellano.
"""

from __future__ import annotations

import sympy as sp

from .simbolico import ErrorSimbolico, analizar, incognitas, texto, variable_principal

__all__ = [
    "derivar",
    "integrar",
    "integrar_definida",
    "limite",
    "serie_taylor",
    "analizar_funcion",
    "puntos_criticos",
    "OPERACIONES",
]

#: Límite de seguridad: sympy puede tardar mucho con expresiones patológicas.
_ORDEN_MAXIMO = 10


def _preparar(expresion_texto: str, variable_texto: str = "") -> tuple[sp.Expr, sp.Symbol]:
    expresion = analizar(expresion_texto)
    variable = variable_principal(expresion, variable_texto.strip())
    return expresion, variable


def derivar(expresion_texto: str, variable_texto: str = "", orden: int = 1) -> list[tuple[str, str]]:
    """Derivada de orden ``orden`` respecto a ``variable_texto``."""
    if not 1 <= orden <= _ORDEN_MAXIMO:
        raise ErrorSimbolico(f"El orden debe estar entre 1 y {_ORDEN_MAXIMO}")

    expresion, variable = _preparar(expresion_texto, variable_texto)
    try:
        derivada = sp.diff(expresion, variable, orden)
    except (ValueError, TypeError, NotImplementedError) as e:
        raise ErrorSimbolico(f"No se pudo derivar: {e}") from e

    filas = [
        ("Función", f"f({variable}) = {texto(expresion)}"),
        (f"Derivada de orden {orden}", texto(sp.simplify(derivada))),
    ]

    sin_simplificar = texto(derivada)
    if sin_simplificar != texto(sp.simplify(derivada)):
        filas.append(("Sin simplificar", sin_simplificar))

    factorizada = sp.factor(derivada)
    if texto(factorizada) != texto(sp.simplify(derivada)):
        filas.append(("Factorizada", texto(factorizada)))

    # Las derivadas intermedias ayudan a seguir el proceso.
    if orden > 1:
        parcial = expresion
        for k in range(1, orden):
            parcial = sp.diff(parcial, variable)
            filas.append((f"  · derivada {k}ª", texto(sp.simplify(parcial))))

    return filas


def integrar(expresion_texto: str, variable_texto: str = "") -> list[tuple[str, str]]:
    """Integral indefinida."""
    expresion, variable = _preparar(expresion_texto, variable_texto)
    try:
        primitiva = sp.integrate(expresion, variable)
    except (ValueError, TypeError, NotImplementedError) as e:
        raise ErrorSimbolico(f"No se pudo integrar: {e}") from e

    if primitiva.has(sp.Integral):
        raise ErrorSimbolico(
            "Esta integral no tiene primitiva expresable con funciones elementales. "
            "Pruebe con la integral definida, que se calcula numéricamente."
        )

    filas = [
        ("Función", f"f({variable}) = {texto(expresion)}"),
        ("Integral indefinida", f"{texto(sp.simplify(primitiva))} + C"),
    ]
    comprobacion = sp.simplify(sp.diff(primitiva, variable) - expresion)
    filas.append((
        "Comprobación (derivar el resultado)",
        "correcto: se recupera f" if comprobacion == 0 else texto(comprobacion),
    ))
    return filas


def integrar_definida(expresion_texto: str, variable_texto: str,
                      inferior: str, superior: str) -> list[tuple[str, str]]:
    """Integral definida entre dos límites, con valor exacto y aproximado."""
    expresion, variable = _preparar(expresion_texto, variable_texto)
    a = analizar(inferior)
    b = analizar(superior)

    try:
        valor = sp.integrate(expresion, (variable, a, b))
    except (ValueError, TypeError, NotImplementedError) as e:
        raise ErrorSimbolico(f"No se pudo integrar: {e}") from e

    filas = [
        ("Función", f"f({variable}) = {texto(expresion)}"),
        ("Intervalo", f"de {texto(a)} a {texto(b)}"),
    ]

    if valor.has(sp.Integral) or valor.has(sp.nan):
        # Sin primitiva elemental: se recurre a la cuadratura numérica.
        try:
            aproximado = sp.N(sp.Integral(expresion, (variable, a, b)).evalf())
        except (ValueError, TypeError) as e:
            raise ErrorSimbolico(f"La integral no converge o no se puede calcular: {e}") from e
        filas.append(("Valor (numérico)", texto(aproximado)))
        filas.append(("Nota", "sin primitiva elemental: calculada por cuadratura numérica"))
        return filas

    filas.append(("Valor exacto", texto(sp.simplify(valor))))
    try:
        filas.append(("Valor aproximado", texto(sp.N(valor, 10))))
    except (TypeError, ValueError):
        pass

    if valor.is_real is not False:
        filas.append((
            "Interpretación",
            "área con signo entre la curva y el eje horizontal",
        ))
    return filas


def limite(expresion_texto: str, variable_texto: str, punto: str,
           direccion: str = "ambos") -> list[tuple[str, str]]:
    """Límite en un punto. ``direccion`` es ``"ambos"``, ``"+"`` o ``"-"``."""
    expresion, variable = _preparar(expresion_texto, variable_texto)
    destino = analizar(punto) if punto.strip() not in ("oo", "+oo", "inf") else sp.oo
    if punto.strip() in ("-oo", "-inf"):
        destino = -sp.oo

    filas = [
        ("Función", f"f({variable}) = {texto(expresion)}"),
        ("Punto", texto(destino)),
    ]

    def calcular(lado: str):
        try:
            return sp.limit(expresion, variable, destino, lado)
        except (ValueError, TypeError, NotImplementedError) as e:
            raise ErrorSimbolico(f"No se pudo calcular el límite: {e}") from e

    if direccion == "+":
        filas.append(("Límite por la derecha", texto(calcular("+"))))
    elif direccion == "-":
        filas.append(("Límite por la izquierda", texto(calcular("-"))))
    else:
        por_izquierda = calcular("-")
        por_derecha = calcular("+")
        filas.append(("Límite por la izquierda", texto(por_izquierda)))
        filas.append(("Límite por la derecha", texto(por_derecha)))
        if sp.simplify(por_izquierda - por_derecha) == 0:
            filas.append(("Límite", texto(por_derecha)))
        else:
            filas.append(("Límite", "no existe: los límites laterales no coinciden"))
    return filas


def serie_taylor(expresion_texto: str, variable_texto: str, punto: str = "0",
                 orden: int = 5) -> list[tuple[str, str]]:
    """Desarrollo en serie de Taylor (de Maclaurin si el punto es 0)."""
    if not 1 <= orden <= 20:
        raise ErrorSimbolico("El orden debe estar entre 1 y 20")

    expresion, variable = _preparar(expresion_texto, variable_texto)
    centro = analizar(punto) if punto.strip() else sp.Integer(0)

    try:
        serie = sp.series(expresion, variable, centro, orden + 1)
    except (ValueError, TypeError, NotImplementedError) as e:
        raise ErrorSimbolico(f"No se pudo desarrollar la serie: {e}") from e

    polinomio = serie.removeO()
    nombre = "Maclaurin" if centro == 0 else "Taylor"
    return [
        ("Función", f"f({variable}) = {texto(expresion)}"),
        ("Centro del desarrollo", texto(centro)),
        (f"Serie de {nombre} (orden {orden})", texto(serie)),
        ("Polinomio (sin el resto)", texto(sp.expand(polinomio))),
    ]


def puntos_criticos(expresion_texto: str, variable_texto: str = "") -> list[tuple[str, str]]:
    """Máximos, mínimos, inflexiones y asíntotas de una función de una variable."""
    expresion, variable = _preparar(expresion_texto, variable_texto)

    primera = sp.diff(expresion, variable)
    segunda = sp.diff(primera, variable)

    filas = [
        ("Función", f"f({variable}) = {texto(expresion)}"),
        ("f'", texto(sp.simplify(primera))),
        ("f''", texto(sp.simplify(segunda))),
    ]

    try:
        criticos = sp.solve(sp.Eq(primera, 0), variable)
    except (ValueError, TypeError, NotImplementedError):
        criticos = []

    if not criticos:
        filas.append(("Puntos críticos", "no se encontraron (o no son resolubles)"))
    else:
        for punto in criticos:
            if punto.free_symbols:
                continue
            try:
                curvatura = sp.N(segunda.subs(variable, punto))
                altura = sp.N(expresion.subs(variable, punto), 8)
            except (TypeError, ValueError):
                continue
            if not curvatura.is_real:
                continue
            if curvatura > 0:
                tipo = "mínimo local"
            elif curvatura < 0:
                tipo = "máximo local"
            else:
                tipo = "posible inflexión (f'' = 0)"
            filas.append((f"{variable} = {texto(sp.N(punto, 8))}", f"{tipo}, f = {texto(altura)}"))

    try:
        inflexiones = [p for p in sp.solve(sp.Eq(segunda, 0), variable) if not p.free_symbols]
        if inflexiones:
            filas.append((
                "Puntos de inflexión",
                ", ".join(f"{variable} = {texto(sp.N(p, 8))}" for p in inflexiones[:8]),
            ))
    except (ValueError, TypeError, NotImplementedError):
        pass

    for etiqueta, destino in (("Límite en +∞", sp.oo), ("Límite en −∞", -sp.oo)):
        try:
            filas.append((etiqueta, texto(sp.limit(expresion, variable, destino))))
        except (ValueError, TypeError, NotImplementedError):
            pass

    return filas


def analizar_funcion(expresion_texto: str, variable_texto: str = "") -> list[tuple[str, str]]:
    """Ficha completa: dominio, cortes con los ejes, paridad y periodicidad."""
    expresion, variable = _preparar(expresion_texto, variable_texto)
    filas: list[tuple[str, str]] = [("Función", f"f({variable}) = {texto(expresion)}")]

    if len(incognitas(expresion)) > 1:
        filas.append(("Aviso", "la función tiene más de una variable; se analiza respecto a "
                               f"«{variable}»"))

    try:
        dominio = sp.calculus.util.continuous_domain(expresion, variable, sp.S.Reals)
        filas.append(("Dominio", texto(dominio)))
    except (ValueError, TypeError, NotImplementedError):
        filas.append(("Dominio", "no se pudo determinar"))

    try:
        recorrido = sp.calculus.util.function_range(expresion, variable, sp.S.Reals)
        filas.append(("Recorrido", texto(recorrido)))
    except (ValueError, TypeError, NotImplementedError):
        pass

    try:
        filas.append(("Corte con el eje Y", texto(sp.simplify(expresion.subs(variable, 0)))))
    except (TypeError, ValueError, ZeroDivisionError):
        filas.append(("Corte con el eje Y", "no existe (no está definida en 0)"))

    try:
        raices = [r for r in sp.solve(sp.Eq(expresion, 0), variable) if not r.free_symbols]
        reales = [r for r in raices if sp.im(sp.N(r)) == 0]
        filas.append((
            "Cortes con el eje X",
            ", ".join(f"{variable} = {texto(sp.N(r, 8))}" for r in reales[:10]) or "ninguno real",
        ))
    except (ValueError, TypeError, NotImplementedError):
        filas.append(("Cortes con el eje X", "no se pudieron calcular"))

    par = sp.simplify(expresion.subs(variable, -variable) - expresion) == 0
    impar = sp.simplify(expresion.subs(variable, -variable) + expresion) == 0
    filas.append(("Simetría", "par (respecto al eje Y)" if par
                  else "impar (respecto al origen)" if impar else "ninguna"))

    try:
        periodo = sp.periodicity(expresion, variable)
        if periodo:
            filas.append(("Periodo", texto(periodo)))
    except (ValueError, TypeError, NotImplementedError):
        pass

    return filas


#: (clave, título, campos que necesita) — lo consume el panel para montar el formulario.
OPERACIONES = [
    ("derivada", "Derivada", ["expresion", "variable", "orden"]),
    ("integral", "Integral indefinida", ["expresion", "variable"]),
    ("integral_definida", "Integral definida", ["expresion", "variable", "desde", "hasta"]),
    ("limite", "Límite", ["expresion", "variable", "punto", "direccion"]),
    ("taylor", "Serie de Taylor", ["expresion", "variable", "punto", "orden"]),
    ("criticos", "Máximos, mínimos e inflexiones", ["expresion", "variable"]),
    ("analisis", "Análisis completo de la función", ["expresion", "variable"]),
]
