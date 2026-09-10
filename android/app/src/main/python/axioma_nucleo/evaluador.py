"""Evaluador de expresiones matemáticas.

La versión anterior usaba ``eval()`` sobre el texto que escribía el usuario. Eso
significa que cualquier expresión pegada en la pantalla podía ejecutar código
arbitrario (``__import__('os').system(...)``) y que un simple ``1/0`` mostraba un
mensaje de error de Python en lugar de algo comprensible.

Aquí la expresión se **compila a un árbol de sintaxis** (``ast``) y se recorre
permitiendo únicamente números, operadores aritméticos y una lista blanca de
funciones y constantes. No hay acceso a atributos, nombres, llamadas dinámicas
ni comprensiones, así que no hay forma de salir del sandbox.
"""

from __future__ import annotations

import ast
import math
import operator
import re

__all__ = ["ErrorExpresion", "evaluar", "FUNCIONES", "CONSTANTES", "MODOS_ANGULO"]

MODOS_ANGULO = ("DEG", "RAD", "GRAD")

# Límite para el factorial: 10000! ya tiene 35 660 dígitos y calcularlo dentro de
# una expresión más grande puede congelar la interfaz.
_MAX_FACTORIAL = 10_000


class ErrorExpresion(ValueError):
    """La expresión no es válida o no se puede evaluar."""


# --------------------------------------------------------------------------- #
# Preprocesado del texto
# --------------------------------------------------------------------------- #

_SUSTITUCIONES = {
    "×": "*", "·": "*", "✕": "*", "∗": "*",
    "÷": "/", "∕": "/", "：": "/",
    "−": "-", "–": "-", "—": "-",
    "π": "pi", "τ": "tau", "φ": "phi", "∞": "inf",
    "²": "**2", "³": "**3", "⁴": "**4",
    "≤": "<=", "≥": ">=",
    "^": "**",
}

# Multiplicación implícita: sólo en los casos donde no hay ambigüedad posible.
# Deliberadamente NO se inserta entre dígito y letra, para no romper la notación
# científica (`1e5`) ni nombres de función con cifras (`log10`).
_IMPLICITA = (
    # `2(3+4)`, `2π`, `3√2`. El lookbehind exige que la cifra empiece un token
    # nuevo, para no partir nombres como `log10` o `log2`.
    (re.compile(r"(?<![\w.])(\d+(?:\.\d+)?)\s*(?=[π√∛(])"), r"\1*"),
    # `π2`, `π(...)`, `ππ`.
    (re.compile(r"(π)\s*(?=[\w(π√∛])"), r"\1*"),
    # `(1+2)(3+4)`, `(1+2)3`, `(1+2)x`.
    (re.compile(r"(\))\s*(?=[\w(π√∛])"), r"\1*"),
)

_PORCENTAJE = re.compile(r"(\d+(?:\.\d+)?)\s*%")

# Los símbolos de raíz son prefijos, no nombres: `√9` debe volverse `sqrt(9)` y no
# `sqrt9`, que sería un nombre desconocido.
_PREFIJOS_RAIZ = (("√", "sqrt"), ("∛", "cbrt"))
_OPERANDO_SIMPLE = r"(\d+(?:\.\d+)?|[A-Za-z_]\w*)"


def _preparar(expresion: str) -> str:
    """Normaliza la notación «de calculadora» a sintaxis de Python."""
    texto = expresion.strip()
    if not texto:
        raise ErrorExpresion("Ingrese una expresión")

    for patron, reemplazo in _IMPLICITA:
        texto = patron.sub(reemplazo, texto)

    # `50%` significa 0.5, como en cualquier calculadora. Para el resto (módulo)
    # existe la función `mod(a, b)`.
    texto = _PORCENTAJE.sub(r"(\1/100)", texto)

    for simbolo, funcion in _PREFIJOS_RAIZ:
        texto = re.sub(f"{simbolo}\\s*{_OPERANDO_SIMPLE}", rf"{funcion}(\1)", texto)
        texto = texto.replace(simbolo, funcion)  # queda el caso `√(...)`

    for simbolo, reemplazo in _SUSTITUCIONES.items():
        texto = texto.replace(simbolo, reemplazo)

    texto = _expandir_factoriales(texto)
    return texto


def _expandir_factoriales(texto: str) -> str:
    """Convierte el ``!`` postfijo en llamadas a ``factorial(...)``.

    Recorre el texto de izquierda a derecha; al encontrar un ``!`` busca hacia
    atrás el operando completo (un número, un nombre o un paréntesis
    equilibrado) y lo envuelve.
    """
    resultado = texto
    while True:
        pos = resultado.find("!")
        if pos == -1:
            return resultado
        # `!=` es una comparación, no un factorial.
        if resultado[pos + 1 : pos + 2] == "=":
            siguiente = resultado.find("!", pos + 1)
            if siguiente == -1:
                return resultado
            pos = siguiente

        inicio = _inicio_operando(resultado, pos)
        if inicio is None:
            raise ErrorExpresion("El signo '!' debe ir después de un número")
        operando = resultado[inicio:pos]
        resultado = f"{resultado[:inicio]}factorial({operando}){resultado[pos + 1:]}"


def _inicio_operando(texto: str, fin: int) -> int | None:
    """Índice donde empieza el operando que termina justo antes de ``fin``."""
    i = fin - 1
    while i >= 0 and texto[i].isspace():
        i -= 1
    if i < 0:
        return None

    if texto[i] == ")":
        profundidad = 0
        while i >= 0:
            if texto[i] == ")":
                profundidad += 1
            elif texto[i] == "(":
                profundidad -= 1
                if profundidad == 0:
                    # Incluye el nombre de la función si la hay: `sin(x)!`
                    j = i - 1
                    while j >= 0 and (texto[j].isalnum() or texto[j] == "_"):
                        j -= 1
                    return j + 1
            i -= 1
        return None

    if texto[i].isalnum() or texto[i] in "._":
        while i >= 0 and (texto[i].isalnum() or texto[i] in "._"):
            i -= 1
        return i + 1
    return None


# --------------------------------------------------------------------------- #
# Funciones y constantes permitidas
# --------------------------------------------------------------------------- #


def _factorial(x):
    if isinstance(x, float):
        if not x.is_integer():
            # Para no enteros el factorial se extiende con la función gamma.
            return math.gamma(x + 1)
        x = int(x)
    if x < 0:
        raise ErrorExpresion("El factorial requiere un número no negativo")
    if x > _MAX_FACTORIAL:
        raise ErrorExpresion(f"Factorial demasiado grande (máximo {_MAX_FACTORIAL})")
    return math.factorial(x)


def _raiz(x):
    if x < 0:
        raise ErrorExpresion("La raíz cuadrada de un número negativo no es real")
    return math.sqrt(x)


def _raiz_n(x, n):
    if n == 0:
        raise ErrorExpresion("El índice de la raíz no puede ser 0")
    if x < 0:
        if int(n) == n and int(n) % 2 == 1:
            return -((-x) ** (1.0 / n))
        raise ErrorExpresion("Raíz de índice par de un número negativo")
    return x ** (1.0 / n)


def _log(x, base=None):
    if x <= 0:
        raise ErrorExpresion("El logaritmo requiere un número positivo")
    if base is None:
        return math.log(x)
    if base <= 0 or base == 1:
        raise ErrorExpresion("Base de logaritmo inválida")
    return math.log(x, base)


def _asegurar_dominio(nombre: str, x, minimo: float, maximo: float):
    if not (minimo <= x <= maximo):
        raise ErrorExpresion(f"{nombre} sólo acepta valores entre {minimo} y {maximo}")
    return x


class _Trig:
    """Envuelve las funciones trigonométricas aplicando el modo de ángulo."""

    def __init__(self, modo: str = "RAD") -> None:
        self.modo = modo if modo in MODOS_ANGULO else "RAD"

    def a_radianes(self, valor: float) -> float:
        if self.modo == "DEG":
            return math.radians(valor)
        if self.modo == "GRAD":
            return valor * math.pi / 200.0
        return valor

    def desde_radianes(self, valor: float) -> float:
        if self.modo == "DEG":
            return math.degrees(valor)
        if self.modo == "GRAD":
            return valor * 200.0 / math.pi
        return valor

    def funciones(self) -> dict:
        r, d = self.a_radianes, self.desde_radianes
        return {
            "sin": lambda x: _redondear_ruido(math.sin(r(x))),
            "cos": lambda x: _redondear_ruido(math.cos(r(x))),
            "tan": lambda x: _tan(r(x)),
            "sec": lambda x: _dividir(1.0, math.cos(r(x)), "sec"),
            "csc": lambda x: _dividir(1.0, math.sin(r(x)), "csc"),
            "cot": lambda x: _dividir(1.0, _tan(r(x)), "cot"),
            "asin": lambda x: d(math.asin(_asegurar_dominio("asin", x, -1, 1))),
            "acos": lambda x: d(math.acos(_asegurar_dominio("acos", x, -1, 1))),
            "atan": lambda x: d(math.atan(x)),
            "atan2": lambda y, x: d(math.atan2(y, x)),
            "acot": lambda x: d(math.pi / 2 - math.atan(x)),
        }


def _tan(radianes: float) -> float:
    valor = math.tan(radianes)
    if abs(valor) > 1e15:
        raise ErrorExpresion("La tangente no está definida en ese ángulo")
    return _redondear_ruido(valor)


def _dividir(a: float, b: float, nombre: str) -> float:
    if b == 0 or abs(b) < 1e-15:
        raise ErrorExpresion(f"{nombre} no está definida en ese ángulo")
    return a / b


def _redondear_ruido(valor: float) -> float:
    """Corrige el ruido de coma flotante: ``sin(180°)`` debe dar 0, no 1.2e-16."""
    if abs(valor) < 1e-14:
        return 0.0
    redondeado = round(valor, 12)
    return redondeado if abs(valor - redondeado) < 1e-13 else valor


#: Funciones disponibles en las expresiones (las trigonométricas se añaden según
#: el modo de ángulo activo).
FUNCIONES: dict = {
    "sqrt": _raiz,
    "raiz": _raiz_n,
    "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
    "exp": math.exp,
    "ln": _log,
    "log": lambda x, base=10: _log(x, base),
    "log10": lambda x: _log(x, 10),
    "log2": lambda x: _log(x, 2),
    "abs": abs,
    "sign": lambda x: (x > 0) - (x < 0),
    "floor": math.floor,
    "ceil": math.ceil,
    "trunc": math.trunc,
    "round": lambda x, n=0: round(x, int(n)),
    "factorial": _factorial,
    "gamma": math.gamma,
    "mod": lambda a, b: _modulo(a, b),
    "hypot": math.hypot,
    "gcd": lambda *xs: math.gcd(*(int(x) for x in xs)),
    "lcm": lambda *xs: math.lcm(*(int(x) for x in xs)),
    "min": min,
    "max": max,
    "sinh": math.sinh,
    "cosh": math.cosh,
    "tanh": math.tanh,
    "asinh": math.asinh,
    "acosh": lambda x: math.acosh(x) if x >= 1 else _fuera("acosh requiere x ≥ 1"),
    "atanh": lambda x: math.atanh(x) if -1 < x < 1 else _fuera("atanh requiere -1 < x < 1"),
    "degrees": math.degrees,
    "radians": math.radians,
    "grados": math.degrees,
    "radianes": math.radians,
}

#: Constantes disponibles en las expresiones.
CONSTANTES: dict = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "phi": (1 + math.sqrt(5)) / 2,
    "inf": math.inf,
}


def _fuera(mensaje: str):
    raise ErrorExpresion(mensaje)


def _modulo(a, b):
    if b == 0:
        raise ErrorExpresion("No se puede calcular el módulo con divisor 0")
    return math.fmod(a, b)


# --------------------------------------------------------------------------- #
# Recorrido del árbol
# --------------------------------------------------------------------------- #

_OPERADORES_BINARIOS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_OPERADORES_UNARIOS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

# Cotas para evitar que una expresión bloquee la interfaz: 9**9**9 tardaría
# esencialmente para siempre y agotaría la memoria.
_MAX_EXPONENTE = 1e6
_MAX_BASE_ENTERA = 1e6


class _Evaluador(ast.NodeVisitor):
    def __init__(self, funciones: dict, variables: dict) -> None:
        self.funciones = funciones
        self.variables = variables

    # -- nodos permitidos -------------------------------------------------- #

    def visit_Expression(self, nodo: ast.Expression):
        return self.visit(nodo.body)

    def visit_Constant(self, nodo: ast.Constant):
        if isinstance(nodo.value, bool) or not isinstance(nodo.value, (int, float)):
            raise ErrorExpresion("Sólo se admiten valores numéricos")
        return nodo.value

    def visit_Name(self, nodo: ast.Name):
        nombre = nodo.id
        if nombre in self.variables:
            return self.variables[nombre]
        if nombre in CONSTANTES:
            return CONSTANTES[nombre]
        if nombre in self.funciones:
            raise ErrorExpresion(f"Falta el paréntesis en '{nombre}(...)'")
        raise ErrorExpresion(f"Nombre desconocido: '{nombre}'")

    def visit_BinOp(self, nodo: ast.BinOp):
        operacion = _OPERADORES_BINARIOS.get(type(nodo.op))
        if operacion is None:
            raise ErrorExpresion("Operador no permitido")

        izquierda = self.visit(nodo.left)
        derecha = self.visit(nodo.right)

        if isinstance(nodo.op, ast.Pow):
            return self._potencia(izquierda, derecha)

        if isinstance(nodo.op, (ast.Div, ast.FloorDiv, ast.Mod)) and derecha == 0:
            raise ErrorExpresion("No se puede dividir entre cero")

        try:
            return operacion(izquierda, derecha)
        except OverflowError:
            raise ErrorExpresion("El resultado es demasiado grande") from None
        except (TypeError, ValueError) as e:
            raise ErrorExpresion(f"Operación inválida: {e}") from e

    def visit_UnaryOp(self, nodo: ast.UnaryOp):
        operacion = _OPERADORES_UNARIOS.get(type(nodo.op))
        if operacion is None:
            raise ErrorExpresion("Operador unario no permitido")
        return operacion(self.visit(nodo.operand))

    def visit_Call(self, nodo: ast.Call):
        if not isinstance(nodo.func, ast.Name):
            raise ErrorExpresion("Sólo se pueden llamar funciones por su nombre")
        nombre = nodo.func.id
        funcion = self.funciones.get(nombre)
        if funcion is None:
            raise ErrorExpresion(f"Función desconocida: '{nombre}'")
        if nodo.keywords:
            raise ErrorExpresion("Los argumentos con nombre no están permitidos")

        argumentos = [self.visit(a) for a in nodo.args]
        try:
            return funcion(*argumentos)
        except ErrorExpresion:
            raise
        except TypeError:
            raise ErrorExpresion(f"Número de argumentos incorrecto en '{nombre}'") from None
        except (ValueError, ZeroDivisionError) as e:
            raise ErrorExpresion(f"'{nombre}' no está definida ahí ({e})") from e
        except OverflowError:
            raise ErrorExpresion(f"'{nombre}' produce un resultado demasiado grande") from None

    # -- cualquier otro nodo se rechaza ------------------------------------ #

    def generic_visit(self, nodo: ast.AST):
        raise ErrorExpresion("La expresión contiene elementos no permitidos")

    # -- auxiliares -------------------------------------------------------- #

    @staticmethod
    def _potencia(base, exponente):
        if abs(exponente) > _MAX_EXPONENTE:
            raise ErrorExpresion("Exponente demasiado grande")
        if (
            isinstance(base, int)
            and isinstance(exponente, int)
            and abs(base) > _MAX_BASE_ENTERA
            and exponente > 100
        ):
            raise ErrorExpresion("La potencia produce un número demasiado grande")
        if base < 0 and isinstance(exponente, float) and not float(exponente).is_integer():
            raise ErrorExpresion("Potencia fraccionaria de una base negativa (no real)")
        try:
            resultado = operator.pow(base, exponente)
        except OverflowError:
            raise ErrorExpresion("El resultado es demasiado grande") from None
        except ZeroDivisionError:
            raise ErrorExpresion("0 elevado a un exponente negativo no está definido") from None
        if isinstance(resultado, complex):
            raise ErrorExpresion("El resultado no es un número real")
        return resultado


def evaluar(
    expresion: str,
    modo_angulo: str = "RAD",
    variables: dict | None = None,
) -> float:
    """Evalúa ``expresion`` y devuelve el resultado numérico.

    Args:
        expresion: texto tal cual lo escribió el usuario.
        modo_angulo: ``"DEG"``, ``"RAD"`` o ``"GRAD"``.
        variables: valores extra disponibles, p. ej. ``{"ans": 42}``.

    Raises:
        ErrorExpresion: con un mensaje en castellano apto para mostrar al usuario.
    """
    texto = _preparar(expresion)

    funciones = dict(FUNCIONES)
    funciones.update(_Trig(modo_angulo).funciones())

    try:
        arbol = ast.parse(texto, mode="eval")
    except SyntaxError:
        raise ErrorExpresion("La expresión está mal escrita (revise los paréntesis y operadores)") from None
    except ValueError:
        raise ErrorExpresion("La expresión es demasiado compleja") from None

    resultado = _Evaluador(funciones, dict(variables or {})).visit(arbol)

    if isinstance(resultado, bool) or not isinstance(resultado, (int, float)):
        raise ErrorExpresion("La expresión no produce un número")
    if isinstance(resultado, float) and math.isnan(resultado):
        raise ErrorExpresion("El resultado no está definido")
    return resultado


def parentesis_pendientes(expresion: str) -> int:
    """Cuántos ``)`` faltan para equilibrar la expresión (útil para la interfaz)."""
    abiertos = 0
    for caracter in expresion:
        if caracter == "(":
            abiertos += 1
        elif caracter == ")":
            abiertos = max(0, abiertos - 1)
    return abiertos
