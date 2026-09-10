"""Resolución paso a paso.

El resultado de un cálculo dice *qué*; estos pasos dicen *cómo*. Es lo que
busca quien está aprendiendo, y la razón de ser de herramientas como Symbolab.

Cada función devuelve una lista de :class:`Paso`, que el panel sólo tiene que
pintar. Para las derivadas se recorre el árbol de la expresión aplicando las
reglas una a una; para las integrales se aprovecha ``integral_steps`` de sympy,
que ya devuelve el árbol de reglas usado, y aquí se traduce y se explica.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import sympy as sp

from .simbolico import ErrorSimbolico, texto

__all__ = [
    "Paso",
    "pasos_derivada",
    "pasos_integral",
    "pasos_ecuacion",
    "pasos_sistema",
]


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


def _con_aproximacion(valor) -> str:
    """Texto de una solución, añadiendo el decimal sólo si aporta algo.

    Para una raíz exacta como 2 no tiene sentido escribir «2 ≈ 2.0000000»; sí lo
    tiene para √2 o para una fracción.
    """
    simplificada = sp.simplify(valor)
    if simplificada.is_number and simplificada.is_rational:
        return texto(simplificada)
    try:
        aproximada = sp.N(simplificada, 8)
    except (TypeError, ValueError):
        return texto(simplificada)
    if texto(aproximada) == texto(simplificada):
        return texto(simplificada)
    return f"{texto(simplificada)}   ≈ {texto(aproximada)}"


# --------------------------------------------------------------------------- #
# Derivadas
# --------------------------------------------------------------------------- #

#: Derivada de cada función elemental, para poder nombrar la regla aplicada.
_DERIVADAS = {
    sp.sin: ("seno", lambda u: sp.cos(u)),
    sp.cos: ("coseno", lambda u: -sp.sin(u)),
    sp.tan: ("tangente", lambda u: 1 + sp.tan(u) ** 2),
    sp.asin: ("arcoseno", lambda u: 1 / sp.sqrt(1 - u ** 2)),
    sp.acos: ("arcocoseno", lambda u: -1 / sp.sqrt(1 - u ** 2)),
    sp.atan: ("arcotangente", lambda u: 1 / (1 + u ** 2)),
    sp.sinh: ("seno hiperbólico", lambda u: sp.cosh(u)),
    sp.cosh: ("coseno hiperbólico", lambda u: sp.sinh(u)),
    sp.tanh: ("tangente hiperbólica", lambda u: 1 - sp.tanh(u) ** 2),
    sp.exp: ("exponencial", lambda u: sp.exp(u)),
    sp.log: ("logaritmo", lambda u: 1 / u),
}


def pasos_derivada(expresion: sp.Expr, variable: sp.Symbol) -> list[Paso]:
    """Desarrollo de la derivada, regla a regla."""
    acumulador = _Acumulador()
    acumulador.add("Función de partida", f"Derivamos respecto a {variable}.",
                   f"f({variable}) = {texto(expresion)}")

    derivada = _derivar(expresion, variable, acumulador, nivel=1)

    simplificada = sp.simplify(derivada)
    acumulador.add("Resultado sin simplificar", "", texto(derivada))
    if texto(simplificada) != texto(derivada):
        acumulador.add("Simplificando", "Agrupamos términos semejantes.",
                       texto(simplificada))
    acumulador.add("Derivada", "", f"f'({variable}) = {texto(simplificada)}")
    return acumulador.pasos


def _derivar(expresion: sp.Expr, variable: sp.Symbol, acumulador: _Acumulador,
             nivel: int) -> sp.Expr:
    """Deriva anotando la regla usada en cada nodo del árbol."""
    if nivel > 12:  # expresiones absurdamente anidadas
        return sp.diff(expresion, variable)

    if not expresion.has(variable):
        acumulador.add("Regla de la constante",
                       f"{texto(expresion)} no depende de {variable}, así que su "
                       f"derivada es 0.", "0", nivel)
        return sp.Integer(0)

    if expresion == variable:
        acumulador.add("Derivada de la variable", f"La derivada de {variable} es 1.",
                       "1", nivel)
        return sp.Integer(1)

    # --- suma y resta -------------------------------------------------- #
    if isinstance(expresion, sp.Add):
        acumulador.add("Regla de la suma",
                       "La derivada de una suma es la suma de las derivadas. "
                       "Derivamos cada sumando por separado.",
                       texto(expresion), nivel)
        partes = [_derivar(t, variable, acumulador, nivel + 1) for t in expresion.args]
        return sp.Add(*partes)

    # --- producto ------------------------------------------------------- #
    if isinstance(expresion, sp.Mul):
        constantes = [f for f in expresion.args if not f.has(variable)]
        variables = [f for f in expresion.args if f.has(variable)]

        if constantes and len(variables) == 1:
            constante = sp.Mul(*constantes)
            acumulador.add("Constante por función",
                           f"El factor {texto(constante)} es constante: sale fuera "
                           f"de la derivada.", texto(expresion), nivel)
            return constante * _derivar(variables[0], variable, acumulador, nivel + 1)

        if len(variables) >= 2:
            u = variables[0]
            v = sp.Mul(*variables[1:]) * sp.Mul(*constantes) if constantes else sp.Mul(*variables[1:])
            acumulador.add("Regla del producto",
                           "(u·v)' = u'·v + u·v'   con   "
                           f"u = {texto(u)}   y   v = {texto(v)}",
                           texto(expresion), nivel)
            du = _derivar(u, variable, acumulador, nivel + 1)
            dv = _derivar(v, variable, acumulador, nivel + 1)
            return du * v + u * dv

    # --- potencia ------------------------------------------------------- #
    if isinstance(expresion, sp.Pow):
        base, exponente = expresion.args

        if not exponente.has(variable):
            if base == variable:
                acumulador.add("Regla de la potencia",
                               f"(x^n)' = n·x^(n−1), con n = {texto(exponente)}.",
                               texto(exponente * variable ** (exponente - 1)), nivel)
                return exponente * variable ** (exponente - 1)

            acumulador.add("Regla de la cadena con potencia",
                           f"(u^n)' = n·u^(n−1)·u', con n = {texto(exponente)} y "
                           f"u = {texto(base)}.", texto(expresion), nivel)
            du = _derivar(base, variable, acumulador, nivel + 1)
            return exponente * base ** (exponente - 1) * du

        if not base.has(variable):
            acumulador.add("Derivada de una exponencial",
                           f"(a^u)' = a^u·ln(a)·u', con a = {texto(base)}.",
                           texto(expresion), nivel)
            du = _derivar(exponente, variable, acumulador, nivel + 1)
            return expresion * sp.log(base) * du

        # Ambos dependen de x: derivación logarítmica.
        acumulador.add("Derivación logarítmica",
                       "La base y el exponente dependen de la variable, así que "
                       "se aplica u^v = e^(v·ln u).", texto(expresion), nivel)
        return sp.diff(expresion, variable)

    # --- funciones elementales ------------------------------------------ #
    for clase, (nombre, derivada) in _DERIVADAS.items():
        if isinstance(expresion, clase):
            argumento = expresion.args[0]
            if argumento == variable:
                resultado = derivada(argumento)
                acumulador.add(f"Derivada del {nombre}",
                               f"({texto(expresion)})' = {texto(resultado)}",
                               texto(resultado), nivel)
                return resultado

            acumulador.add("Regla de la cadena",
                           f"Derivamos el {nombre} y multiplicamos por la derivada "
                           f"de dentro: u = {texto(argumento)}.",
                           texto(expresion), nivel)
            du = _derivar(argumento, variable, acumulador, nivel + 1)
            return derivada(argumento) * du

    # --- cualquier otra cosa -------------------------------------------- #
    resultado = sp.diff(expresion, variable)
    acumulador.add("Derivada directa",
                   f"Se aplica la derivada conocida de {texto(expresion)}.",
                   texto(resultado), nivel)
    return resultado


# --------------------------------------------------------------------------- #
# Integrales
# --------------------------------------------------------------------------- #

#: Nombre en castellano de cada regla de ``sympy.integrals.manualintegrate``.
_REGLAS_INTEGRAL = {
    "ConstantRule": ("Integral de una constante", "∫k dx = k·x"),
    "ConstantTimesRule": ("Constante por función",
                          "La constante sale fuera: ∫k·f(x) dx = k·∫f(x) dx"),
    "PowerRule": ("Regla de la potencia", "∫xⁿ dx = xⁿ⁺¹/(n+1),  con n ≠ −1"),
    "AddRule": ("Regla de la suma",
                "La integral de una suma es la suma de las integrales"),
    "URule": ("Cambio de variable (sustitución)",
              "Se sustituye una parte por u para simplificar la integral"),
    "USubstitutionRule": ("Cambio de variable (sustitución)",
                          "Se sustituye una parte por u para simplificar la integral"),
    "PartsRule": ("Integración por partes", "∫u dv = u·v − ∫v du"),
    "CyclicPartsRule": ("Integración por partes cíclica",
                        "Tras aplicar partes varias veces reaparece la integral "
                        "original y se despeja"),
    "SinRule": ("Integral del seno", "∫sen(x) dx = −cos(x)"),
    "CosRule": ("Integral del coseno", "∫cos(x) dx = sen(x)"),
    "TanRule": ("Integral de la tangente", "∫tan(x) dx = −ln|cos(x)|"),
    "SecRule": ("Integral de la secante", ""),
    "CscRule": ("Integral de la cosecante", ""),
    "CotRule": ("Integral de la cotangente", ""),
    "ExpRule": ("Integral de la exponencial", "∫eˣ dx = eˣ"),
    "ReciprocalRule": ("Integral de 1/x", "∫(1/x) dx = ln|x|"),
    "ArctanRule": ("Integral que da un arcotangente",
                   "∫1/(1+x²) dx = arctan(x)"),
    "ArcsinRule": ("Integral que da un arcoseno", "∫1/√(1−x²) dx = arcsen(x)"),
    "ArccothRule": ("Integral que da una arcocotangente hiperbólica", ""),
    "RewriteRule": ("Reescritura previa",
                    "Se reescribe la expresión en una forma que sí sabemos integrar"),
    "AlternativeRule": ("Camino elegido",
                        "Hay varias formas de resolverla; se sigue la más directa"),
    "PiecewiseRule": ("Distinción de casos",
                      "El resultado depende del valor de los parámetros"),
    "TrigSubstitutionRule": ("Sustitución trigonométrica", ""),
    "SqrtQuadraticRule": ("Raíz de un polinomio de segundo grado", ""),
    "DontKnowRule": ("Sin método elemental",
                     "sympy no encuentra un procedimiento paso a paso para esta "
                     "integral, aunque sepa calcular el resultado"),
}


def pasos_integral(expresion: sp.Expr, variable: sp.Symbol) -> list[Paso]:
    """Desarrollo de la integral indefinida."""
    from sympy.integrals.manualintegrate import integral_steps

    acumulador = _Acumulador()
    acumulador.add("Integral de partida", f"Integramos respecto a {variable}.",
                   f"∫ {texto(expresion)} d{variable}")

    try:
        arbol = integral_steps(expresion, variable)
    except (ValueError, TypeError, NotImplementedError, RecursionError) as e:
        raise ErrorSimbolico(
            f"No se pudo desarrollar el procedimiento de esta integral ({e})"
        ) from None

    _recorrer_reglas(arbol, acumulador, nivel=1)

    primitiva = sp.integrate(expresion, variable)
    if primitiva.has(sp.Integral):
        raise ErrorSimbolico(
            "Esta integral no tiene primitiva expresable con funciones elementales."
        )

    acumulador.add("Resultado", "No olvide la constante de integración.",
                   f"{texto(sp.simplify(primitiva))} + C")
    comprobacion = sp.simplify(sp.diff(primitiva, variable) - expresion)
    acumulador.add(
        "Comprobación",
        "Derivando el resultado debe recuperarse la función de partida.",
        "correcto" if comprobacion == 0 else f"queda {texto(comprobacion)}",
    )
    return acumulador.pasos


def _recorrer_reglas(regla, acumulador: _Acumulador, nivel: int) -> None:
    """Recorre el árbol de reglas de sympy traduciendo cada nodo."""
    if nivel > 10:
        return

    nombre_clase = type(regla).__name__
    titulo, detalle = _REGLAS_INTEGRAL.get(
        nombre_clase, (f"Regla: {nombre_clase}", "")
    )

    integrando = getattr(regla, "integrand", None)
    acumulador.add(titulo, detalle,
                   f"∫ {texto(integrando)} d{getattr(regla, 'variable', 'x')}"
                   if integrando is not None else "",
                   nivel)

    # Las subreglas aparecen en atributos distintos según la versión de sympy.
    # De `alternatives` sólo interesa la primera: es el camino que sympy elige.
    for atributo in ("substeps", "substep", "subrules", "alternatives"):
        hijo = getattr(regla, atributo, None)
        if hijo is None:
            continue
        if isinstance(hijo, (list, tuple)):
            candidatos = [s for s in hijo if _es_regla(s)]
            if atributo == "alternatives":
                candidatos = candidatos[:1]
            for sub in candidatos:
                _recorrer_reglas(sub, acumulador, nivel + 1)
        elif _es_regla(hijo):
            _recorrer_reglas(hijo, acumulador, nivel + 1)


def _es_regla(objeto) -> bool:
    return hasattr(objeto, "integrand") or type(objeto).__name__.endswith("Rule")


# --------------------------------------------------------------------------- #
# Ecuaciones
# --------------------------------------------------------------------------- #


def pasos_ecuacion(expresion: sp.Expr, variable: sp.Symbol) -> list[Paso]:
    """Desarrollo de la resolución de una ecuación de una incógnita.

    ``expresion`` está ya igualada a cero.
    """
    acumulador = _Acumulador()
    acumulador.add("Ecuación", "Pasamos todo a un lado para igualar a cero.",
                   f"{texto(expresion)} = 0")

    desarrollada = sp.expand(expresion)
    if texto(desarrollada) != texto(expresion):
        acumulador.add("Desarrollamos", "Quitamos paréntesis y agrupamos.",
                       f"{texto(desarrollada)} = 0")

    try:
        polinomio = sp.Poly(desarrollada, variable)
        grado = polinomio.degree()
    except (sp.PolynomialError, sp.GeneratorsNeeded, TypeError):
        return _pasos_no_polinomica(desarrollada, variable, acumulador)

    if grado == 1:
        return _pasos_lineal(polinomio, variable, acumulador)
    if grado == 2:
        return _pasos_cuadratica(polinomio, variable, acumulador)
    return _pasos_grado_alto(desarrollada, variable, grado, acumulador)


def _pasos_lineal(polinomio: sp.Poly, variable: sp.Symbol,
                  acumulador: _Acumulador) -> list[Paso]:
    a, b = polinomio.all_coeffs()
    acumulador.add("Es una ecuación de primer grado",
                   f"Tiene la forma a·{variable} + b = 0, con a = {texto(a)} y "
                   f"b = {texto(b)}.")
    # Con b negativo hay que sumar, no restar: decir «restamos −8» confunde.
    verbo = "Sumamos" if b.is_number and b < 0 else "Restamos"
    acumulador.add(f"Despejamos {variable}",
                   f"{verbo} {texto(abs(b) if b.is_number else b)} en los dos lados.",
                   f"{texto(a)}·{variable} = {texto(-b)}")
    solucion = sp.simplify(-b / a)
    acumulador.add("Dividimos entre el coeficiente",
                   f"Dividimos los dos lados entre {texto(a)}.",
                   f"{variable} = {texto(solucion)}")
    _comprobar(acumulador, polinomio.as_expr(), variable, solucion)
    return acumulador.pasos


def _pasos_cuadratica(polinomio: sp.Poly, variable: sp.Symbol,
                      acumulador: _Acumulador) -> list[Paso]:
    a, b, c = polinomio.all_coeffs()
    acumulador.add("Es una ecuación de segundo grado",
                   f"Tiene la forma a·{variable}² + b·{variable} + c = 0, con "
                   f"a = {texto(a)}, b = {texto(b)} y c = {texto(c)}.")

    factorizada = sp.factor(polinomio.as_expr())
    if texto(factorizada) != texto(polinomio.as_expr()):
        acumulador.add("Se puede factorizar",
                       "Un producto es cero cuando lo es alguno de sus factores.",
                       f"{texto(factorizada)} = 0")

    discriminante = sp.simplify(b ** 2 - 4 * a * c)
    acumulador.add("Calculamos el discriminante", "Δ = b² − 4·a·c",
                   f"Δ = ({texto(b)})² − 4·({texto(a)})·({texto(c)}) = "
                   f"{texto(discriminante)}")

    if discriminante.is_number:
        if discriminante > 0:
            lectura = "Δ > 0: hay dos soluciones reales distintas."
        elif discriminante == 0:
            lectura = "Δ = 0: hay una solución real doble."
        else:
            lectura = "Δ < 0: no hay soluciones reales, sino dos complejas conjugadas."
        acumulador.add("Qué significa el discriminante", lectura)

    acumulador.add("Aplicamos la fórmula",
                   f"{variable} = (−b ± √Δ) / (2·a)",
                   f"{variable} = ({texto(-b)} ± √{texto(discriminante)}) / "
                   f"{texto(2 * a)}")

    raices = sp.solve(sp.Eq(polinomio.as_expr(), 0), variable)
    for i, raiz in enumerate(raices, 1):
        acumulador.add(f"Solución {i}", "",
                       f"{variable} = {_con_aproximacion(raiz)}")

    if raices:
        _comprobar(acumulador, polinomio.as_expr(), variable, raices[0])
    return acumulador.pasos


def _pasos_grado_alto(expresion: sp.Expr, variable: sp.Symbol, grado: int,
                      acumulador: _Acumulador) -> list[Paso]:
    acumulador.add(f"Es una ecuación de grado {grado}",
                   f"Puede tener hasta {grado} soluciones, contando las repetidas.")

    factorizada = sp.factor(expresion)
    if texto(factorizada) != texto(expresion):
        acumulador.add("Factorizamos",
                       "Buscamos raíces para descomponerla en factores más "
                       "simples. Un producto vale 0 si algún factor vale 0.",
                       f"{texto(factorizada)} = 0")
        for factor, _ in sp.factor_list(expresion)[1]:
            if factor.has(variable):
                acumulador.add("Igualamos un factor a cero", "",
                               f"{texto(factor)} = 0", nivel=1)

    raices = sp.solve(sp.Eq(expresion, 0), variable)
    for i, raiz in enumerate(raices, 1):
        acumulador.add(f"Solución {i}", "", f"{variable} = {texto(sp.simplify(raiz))}")
    if not raices:
        acumulador.add("Sin soluciones", "La ecuación no tiene solución.")
    return acumulador.pasos


def _pasos_no_polinomica(expresion: sp.Expr, variable: sp.Symbol,
                         acumulador: _Acumulador) -> list[Paso]:
    acumulador.add("No es una ecuación polinómica",
                   "Intervienen funciones como senos, logaritmos o exponenciales, "
                   "así que no hay una fórmula general: se resuelve despejando.")

    raices = sp.solve(sp.Eq(expresion, 0), variable)
    if not raices:
        acumulador.add("Sin soluciones", "No se encontró ninguna solución.")
        return acumulador.pasos

    for i, raiz in enumerate(raices, 1):
        acumulador.add(f"Solución {i}", "",
                       f"{variable} = {_con_aproximacion(raiz)}")

    acumulador.add("Aviso",
                   "Las ecuaciones con funciones periódicas (senos, cosenos) "
                   "suelen tener infinitas soluciones; aquí se muestran las "
                   "principales.")
    return acumulador.pasos


def _comprobar(acumulador: _Acumulador, expresion: sp.Expr, variable: sp.Symbol,
               solucion) -> None:
    try:
        residuo = sp.simplify(expresion.subs(variable, solucion))
    except (TypeError, ValueError):
        return
    acumulador.add(
        "Comprobación",
        f"Sustituimos {variable} = {texto(sp.simplify(solucion))} en la ecuación.",
        "0 = 0, correcto" if residuo == 0 else f"queda {texto(residuo)}",
    )


# --------------------------------------------------------------------------- #
# Sistemas lineales
# --------------------------------------------------------------------------- #


def pasos_sistema(ecuaciones: list, incognitas: list) -> list[Paso]:
    """Desarrollo por eliminación de Gauss sobre la matriz ampliada."""
    acumulador = _Acumulador()
    nombres = [s.name for s in incognitas]

    matriz, terminos = sp.linear_eq_to_matrix(ecuaciones, incognitas)
    ampliada = matriz.row_join(terminos)

    acumulador.add("Escribimos la matriz ampliada",
                   f"Cada fila es una ecuación; las columnas son "
                   f"{', '.join(nombres)} y el término independiente.",
                   _matriz(ampliada))

    trabajo = ampliada.copy()
    filas, columnas = trabajo.rows, len(incognitas)
    fila_pivote = 0

    for columna in range(columnas):
        if fila_pivote >= filas:
            break

        # Se busca un pivote no nulo en la columna actual.
        seleccion = None
        for fila in range(fila_pivote, filas):
            if sp.simplify(trabajo[fila, columna]) != 0:
                seleccion = fila
                break
        if seleccion is None:
            continue

        if seleccion != fila_pivote:
            trabajo.row_swap(fila_pivote, seleccion)
            acumulador.add(
                f"Intercambiamos F{fila_pivote + 1} y F{seleccion + 1}",
                f"Necesitamos un número distinto de 0 en la columna de "
                f"{nombres[columna]}.", _matriz(trabajo))

        pivote = trabajo[fila_pivote, columna]
        if sp.simplify(pivote - 1) != 0:
            trabajo.row_op(fila_pivote, lambda valor, _c, p=pivote: valor / p)
            acumulador.add(
                f"F{fila_pivote + 1} ÷ {texto(pivote)}",
                f"Dividimos la fila para que el pivote de {nombres[columna]} valga 1.",
                _matriz(trabajo))

        for fila in range(filas):
            if fila == fila_pivote:
                continue
            factor = sp.simplify(trabajo[fila, columna])
            if factor == 0:
                continue
            trabajo.row_op(
                fila,
                lambda valor, c, f=factor, fp=fila_pivote: valor - f * trabajo[fp, c],
            )
            signo = "−" if factor > 0 else "+"
            # «F2 − 1·F1» se lee peor que «F2 − F1».
            magnitud = "" if abs(factor) == 1 else f"{texto(abs(factor))}·"
            acumulador.add(
                f"F{fila + 1} {signo} {magnitud}F{fila_pivote + 1}",
                f"Hacemos 0 el resto de la columna de {nombres[columna]}.",
                _matriz(trabajo))

        fila_pivote += 1

    acumulador.add("Matriz escalonada reducida",
                   "Cada incógnita queda despejada en su fila.", _matriz(trabajo))

    rango = matriz.rank()
    if rango < ampliada.rank():
        acumulador.add(
            "El sistema es incompatible",
            "Ha quedado una fila del tipo 0 = k con k ≠ 0, que es imposible: "
            "el sistema no tiene solución.")
        return acumulador.pasos

    solucion = sp.linsolve(ecuaciones, incognitas)
    if solucion:
        tupla = next(iter(solucion))
        libres = {str(s) for e in tupla for s in e.free_symbols}
        if rango == len(incognitas) and not libres:
            for nombre, valor in zip(nombres, tupla):
                acumulador.add("Solución", "", f"{nombre} = {texto(sp.simplify(valor))}")
        else:
            grados = len(incognitas) - rango
            acumulador.add(
                "Infinitas soluciones",
                f"Quedan {grados} incógnita(s) libre(s): el sistema es compatible "
                f"indeterminado.")
            for nombre, valor in zip(nombres, tupla):
                acumulador.add("", "", f"{nombre} = {texto(sp.simplify(valor))}", nivel=1)
    return acumulador.pasos


def _matriz(matriz: sp.Matrix) -> str:
    """Matriz ampliada alineada, con la barra que separa los términos."""
    tabla = [[texto(matriz[i, j]) for j in range(matriz.cols)]
             for i in range(matriz.rows)]
    if not tabla:
        return ""
    anchos = [max(len(fila[j]) for fila in tabla) for j in range(matriz.cols)]
    lineas = []
    for fila in tabla:
        coeficientes = "  ".join(v.rjust(anchos[i]) for i, v in enumerate(fila[:-1]))
        lineas.append(f"[ {coeficientes} | {fila[-1].rjust(anchos[-1])} ]")
    return "\n".join(lineas)
