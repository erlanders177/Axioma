"""Paso a paso de las cuentas, de la geometría y de las conversiones.

Complementa a :mod:`pasos`, que ya explica ecuaciones, derivadas, integrales y
sistemas. Aquí va lo de todos los días:

* **Cuentas**: sumar fracciones con común denominador, simplificar, sacar
  factores de una raíz (√72 = √(36·2) = 6√2), racionalizar, potencias de una
  fracción, valores notables de seno y coseno…
* **Geometría**: la fórmula, los datos sustituidos y el resultado.
* **Conversiones**: por qué número se multiplica y de dónde sale.

Todo sale de sympy con valores exactos, y el resultado final se contrasta con
el cálculo de siempre (:func:`exacto.calcular`): si no coinciden, no se enseña
un desarrollo que llega a otro número.
"""

from __future__ import annotations

import ast
import math
import re

import sympy as sp

from . import exacto
from . import exacto_sympy as simb
from .evaluador import ErrorExpresion, _preparar
from .formato import formatear
from .pasos import Paso, _Acumulador

__all__ = ["pasos_expresion", "pasos_figura", "pasos_conversion"]

#: Un desarrollo de cuarenta pasos ya no ayuda a nadie.
_MAXIMO_PASOS = 25


def _t(valor) -> str:
    return simb.a_texto(valor)


def _unir_suma(valores: list) -> str:
    """«1/3 + 1/6 − 1/2», con los signos donde tocan."""
    partes = []
    for i, valor in enumerate(valores):
        if i and valor.could_extract_minus_sign():
            partes.append(" − " + _con_parentesis(-valor))
        elif i:
            partes.append(" + " + _con_parentesis(valor))
        else:
            partes.append(_t(valor))
    return "".join(partes)


def _con_parentesis(valor) -> str:
    texto = _t(valor)
    return f"({texto})" if isinstance(valor, sp.Add) else texto


def _factor(valor) -> str:
    """Un factor dentro de un producto: entre paréntesis si hace falta."""
    texto = _t(valor)
    if isinstance(valor, sp.Add) or valor.could_extract_minus_sign() or "/" in texto:
        return f"({texto})"
    return texto


# --------------------------------------------------------------------------- #
# Raíces
# --------------------------------------------------------------------------- #

def _mayor_factor_potencia(n: int, indice: int) -> int:
    """El mayor k tal que k^indice divide a n (72 → 6 para la raíz cuadrada)."""
    mayor = 1
    for primo, veces in sp.factorint(n).items():
        mayor *= primo ** (veces // indice)
    return mayor


def _pasos_raiz(radicando, indice: int, acc: _Acumulador) -> sp.Expr:
    """√n explicada: fuera los factores que se puedan sacar."""
    simbolo = {2: "√", 3: "∛", 4: "∜"}.get(indice, f"{indice}√")
    resultado = sp.real_root(radicando, indice) if indice % 2 else sp.root(radicando, indice)

    if radicando.is_Integer and radicando > 0:
        n = int(radicando)
        k = _mayor_factor_potencia(n, indice)
        if k == 1:
            return resultado                        # √2: no hay nada que sacar
        resto = n // k ** indice
        potencia = k ** indice
        if resto == 1:
            acc.add("Raíz exacta", f"{potencia} = {k}{_elevado(indice)}",
                    f"{simbolo}{n} = {k}")
        else:
            acc.add("Sacamos factores de la raíz",
                    f"{n} = {potencia}·{resto}, y {potencia} = {k}{_elevado(indice)}",
                    f"{simbolo}{n} = {simbolo}({potencia}·{resto}) = "
                    f"{simbolo}{potencia}·{simbolo}{resto} = {k}{simbolo}{resto}")
        return resultado

    if radicando.is_Rational and radicando > 0 and radicando.q != 1:
        arriba, abajo = sp.Integer(radicando.p), sp.Integer(radicando.q)
        acc.add("La raíz de una fracción es la fracción de las raíces", "",
                f"{simbolo}({_t(radicando)}) = {simbolo}{arriba}/{simbolo}{abajo}")
        _pasos_raiz(arriba, indice, acc)
        _pasos_raiz(abajo, indice, acc)
        if simb.a_texto(resultado) != f"{simbolo}{arriba}/{simbolo}{abajo}":
            acc.add("Queda", "", f"{simbolo}({_t(radicando)}) = {_t(resultado)}")
        return resultado

    if _t(resultado) != f"{simbolo}({_t(radicando)})":
        acc.add("Calculamos la raíz", "", f"{simbolo}({_t(radicando)}) = {_t(resultado)}")
    return resultado


_SUPER = str.maketrans("0123456789-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁻")


def _elevado(n: int) -> str:
    return str(n).translate(_SUPER)


# --------------------------------------------------------------------------- #
# El recorrido
# --------------------------------------------------------------------------- #

class _Cuenta:
    """Recorre la cuenta tal como se escribió, operando y anotando lo que hace.

    Se recorre el árbol de Python y no el de sympy porque sympy reagrupa al
    leer: «2/3 · 9/4» le llega como 2·9/(3·4). La explicación tiene que seguir
    la cuenta que escribió el usuario, no otra equivalente.
    """

    def __init__(self, acc: _Acumulador, modo: str, nombres: dict) -> None:
        self.acc = acc
        self.nombres = nombres
        self.a_rad = {"DEG": sp.pi / 180, "GRAD": sp.pi / 200}.get(modo, sp.Integer(1))
        self.unidad = {"DEG": "°", "GRAD": "ᵍ"}.get(modo, "")

    # -- el árbol -------------------------------------------------------------- #

    def valor(self, nodo):
        if isinstance(nodo, ast.Expression):
            return self.valor(nodo.body)
        if isinstance(nodo, ast.Constant):
            if isinstance(nodo.value, bool) or not isinstance(nodo.value, (int, float)):
                raise ErrorExpresion("Hay algo que no es un número")
            if isinstance(nodo.value, int):
                return sp.Integer(nodo.value)
            return sp.Rational(repr(nodo.value))          # 0.1 es 1/10, exacto
        if isinstance(nodo, ast.Name):
            valor = self.nombres.get(nodo.id)
            if valor is None or callable(valor):
                raise ErrorExpresion(f"No se reconoce «{nodo.id}»")
            return valor
        if isinstance(nodo, ast.UnaryOp) and isinstance(nodo.op, (ast.USub, ast.UAdd)):
            valor = self.valor(nodo.operand)
            return -valor if isinstance(nodo.op, ast.USub) else valor
        if isinstance(nodo, ast.BinOp):
            if isinstance(nodo.op, (ast.Add, ast.Sub)):
                return self._suma(nodo)
            if isinstance(nodo.op, ast.Mult):
                return self._producto(nodo)
            if isinstance(nodo.op, ast.Div):
                return self._division(nodo)
            if isinstance(nodo.op, ast.Pow):
                return self._potencia(nodo)
        if isinstance(nodo, ast.Call):
            return self._llamada(nodo)
        raise ErrorExpresion("Esta cuenta no se puede desarrollar paso a paso")

    # -- sumas y restas -------------------------------------------------------- #

    def _terminos(self, nodo, signo: int = 1) -> list:
        """Aplana a + b − c en una lista de (signo, nodo): es una sola suma."""
        if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, (ast.Add, ast.Sub)):
            derecho = signo if isinstance(nodo.op, ast.Add) else -signo
            return self._terminos(nodo.left, signo) + self._terminos(nodo.right, derecho)
        return [(signo, nodo)]

    def _suma(self, nodo):
        valores = [signo * self.valor(n) for signo, n in self._terminos(nodo)]
        resultado = sp.Add(*valores)

        if all(v.is_Rational for v in valores):
            if any(v.q != 1 for v in valores):
                self._sumar_fracciones(valores, resultado)
        else:
            antes, despues = _unir_suma(valores), _t(resultado)
            if len(sp.Add.make_args(resultado)) < len(valores) and despues != antes:
                self.acc.add("Agrupamos términos semejantes", "", f"{antes} = {despues}")
        return resultado

    def _sumar_fracciones(self, valores: list, resultado) -> None:
        denominadores = [int(v.q) for v in valores]
        comun = math.lcm(*denominadores)
        numeradores = [int(v.p) * (comun // int(v.q)) for v in valores]

        if len(set(denominadores)) > 1:
            ampliadas = " + ".join(f"{n}/{comun}" for n in numeradores).replace("+ -", "− ")
            self.acc.add("Buscamos un denominador común",
                         f"m.c.m.({', '.join(map(str, sorted(set(denominadores))))}) = {comun}",
                         f"{_unir_suma(valores)} = {ampliadas}")
        suma = sum(numeradores)
        cuentas = " + ".join(str(n) for n in numeradores).replace("+ -", "− ")
        self.acc.add("Sumamos los numeradores", "", f"({cuentas})/{comun} = {suma}/{comun}")

        divisor = math.gcd(suma, comun)
        if divisor > 1 and suma:
            self.acc.add("Simplificamos", f"dividimos arriba y abajo entre {divisor}",
                         f"{suma}/{comun} = {_t(resultado)}")

    # -- productos ------------------------------------------------------------- #

    def _factores(self, nodo) -> list:
        if isinstance(nodo, ast.BinOp) and isinstance(nodo.op, ast.Mult):
            return self._factores(nodo.left) + self._factores(nodo.right)
        return [nodo]

    def _producto(self, nodo):
        valores = [self.valor(n) for n in self._factores(nodo)]
        resultado = sp.Mul(*valores)
        if all(v.is_Rational for v in valores):
            if any(v.q != 1 for v in valores):
                self._multiplicar_fracciones(valores, resultado)
        elif any(_tiene_raiz(v) for v in valores):
            antes = "·".join(_factor(v) for v in valores)
            despues = _t(resultado)
            if despues != antes:
                self.acc.add("Multiplicamos", "", f"{antes} = {despues}")
        return resultado

    def _multiplicar_fracciones(self, valores: list, resultado) -> None:
        arriba = [sp.Integer(v.p) for v in valores]
        # Un entero no aporta denominador: «(2·9)/3», no «(2·9)/(3·1)».
        abajo = [sp.Integer(v.q) for v in valores if v.q != 1] or [sp.Integer(1)]
        producto_arriba, producto_abajo = sp.Mul(*arriba), sp.Mul(*abajo)
        self.acc.add("Multiplicamos numeradores y denominadores", "",
                     f"{' · '.join(_factor(v) for v in valores)} = "
                     f"{_agrupar(arriba)}/{_agrupar(abajo)} = "
                     f"{producto_arriba}/{producto_abajo}")
        divisor = math.gcd(int(producto_arriba), int(producto_abajo))
        if divisor > 1 and producto_arriba:
            self.acc.add("Simplificamos", f"dividimos arriba y abajo entre {divisor}",
                         f"{producto_arriba}/{producto_abajo} = {_t(resultado)}")

    # -- divisiones ------------------------------------------------------------ #

    def _division(self, nodo):
        arriba, abajo = self.valor(nodo.left), self.valor(nodo.right)
        if abajo == 0:
            raise ErrorExpresion("No se puede dividir entre cero")
        resultado = arriba / abajo

        # Escribir una fracción («6/8»): si se puede simplificar, se dice.
        if arriba.is_Integer and abajo.is_Integer:
            divisor = math.gcd(int(arriba), int(abajo))
            if divisor > 1 and abs(int(abajo)) != divisor and arriba:
                self.acc.add("Simplificamos la fracción",
                             f"dividimos arriba y abajo entre {divisor}",
                             f"{arriba}/{abajo} = {_t(resultado)}")
            return resultado

        if arriba.is_Rational and abajo.is_Rational:
            inversa = 1 / abajo
            self.acc.add("Dividir es multiplicar por la inversa", "",
                         f"{_factor(arriba)} ÷ {_factor(abajo)} = "
                         f"{_factor(arriba)} · {_factor(inversa)}")
            self._multiplicar_fracciones([arriba, inversa], resultado)
            return resultado

        if _tiene_raiz(abajo):
            return self._racionalizar(arriba, abajo, resultado)
        elif _t(resultado) != f"{_factor(arriba)}/{_factor(abajo)}":
            self.acc.add("Dividimos", "",
                         f"{_factor(arriba)} ÷ {_factor(abajo)} = {_t(resultado)}")
        return resultado

    def _racionalizar(self, numerador, denominador, resultado):
        """Quita la raíz del denominador y devuelve el resultado ya limpio."""
        antes = f"{_con_parentesis(numerador)}/{_con_parentesis(denominador)}"
        if isinstance(denominador, sp.Add) and len(denominador.args) == 2:
            a, b = _terminos_ordenados(denominador)
            conjugado = a - b
            razon = f"multiplicamos arriba y abajo por el conjugado, {_t(conjugado)}"
        else:
            conjugado = _parte_radical(denominador)
            razon = f"multiplicamos arriba y abajo por {_t(conjugado)}"
        nuevo_arriba = sp.expand(numerador * conjugado)
        nuevo_abajo = sp.expand(denominador * conjugado)
        limpio = simb._mas_legible(sp.radsimp(resultado))

        linea = (f"{antes} = ({_factor(numerador)}·{_factor(conjugado)})/"
                 f"({_factor(denominador)}·{_factor(conjugado)}) = "
                 f"{_con_parentesis(nuevo_arriba)}/{_factor(nuevo_abajo)}")
        if _t(limpio) != f"{_con_parentesis(nuevo_arriba)}/{_factor(nuevo_abajo)}":
            linea += f" = {_t(limpio)}"
        self.acc.add("Quitamos la raíz del denominador", razon, linea)
        return limpio

    # -- potencias ------------------------------------------------------------- #

    def _potencia(self, nodo):
        base, exponente = self.valor(nodo.left), self.valor(nodo.right)

        if exponente.is_Rational and exponente.q > 1 and exponente.p == 1:
            return _pasos_raiz(base, int(exponente.q), self.acc)

        resultado = base ** exponente
        if exponente.is_Integer and exponente < 0:
            self.acc.add("Exponente negativo: se da la vuelta", "",
                         f"{_factor(base)}{_elevado(int(exponente))} = "
                         f"1/{_factor(base)}{_elevado(int(-exponente))} = {_t(resultado)}")
        elif exponente.is_Integer and base.is_Rational and base.q != 1:
            n = int(exponente)
            self.acc.add("Se eleva arriba y abajo", "",
                         f"({_t(base)}){_elevado(n)} = {abs(base.p)}{_elevado(n)}/"
                         f"{base.q}{_elevado(n)} = {_t(resultado)}")
        elif (exponente.is_Integer and base.is_Integer and 1 < exponente <= 4
              and 0 < abs(base) <= 20):
            n = int(exponente)
            producto = "·".join([_factor(base)] * n)
            self.acc.add("Potencia", "",
                         f"{_factor(base)}{_elevado(n)} = {producto} = {_t(resultado)}")
        elif exponente.is_Integer and _tiene_raiz(base):
            self.acc.add("Potencia de una raíz", "",
                         f"({_t(base)}){_elevado(int(exponente))} = {_t(resultado)}")
        return resultado

    # -- funciones ------------------------------------------------------------- #

    def _llamada(self, nodo):
        if not isinstance(nodo.func, ast.Name) or nodo.keywords:
            raise ErrorExpresion("Esta cuenta no se puede desarrollar paso a paso")
        nombre = nodo.func.id
        argumentos = [self.valor(a) for a in nodo.args]
        texto_args = ", ".join(_t(a) for a in argumentos)

        if nombre in ("sin", "cos", "tan"):
            funcion = {"sin": sp.sin, "cos": sp.cos, "tan": sp.tan}[nombre]
            resultado = funcion(argumentos[0] * self.a_rad)
            if resultado.has(sp.zoo):
                raise ErrorExpresion(f"{nombre}({texto_args}{self.unidad}) no existe")
            self._anotar(f"{nombre}({texto_args}{self.unidad})", resultado, "Valor notable")
            return resultado

        if nombre in ("asin", "acos", "atan"):
            funcion = {"asin": sp.asin, "acos": sp.acos, "atan": sp.atan}[nombre]
            resultado = funcion(argumentos[0]) / self.a_rad
            sufijo = self.unidad if simb.presentable(resultado) else ""
            self._anotar(f"{nombre}({texto_args})", resultado, "Ángulo notable", sufijo)
            return resultado

        if nombre in ("sqrt", "cbrt", "raiz"):
            indice = {"sqrt": 2, "cbrt": 3}.get(nombre)
            if indice is None:
                indice = int(argumentos[1])
            return _pasos_raiz(argumentos[0], indice, self.acc)

        if nombre == "factorial":
            x = argumentos[0]
            if x.is_integer and x > 10_000:
                raise ErrorExpresion("El factorial está limitado a 10000!")
            resultado = sp.factorial(x)
            if x.is_Integer and 1 < x <= 6:
                producto = "·".join(str(i) for i in range(int(x), 0, -1))
                self.acc.add("Factorial", "", f"{_t(x)}! = {producto} = {_t(resultado)}")
            else:
                self._anotar(f"{_t(x)}!", resultado, "Factorial")
            return resultado

        funcion = self.nombres.get(nombre)
        if not callable(funcion):
            raise ErrorExpresion(f"No se reconoce «{nombre}»")
        resultado = funcion(*argumentos)
        titulos = {"ln": "Logaritmo", "log": "Logaritmo", "log10": "Logaritmo",
                   "log2": "Logaritmo", "abs": "Valor absoluto"}
        self._anotar(f"{nombre}({texto_args})", resultado, titulos.get(nombre, "Calculamos"))
        return resultado

    def _anotar(self, llamada: str, resultado, titulo: str, sufijo: str = "") -> None:
        if simb.presentable(resultado):
            self.acc.add(titulo, "", f"{llamada} = {_t(resultado)}{sufijo}")
            return
        try:
            aproximado = formatear(float(resultado.evalf(20)), 6)
        except (TypeError, ValueError):
            return
        self.acc.add("Calculamos", "No tiene una forma exacta sencilla",
                     f"{llamada} ≈ {aproximado}")


def _terminos_ordenados(suma) -> tuple:
    """Los dos términos de a + b√n, con el de la raíz el segundo."""
    a, b = suma.args
    return (b, a) if _tiene_raiz(a) and not _tiene_raiz(b) else (a, b)


def _parte_radical(valor):
    """De 3√2 se queda con √2, que es por lo que hay que multiplicar."""
    for factor in sp.Mul.make_args(valor):
        if isinstance(factor, sp.Pow) and factor.exp.is_Rational and factor.exp.q > 1:
            return factor
    return valor


def _agrupar(factores: list) -> str:
    """«(2·9)» si son varios, «3» si es uno: sin paréntesis de sobra."""
    texto = "·".join(_factor(v) for v in factores)
    return f"({texto})" if len(factores) > 1 else texto


def _tiene_raiz(valor) -> bool:
    return any(isinstance(n, sp.Pow) and n.exp.is_Rational and n.exp.q > 1
               for n in sp.preorder_traversal(valor))


# --------------------------------------------------------------------------- #
# Cuentas de la calculadora
# --------------------------------------------------------------------------- #

_DECIMAL = re.compile(r"(?<![\w.])(\d+\.\d+)(?![\w.])")


def pasos_expresion(texto: str, modo: str = "DEG", entorno: dict | None = None,
                    decimales: int = 6) -> list[Paso]:
    """El desarrollo de una cuenta, hasta el resultado exacto."""
    resultado = exacto.calcular(texto, modo, entorno, decimales)   # errores, aquí
    acc = _Acumulador()

    decimales_escritos = _DECIMAL.findall(texto)
    if decimales_escritos and resultado.exacto:
        conversiones = [f"{d} = {_t(sp.Rational(d))}" for d in dict.fromkeys(decimales_escritos)]
        acc.add("Escribimos los decimales como fracciones", "", ",  ".join(conversiones))

    cuenta = _Cuenta(acc, modo, simb._nombres(modo, entorno))
    try:
        valor = cuenta.valor(ast.parse(_preparar(texto), mode="eval"))
    except (ErrorExpresion, SyntaxError, ValueError, TypeError, ZeroDivisionError):
        valor = None

    final = Paso("Resultado", "",
                 f"{resultado.exacto}   ≈ {resultado.decimal}" if resultado.tiene_exacto
                 else (resultado.exacto or resultado.decimal))

    # Si el desarrollo no llega al mismo número, mejor no enseñarlo.
    if valor is None:
        return [final]
    try:
        coincide = math.isclose(float(sp.N(valor, 20)), resultado.valor,
                                rel_tol=1e-9, abs_tol=1e-12)
    except (TypeError, ValueError):
        coincide = False
    if not coincide:
        return [final]

    pasos = acc.pasos[:_MAXIMO_PASOS]
    if not pasos:
        pasos = [Paso("No hay nada que desarrollar",
                      "La cuenta sale directa, sin fracciones ni raíces que simplificar.")]
    return pasos + [final]


# --------------------------------------------------------------------------- #
# Geometría
# --------------------------------------------------------------------------- #

_LETRA = "A-Za-zÁÉÍÓÚáéíóúñαβγδθφ_"


def _a_sympy(formula: str) -> str:
    """Una fórmula de la ficha («π·r²·h») en sintaxis de sympy."""
    texto = (formula.replace("·", "*").replace("×", "*").replace("π", "pi")
             .replace("²", "**2").replace("³", "**3").replace("√", "sqrt"))
    return texto


def _exacto_de(valor: float):
    """El dato como fracción si lo es de verdad (2.5 → 5/2), si no, decimal."""
    fraccion = sp.Rational(repr(float(valor)))
    return fraccion if fraccion.q <= 1000 else sp.Float(valor)


def pasos_figura(nombre: str, valores: dict, unidad: str = "",
                 decimales: int = 6) -> list[Paso]:
    """La fórmula, los datos sustituidos y el resultado, para cada magnitud.

    `valores` son los datos ya pasados a la misma unidad. Sólo se desarrollan
    las fórmulas cuyo resultado coincide con el que calcula la figura: una
    ficha con una fórmula mal escrita no debe dar una explicación equivocada.
    """
    from . import figuras as geo

    figura = geo.figura(nombre)
    resultados = figura.calcular(valores)
    acc = _Acumulador()

    datos = {simbolo: _exacto_de(v) for simbolo, v in valores.items()}
    acc.add("Datos", "", ",  ".join(f"{s} = {_t(v)}{(' ' + unidad) if unidad else ''}"
                                   for s, v in datos.items()))

    conocidos = dict(datos)
    usados = set()
    for formula in figura.formulas:
        if "=" not in formula:
            continue
        izquierda, derecha = (parte.strip() for parte in formula.split("=", 1))
        nombres = {s: sp.Symbol(s) for s in conocidos}
        try:
            expresion = sp.sympify(_a_sympy(derecha), locals={**nombres, "pi": sp.pi,
                                                              "sqrt": sp.sqrt})
        except Exception:                                         # noqa: BLE001
            continue
        # «A ≈ … , p = 1,6075» (la del elipsoide) se lee como una tupla: esas
        # fichas llevan aproximaciones, no fórmulas que desarrollar.
        if not isinstance(expresion, sp.Expr):
            continue
        if not expresion.free_symbols <= {sp.Symbol(s) for s in conocidos}:
            continue
        valor = sp.nsimplify(expresion.subs({sp.Symbol(s): v for s, v in conocidos.items()}))
        try:
            numero = float(valor)
        except (TypeError, ValueError):
            continue

        # ¿A qué resultado de la ficha corresponde?
        pareja = next((r for r in resultados if r.etiqueta not in usados
                       and math.isclose(r.valor, numero, rel_tol=1e-9, abs_tol=1e-12)), None)
        if pareja is None:
            conocidos[izquierda] = valor
            continue
        usados.add(pareja.etiqueta)

        sustituida = derecha
        for simbolo, dato in sorted(conocidos.items(), key=lambda par: -len(par[0])):
            sustituida = re.sub(rf"(?<![{_LETRA}]){re.escape(simbolo)}(?![{_LETRA}0-9])",
                                _factor(dato), sustituida)
        exacta = simb._mas_legible(valor)
        texto_exacto = _t(exacta) if simb.presentable(exacta) else None
        aproximado = formatear(pareja.valor, decimales)
        unidad_resultado = (pareja.unidad.replace("u", unidad, 1)
                            if unidad and pareja.unidad.startswith("u") else pareja.unidad)
        sufijo = f" {unidad_resultado}" if unidad_resultado else ""

        conocidos[izquierda] = simb._mas_legible(valor)
        linea = f"{izquierda} = {derecha} = {sustituida}"
        if texto_exacto and texto_exacto != aproximado:
            linea += f" = {texto_exacto} ≈ {aproximado}{sufijo}"
        else:
            linea += f" = {aproximado}{sufijo}"
        acc.add(pareja.etiqueta, "", linea)

    if len(acc.pasos) == 1:
        acc.add("Resultado", "Esta figura se calcula de forma directa: "
                "no hay una fórmula que desarrollar.", "")
    return acc.pasos


# --------------------------------------------------------------------------- #
# Conversiones
# --------------------------------------------------------------------------- #

def pasos_conversion(valor: float, origen: str, destino: str, categoria: str,
                     decimales: int = 6) -> list[Paso]:
    """Por qué número se multiplica, y de dónde sale ese número."""
    from . import unidades as uni

    cat = uni.categoria(categoria)
    de = next(u for u in cat.unidades if u.simbolo == origen)
    a = next(u for u in cat.unidades if u.simbolo == destino)
    base = cat.unidad_base if hasattr(cat, "unidad_base") else None
    simbolo_base = base.simbolo if hasattr(base, "simbolo") else str(base or "")
    resultado = uni.convertir(valor, origen, destino, categoria)
    f = lambda x: formatear(x, decimales)                            # noqa: E731
    acc = _Acumulador()

    if de.simbolo == a.simbolo:
        acc.add("Es la misma unidad", "", f"{f(valor)} {origen} = {f(valor)} {destino}")
        return acc.pasos

    lineales = not (de.desplazamiento or a.desplazamiento or de.inversa or a.inversa)
    if lineales:
        razon = de.factor / a.factor
        if a.factor == 1:
            acc.add("Cuánto vale", "", f"1 {origen} = {f(de.factor)} {destino}")
            acc.add("Multiplicamos", "",
                    f"{f(valor)} {origen} × {f(de.factor)} = {f(resultado)} {destino}")
            return acc.pasos
        if de.factor == 1:
            acc.add("Cuánto vale", "", f"1 {destino} = {f(a.factor)} {origen}")
            acc.add("Dividimos", "",
                    f"{f(valor)} {origen} ÷ {f(a.factor)} = {f(resultado)} {destino}")
            return acc.pasos
        acc.add("Cuánto vale cada una", f"en la unidad de referencia, {simbolo_base}",
                f"1 {origen} = {f(de.factor)} {simbolo_base},   "
                f"1 {destino} = {f(a.factor)} {simbolo_base}")
        if razon >= 1:
            acc.add("El factor de conversión", "", f"1 {origen} = {f(de.factor)} / "
                    f"{f(a.factor)} {destino} = {f(razon)} {destino}")
            acc.add("Multiplicamos", "",
                    f"{f(valor)} {origen} × {f(razon)} = {f(resultado)} {destino}")
        else:
            inversa = a.factor / de.factor
            acc.add("El factor de conversión", "", f"1 {destino} = {f(a.factor)} / "
                    f"{f(de.factor)} {origen} = {f(inversa)} {origen}")
            acc.add("Dividimos", "",
                    f"{f(valor)} {origen} ÷ {f(inversa)} = {f(resultado)} {destino}")
        return acc.pasos

    # Temperaturas: la relación directa entre las dos, «°F = °C × 9/5 + 32»,
    # que es como se enseña, y no el paso por kelvin.
    if not (de.inversa or a.inversa):
        pendiente = de.factor / a.factor
        corte = (de.desplazamiento - a.desplazamiento) / a.factor
        fraccion = sp.Rational(repr(pendiente)).limit_denominator(100)
        texto_pendiente = (_t(fraccion)
                           if math.isclose(float(fraccion), pendiente, rel_tol=1e-12)
                           else f(pendiente))
        corte_texto = f(abs(corte))
        signo = "+" if corte >= 0 else "−"
        relacion = f"{destino} = {origen}"
        cuenta = f"{f(valor)}"
        if not math.isclose(pendiente, 1):
            relacion += f" × {texto_pendiente}"
            cuenta += f" × {texto_pendiente}"
        if not math.isclose(corte, 0, abs_tol=1e-12):
            relacion += f" {signo} {corte_texto}"
            cuenta += f" {signo} {corte_texto}"
        acc.add("La relación entre las dos", "", relacion)
        acc.add("Sustituimos", "", f"{cuenta} = {f(resultado)} {destino}")
        return acc.pasos

    # Unidades inversas (consumos, por ejemplo): se pasa por la referencia.
    en_base = de.a_base(valor)
    if de.inversa:
        cuenta = f"{f(de.factor)} / {f(valor)}"
    elif de.desplazamiento:
        cuenta = (f"{f(valor)} × {f(de.factor)} + {f(de.desplazamiento)}"
                  if de.factor != 1 else f"{f(valor)} + {f(de.desplazamiento)}")
    else:
        cuenta = f"{f(valor)} × {f(de.factor)}"
    acc.add(f"Pasamos a {simbolo_base}", "", f"{cuenta} = {f(en_base)} {simbolo_base}")

    if a.inversa:
        cuenta = f"{f(a.factor)} / {f(en_base)}"
    elif a.desplazamiento:
        cuenta = (f"({f(en_base)} − {f(a.desplazamiento)}) / {f(a.factor)}"
                  if a.factor != 1 else f"{f(en_base)} − {f(a.desplazamiento)}")
    else:
        cuenta = f"{f(en_base)} / {f(a.factor)}"
    acc.add(f"De {simbolo_base} a {destino}", "", f"{cuenta} = {f(resultado)} {destino}")
    return acc.pasos
