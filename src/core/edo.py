"""Ecuaciones diferenciales ordinarias.

Acepta la notación con prima que se usa en clase (``y' + 2y = e^(-x)``) además
de la de Leibniz (``dy/dx``), la clasifica, la resuelve y comprueba el resultado
sustituyéndolo en la ecuación original.

Se apoya en ``dsolve`` de sympy, que sabe resolver los tipos habituales
(separables, lineales de primer orden, exactas, homogéneas, Bernoulli, lineales
de coeficientes constantes de cualquier orden…). Lo que aporta este módulo es
traducir la entrada, nombrar el método en castellano y presentar el resultado.
"""

from __future__ import annotations

import re

import sympy as sp

from .simbolico import ErrorSimbolico, analizar, texto

__all__ = [
    "ErrorEDO",
    "analizar_edo",
    "clasificar",
    "resolver",
    "resolver_por_laplace",
    "resolver_sistema",
    "campo_direcciones",
    "TIPOS",
]


class ErrorEDO(ErrorSimbolico):
    """La ecuación diferencial no se pudo interpretar o resolver."""


#: Nombre en castellano de cada tipo que devuelve ``classify_ode``.
TIPOS = {
    "separable": "de variables separables",
    "1st_exact": "exacta",
    "1st_linear": "lineal de primer orden",
    "Bernoulli": "de Bernoulli",
    "1st_homogeneous_coeff_best": "homogénea",
    "1st_homogeneous_coeff_subs_dep_div_indep": "homogénea",
    "1st_homogeneous_coeff_subs_indep_div_dep": "homogénea",
    "1st_rational_riccati": "de Riccati",
    "almost_linear": "casi lineal",
    "linear_coefficients": "de coeficientes lineales",
    "nth_linear_constant_coeff_homogeneous":
        "lineal homogénea de coeficientes constantes",
    "nth_linear_constant_coeff_undetermined_coefficients":
        "lineal de coeficientes constantes (coeficientes indeterminados)",
    "nth_linear_constant_coeff_variation_of_parameters":
        "lineal de coeficientes constantes (variación de parámetros)",
    "nth_linear_euler_eq_homogeneous": "de Euler-Cauchy homogénea",
    "nth_linear_euler_eq_nonhomogeneous_undetermined_coefficients":
        "de Euler-Cauchy no homogénea",
    "nth_algebraic": "algebraica",
    "factorable": "factorizable",
    "lie_group": "resoluble por grupos de Lie",
    "2nd_power_series_ordinary": "por series de potencias",
    "nth_order_reducible": "de orden reducible",
    "Liouville": "de Liouville",
}

#: Clasificaciones ciertas pero que no orientan sobre el método a seguir.
_POCO_INFORMATIVOS = {"factorizable", "algebraica", "de orden reducible",
                      "resoluble por grupos de Lie", "por series de potencias"}

#: Tope de orden: por encima, dsolve tarda demasiado para una interfaz.
MAX_ORDEN = 6

# Ojo con `\b`: en «2y» no hay frontera de palabra entre el dígito y la letra,
# porque ambos son caracteres de palabra. Hay que mirar explícitamente que no
# venga precedido de otra letra.
_PRIMAS = re.compile(r"(?<![A-Za-z_])([a-zA-Z])('+)")
_LEIBNIZ = re.compile(
    r"(?<![A-Za-z_])d(\d*)\s*([a-zA-Z])\s*/\s*d\s*([a-zA-Z])\s*(?:\^(\d+))?"
)


def _patron_variable(nombre: str) -> re.Pattern:
    """Casa la variable suelta, incluso pegada a un número («2y»)."""
    return re.compile(rf"(?<![A-Za-z_]){nombre}(?![A-Za-z_0-9])(?!\s*\()")


def _preparar(texto_edo: str, dependiente: str, independiente: str) -> str:
    """Traduce la notación de clase a llamadas explícitas a Derivative."""
    resultado = texto_edo.strip()
    if not resultado:
        raise ErrorEDO("Introduzca una ecuación diferencial")

    # d2y/dx2  ·  dy/dx  ·  d^2y/dx^2
    def leibniz(coincidencia: re.Match) -> str:
        orden = coincidencia.group(1) or coincidencia.group(4) or "1"
        dep, indep = coincidencia.group(2), coincidencia.group(3)
        return f"Derivative({dep}({indep}), {indep}, {orden})"

    resultado = _LEIBNIZ.sub(leibniz, resultado)

    # y'  ·  y''  ·  y'''
    def primas(coincidencia: re.Match) -> str:
        nombre, comillas = coincidencia.group(1), coincidencia.group(2)
        if nombre != dependiente:
            return coincidencia.group(0)
        return f"Derivative({nombre}({independiente}), {independiente}, {len(comillas)})"

    resultado = _PRIMAS.sub(primas, resultado)

    # La `y` suelta pasa a ser `y(x)`, pero sin tocar la que ya está aplicada
    # ni la que forma parte de otro identificador.
    resultado = _patron_variable(dependiente).sub(
        f"{dependiente}({independiente})", resultado
    )
    return resultado


def analizar_edo(texto_edo: str, dependiente: str = "y",
                 independiente: str = "x") -> tuple[sp.Eq, sp.Function, sp.Symbol]:
    """Convierte el texto en una ecuación de sympy, su función y su variable."""
    if len(dependiente) != 1 or len(independiente) != 1:
        raise ErrorEDO("Las variables deben ser una sola letra")
    if dependiente == independiente:
        raise ErrorEDO("La función y la variable no pueden llamarse igual")

    preparado = _preparar(texto_edo, dependiente, independiente)

    izquierda, signo, derecha = preparado.partition("=")
    if not signo:
        derecha = "0"
    if not derecha.strip():
        derecha = "0"

    # Declarar `y` como función es imprescindible: sin ello, la multiplicación
    # implícita del analizador interpreta `y(x)` como `y·x`.
    locales = {
        dependiente: sp.Function(dependiente),
        independiente: sp.Symbol(independiente),
        "Derivative": sp.Derivative,
    }
    try:
        permitidas = frozenset({"Derivative", dependiente, independiente})
        expr_izq = analizar(izquierda, permitidas, locales)
        expr_der = analizar(derecha, permitidas, locales)
    except ErrorSimbolico as e:
        raise ErrorEDO(
            f"No se entiende la ecuación: {e}. Escriba la derivada como «y'» o "
            f"«dy/dx»."
        ) from None

    x = sp.Symbol(independiente)
    y = sp.Function(dependiente)
    ecuacion = sp.Eq(expr_izq, expr_der)

    if not ecuacion.has(sp.Derivative):
        raise ErrorEDO(
            "No hay ninguna derivada: esto no es una ecuación diferencial. "
            "Use el módulo «Ecuaciones» para las ecuaciones normales."
        )

    orden = sp.ode_order(ecuacion, y(x))
    if orden > MAX_ORDEN:
        raise ErrorEDO(f"Orden {orden}: el máximo admitido es {MAX_ORDEN}")

    return ecuacion, y, x


def clasificar(ecuacion: sp.Eq, y: sp.Function, x: sp.Symbol) -> list[tuple[str, str]]:
    """Orden, linealidad y métodos aplicables."""
    filas: list[tuple[str, str]] = []
    orden = sp.ode_order(ecuacion, y(x))
    filas.append(("Orden", str(orden)))

    try:
        tipos = sp.classify_ode(ecuacion, y(x))
    except (NotImplementedError, ValueError, TypeError):
        tipos = ()

    nombres = []
    for tipo in tipos:
        # sympy añade sufijos como «_Integral» a variantes del mismo método.
        base = tipo.replace("_Integral", "")
        nombre = TIPOS.get(base)
        if nombre and nombre not in nombres:
            nombres.append(nombre)

    # sympy suele poner «factorizable» o «algebraica» primero, que son ciertas
    # pero no dicen nada útil. Se dejan para el final.
    nombres.sort(key=lambda n: n in _POCO_INFORMATIVOS)

    if nombres:
        filas.append(("Tipo", nombres[0]))
        if len(nombres) > 1:
            filas.append(("También se puede resolver como", ", ".join(nombres[1:4])))
    else:
        filas.append(("Tipo", "no reconocido entre los métodos habituales"))

    lineal = any("linear" in t for t in tipos)
    filas.append(("Linealidad", "lineal" if lineal else "no lineal"))
    return filas


def _condiciones(texto_condiciones: str, y: sp.Function,
                 x: sp.Symbol) -> dict:
    """Interpreta «y(0)=1, y'(0)=0» como el diccionario que espera dsolve."""
    if not texto_condiciones.strip():
        return {}

    condiciones = {}
    for trozo in texto_condiciones.replace(";", ",").split(","):
        trozo = trozo.strip()
        if not trozo:
            continue
        if "=" not in trozo:
            raise ErrorEDO(f"Falta el «=» en la condición «{trozo}»")

        izquierda, _, derecha = trozo.partition("=")
        izquierda = izquierda.strip()
        try:
            valor = analizar(derecha)
        except ErrorSimbolico as e:
            raise ErrorEDO(f"Valor inválido en la condición «{trozo}»: {e}") from None

        # y(0)=1  o  y'(0)=2
        coincidencia = re.fullmatch(rf"{y.__name__}('*)\s*\(\s*([^)]+)\s*\)",
                                    izquierda)
        if not coincidencia:
            raise ErrorEDO(
                f"No se entiende la condición «{trozo}». Escríbala como "
                f"«{y.__name__}(0) = 1» o «{y.__name__}'(0) = 0»."
            )
        primas = len(coincidencia.group(1))
        try:
            punto = analizar(coincidencia.group(2))
        except ErrorSimbolico:
            raise ErrorEDO(f"Punto inválido en la condición «{trozo}»") from None

        if primas == 0:
            condiciones[y(punto)] = valor
        else:
            condiciones[sp.Derivative(y(x), x, primas).subs(x, punto)] = valor

    return condiciones


def resolver(texto_edo: str, texto_condiciones: str = "", dependiente: str = "y",
             independiente: str = "x") -> list[tuple[str, str]]:
    """Resuelve la ecuación y comprueba el resultado."""
    ecuacion, y, x = analizar_edo(texto_edo, dependiente, independiente)

    filas: list[tuple[str, str]] = [
        ("Ecuación", texto(ecuacion)),
    ]
    filas.extend(clasificar(ecuacion, y, x))
    filas.append(("", ""))

    condiciones = _condiciones(texto_condiciones, y, x)

    try:
        solucion = sp.dsolve(ecuacion, y(x), ics=condiciones or None)
    except (NotImplementedError, ValueError, TypeError, AttributeError) as e:
        raise ErrorEDO(
            f"sympy no sabe resolver esta ecuación con sus métodos ({e}). "
            f"Puede probar el módulo «Numérico», que la resuelve por "
            f"aproximación con Euler o Runge-Kutta."
        ) from None
    except Exception as e:  # dsolve lanza tipos muy variados
        raise ErrorEDO(f"No se pudo resolver: {type(e).__name__}: {e}") from None

    soluciones = solucion if isinstance(solucion, (list, tuple)) else [solucion]

    etiqueta = "Solución particular" if condiciones else "Solución general"
    for i, sol in enumerate(soluciones, 1):
        sufijo = f" {i}" if len(soluciones) > 1 else ""
        filas.append((etiqueta + sufijo, texto(sp.simplify(sol))))

    if not condiciones:
        constantes = sorted({str(s) for sol in soluciones
                             for s in sol.free_symbols if str(s).startswith("C")})
        if constantes:
            filas.append((
                "Constantes de integración",
                f"{', '.join(constantes)} — se determinan con las condiciones iniciales",
            ))

    filas.append(("", ""))
    filas.append(("Comprobación", _comprobar(ecuacion, soluciones, y, x)))
    return filas


def _comprobar(ecuacion: sp.Eq, soluciones: list, y: sp.Function,
               x: sp.Symbol) -> str:
    """Sustituye cada solución en la ecuación original."""
    correctas = 0
    for sol in soluciones:
        try:
            resultado = sp.checkodesol(ecuacion, sol, func=y(x))
        except (NotImplementedError, ValueError, TypeError):
            return "no se pudo comprobar automáticamente"
        if isinstance(resultado, tuple) and resultado[0]:
            correctas += 1
        elif isinstance(resultado, list) and all(r[0] for r in resultado):
            correctas += 1

    if correctas == len(soluciones):
        return "correcta: al sustituirla, la ecuación se cumple"
    if correctas:
        return f"{correctas} de {len(soluciones)} soluciones verificadas"
    return "no se pudo verificar"


def resolver_por_laplace(texto_edo: str, texto_condiciones: str,
                         dependiente: str = "y",
                         independiente: str = "t") -> list[tuple[str, str]]:
    """Resuelve un problema de valor inicial con la transformada de Laplace.

    Es como se enseña en ingeniería: transformar, despejar Y(s) y antitransformar.
    """
    ecuacion, y, t = analizar_edo(texto_edo, dependiente, independiente)
    condiciones = _condiciones(texto_condiciones, y, t)

    if not condiciones:
        raise ErrorEDO(
            "El método de Laplace necesita condiciones iniciales en 0, "
            "por ejemplo «y(0) = 1»."
        )

    filas: list[tuple[str, str]] = [
        ("Ecuación", texto(ecuacion)),
        ("Condiciones iniciales",
         ", ".join(f"{texto(k)} = {texto(v)}" for k, v in condiciones.items())),
        ("", ""),
        ("Método",
         "Se aplica L{·} a los dos lados, se despeja Y(s) y se antitransforma."),
    ]

    try:
        solucion = sp.dsolve(ecuacion, y(t), ics=condiciones, hint="default")
    except Exception as e:
        raise ErrorEDO(f"No se pudo resolver: {e}") from None

    # La transformada de la incógnita, para mostrar el paso intermedio.
    s = sp.Symbol("s")
    try:
        derecha = sp.laplace_transform(ecuacion.rhs, t, s, noconds=True)
        filas.append(("Transformada del término independiente", texto(derecha)))
    except Exception:
        pass

    filas.append(("", ""))
    filas.append(("Solución", texto(sp.simplify(solucion))))
    return filas


def resolver_sistema(lineas: list[str], independiente: str = "t") -> list[tuple[str, str]]:
    """Resuelve un sistema de ecuaciones diferenciales de primer orden."""
    validas = [l.strip() for l in lineas if l.strip()]
    if len(validas) < 2:
        raise ErrorEDO("Escriba al menos dos ecuaciones")
    if len(validas) > 4:
        raise ErrorEDO("El máximo admitido son 4 ecuaciones")

    t = sp.Symbol(independiente)
    ecuaciones = []
    funciones = []

    for numero, linea in enumerate(validas, 1):
        # Se detecta la función de cada ecuación por la prima que lleve.
        coincidencia = re.search(r"\b([a-zA-Z])'", linea)
        if not coincidencia:
            raise ErrorEDO(
                f"La ecuación {numero} no tiene ninguna derivada. Escríbala "
                f"como «x' = ...»."
            )
        nombre = coincidencia.group(1)

        preparado = linea
        # Todas las funciones del sistema pasan a estar aplicadas en t.
        for otra in set(re.findall(r"(?<![A-Za-z_])([a-zA-Z])(?![A-Za-z_0-9])", linea)):
            if otra == independiente:
                continue
            preparado = re.sub(rf"(?<![A-Za-z_]){otra}'",
                               f"Derivative({otra}({t}), {t})", preparado)
            preparado = _patron_variable(otra).sub(f"{otra}({t})", preparado)

        izquierda, _, derecha = preparado.partition("=")
        letras = set(re.findall(r"\b([a-zA-Z])\b", linea)) - {independiente}
        permitidas = frozenset({"Derivative", independiente} | letras)
        locales = {n: sp.Function(n) for n in letras}
        locales[independiente] = t
        locales["Derivative"] = sp.Derivative
        try:
            ecuaciones.append(sp.Eq(analizar(izquierda, permitidas, locales),
                                    analizar(derecha or "0", permitidas, locales)))
        except ErrorSimbolico as e:
            raise ErrorEDO(f"No se entiende la ecuación {numero}: {e}") from None
        funciones.append(sp.Function(nombre)(t))

    filas: list[tuple[str, str]] = [("Sistema", "")]
    for i, ecuacion in enumerate(ecuaciones, 1):
        filas.append((f"  ({i})", texto(ecuacion)))
    filas.append(("", ""))

    try:
        solucion = sp.dsolve(ecuaciones, funciones)
    except Exception as e:
        raise ErrorEDO(
            f"No se pudo resolver el sistema ({type(e).__name__}: {e})"
        ) from None

    soluciones = solucion if isinstance(solucion, (list, tuple)) else [solucion]
    for sol in soluciones:
        filas.append(("Solución", texto(sp.simplify(sol))))
    return filas


def campo_direcciones(texto_edo: str, dependiente: str = "y",
                      independiente: str = "x"):
    """Devuelve y′ = f(x, y) despejada, para dibujar el campo de direcciones.

    Sólo tiene sentido en ecuaciones de primer orden.
    """
    ecuacion, y, x = analizar_edo(texto_edo, dependiente, independiente)
    if sp.ode_order(ecuacion, y(x)) != 1:
        raise ErrorEDO("El campo de direcciones sólo se dibuja en las de primer orden")

    derivada = sp.Derivative(y(x), x)
    try:
        despejada = sp.solve(ecuacion, derivada)
    except (NotImplementedError, ValueError, TypeError):
        despejada = []
    if not despejada:
        raise ErrorEDO("No se pudo despejar la derivada")

    simbolo_y = sp.Symbol(dependiente)
    pendiente = despejada[0].subs(y(x), simbolo_y)
    return sp.lambdify((x, simbolo_y), pendiente, "numpy"), texto(pendiente)
