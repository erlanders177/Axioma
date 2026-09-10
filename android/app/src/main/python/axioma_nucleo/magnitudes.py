"""Aritmética con unidades dentro de la calculadora.

Permite escribir ``5 km + 300 m`` y obtener ``5.3 km``, o ``5 km a millas`` para
convertir. Se apoya en el catálogo de :mod:`unidades`.

**Alcance deliberado.** Se admiten:

* sumas y restas entre magnitudes de la **misma** categoría (``5 km + 300 m``);
* producto y división por un número (``5 km * 3``, ``10 km / 4``);
* división entre magnitudes de la misma categoría, que da un número sin unidad
  (``10 km / 2 km`` → ``5``);
* conversión explícita con ``a``, ``en``, ``in``, ``to`` o ``→``.

**No** se admite crear unidades derivadas multiplicando o dividiendo magnitudes
de distinta categoría (``10 km / 2 h``): eso exigiría un motor de análisis
dimensional completo. En su lugar se devuelve un mensaje que lo explica y
remite al módulo de conversiones, donde ``km/h`` ya existe como unidad.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import unidades as uni
from .formato import formatear

__all__ = [
    "ErrorMagnitud",
    "Cantidad",
    "contiene_unidades",
    "evaluar",
    "SIMBOLOS",
]


class ErrorMagnitud(ValueError):
    """La expresión con unidades no es válida."""


#: Categorías que tienen sentido en la calculadora. Se dejan fuera «Cantidades y
#: prefijos» y «Proporción» porque sus símbolos de una letra (``m`` = mili,
#: ``a`` = atto) chocarían con los de longitud, y no son magnitudes que uno sume.
_CATEGORIAS_EXCLUIDAS = {"Cantidades y prefijos", "Proporción"}

#: Orden de preferencia cuando un símbolo existe en varias categorías.
_PRIORIDAD = [
    "Longitud", "Masa", "Tiempo", "Volumen", "Área", "Velocidad",
    "Temperatura", "Energía y trabajo", "Potencia", "Presión", "Fuerza",
    "Almacenamiento de datos", "Ángulo", "Frecuencia",
]

#: La temperatura usa escalas afines: sumar 20 °C + 5 °C no significa nada
#: (¿son 25 °C o 298 K + 278 K?). Se permite convertir, pero no operar.
_SOLO_CONVERSION = {"Temperatura"}


def _construir_indice() -> dict[str, list[tuple[str, uni.Unidad]]]:
    """Símbolo -> lista de (categoría, unidad), ordenada por preferencia."""
    indice: dict[str, list[tuple[str, uni.Unidad]]] = {}
    for nombre, categoria in uni.CATEGORIAS.items():
        if nombre in _CATEGORIAS_EXCLUIDAS:
            continue
        for unidad in categoria.unidades:
            # Los símbolos con espacios o paréntesis («gal US», «mes (30 d)») no
            # se pueden reconocer sin ambigüedad dentro de una expresión.
            if " " in unidad.simbolo or "(" in unidad.simbolo:
                continue
            indice.setdefault(unidad.simbolo, []).append((nombre, unidad))

    def clave(par: tuple[str, uni.Unidad]) -> tuple[int, str]:
        nombre = par[0]
        return (_PRIORIDAD.index(nombre) if nombre in _PRIORIDAD else len(_PRIORIDAD),
                nombre)

    for simbolo in indice:
        indice[simbolo].sort(key=clave)
    return indice


_INDICE = _construir_indice()

#: Símbolos reconocidos, del más largo al más corto (para casar «km/h» antes
#: que «km»).
SIMBOLOS = sorted(_INDICE, key=len, reverse=True)

#: Palabras que introducen una conversión explícita.
_CONVERSORES = ("→", "->", " a ", " en ", " in ", " to ")

_NUMERO = re.compile(r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?")


@dataclass(frozen=True)
class Cantidad:
    """Un número con su unidad, o sin ella si ``unidad`` es ``None``."""

    valor: float
    categoria: str | None = None
    unidad: uni.Unidad | None = None

    @property
    def es_numero(self) -> bool:
        return self.unidad is None

    def en_base(self) -> float:
        if self.unidad is None:
            return self.valor
        return self.unidad.a_base(self.valor)

    def convertida_a(self, otra: uni.Unidad) -> "Cantidad":
        if self.unidad is None:
            raise ErrorMagnitud("Ese valor no tiene unidad que convertir")
        return Cantidad(otra.desde_base(self.en_base()), self.categoria, otra)

    def texto(self, decimales: int = 6) -> str:
        if self.unidad is None:
            return formatear(self.valor, decimales)
        return f"{formatear(self.valor, decimales)} {self.unidad.simbolo}"


def contiene_unidades(expresion: str) -> bool:
    """True si la expresión parece llevar unidades (para no estorbar si no).

    La calculadora la usa para decidir si evalúa con este motor o con el
    evaluador normal, así que ante la duda debe decir que no.
    """
    cuerpo, destino = _separar_conversion(expresion)
    try:
        elementos = _tokenizar(cuerpo)
    except ErrorMagnitud:
        return False

    lleva_unidad = any(
        tipo == "cantidad" and isinstance(valor, Cantidad) and valor.unidad is not None
        for tipo, valor in elementos
    )
    if not lleva_unidad:
        return False
    # En una conversión, el destino también tiene que ser una unidad conocida.
    return destino is None or _casar_simbolo(destino, 0) == destino.strip()


# --------------------------------------------------------------------------- #
# Análisis léxico
# --------------------------------------------------------------------------- #


def _resolver_unidad(simbolo: str, pista: str | None) -> tuple[str, uni.Unidad]:
    """Elige la categoría de un símbolo, usando el resto de la expresión."""
    candidatos = _INDICE[simbolo]
    if pista:
        for nombre, unidad in candidatos:
            if nombre == pista:
                return nombre, unidad
    return candidatos[0]


def _tokenizar(expresion: str) -> list[tuple[str, object]]:
    """Convierte el texto en una lista de (tipo, valor).

    Los tipos son ``"cantidad"``, ``"op"`` y ``"paren"``. Una unidad sólo se
    reconoce **detrás de un número**: así ``sin(30)`` no confunde la ``s`` de
    segundo con el nombre de la función.
    """
    texto = expresion.strip().replace(",", ".")
    elementos: list[tuple[str, object]] = []
    i = 0
    n = len(texto)

    while i < n:
        caracter = texto[i]

        if caracter.isspace():
            i += 1
            continue

        if caracter in "+-*/×÷−":
            normalizado = {"×": "*", "÷": "/", "−": "-"}.get(caracter, caracter)
            elementos.append(("op", normalizado))
            i += 1
            continue

        if caracter in "()":
            elementos.append(("paren", caracter))
            i += 1
            continue

        coincidencia = _NUMERO.match(texto, i)
        if not coincidencia:
            raise ErrorMagnitud(
                f"No se entiende «{texto[i:].strip()[:20]}» en una expresión con unidades"
            )

        valor = float(coincidencia.group())
        i = coincidencia.end()

        # Unidad opcional pegada al número o separada por espacios.
        j = i
        while j < n and texto[j].isspace():
            j += 1
        simbolo = _casar_simbolo(texto, j)
        if simbolo is None:
            elementos.append(("cantidad", Cantidad(valor)))
        else:
            # La categoría se decide después, cuando se conoce toda la expresión.
            elementos.append(("cantidad", (valor, simbolo)))
            i = j + len(simbolo)

    return _asignar_categorias(elementos)


def _casar_simbolo(texto: str, posicion: int) -> str | None:
    """Símbolo de unidad más largo que empiece en ``posicion``, si lo hay."""
    for simbolo in SIMBOLOS:
        if not texto.startswith(simbolo, posicion):
            continue
        siguiente = posicion + len(simbolo)
        # Si detrás sigue una letra o un dígito, el símbolo era en realidad el
        # principio de otra palabra: «2sin(x)» no es «2 s» seguido de «in».
        if siguiente < len(texto) and (texto[siguiente].isalnum() or texto[siguiente] == "_"):
            continue
        return simbolo
    return None


def _asignar_categorias(crudos: list[tuple[str, object]]) -> list[tuple[str, object]]:
    """Decide la categoría de cada unidad usando las demás como contexto."""
    simbolos = [v[1] for t, v in crudos if t == "cantidad" and isinstance(v, tuple)]

    # Una categoría que sólo pueda venir de un símbolo no ambiguo sirve de pista
    # para los demás: en «5 km + 300 m», «km» fija Longitud y desambigua «m».
    pista: str | None = None
    for simbolo in simbolos:
        candidatos = _INDICE[simbolo]
        if len(candidatos) == 1:
            pista = candidatos[0][0]
            break

    resultado: list[tuple[str, object]] = []
    for tipo, valor in crudos:
        if tipo == "cantidad" and isinstance(valor, tuple):
            numero, simbolo = valor
            categoria, unidad = _resolver_unidad(simbolo, pista)
            resultado.append(("cantidad", Cantidad(numero, categoria, unidad)))
        else:
            resultado.append((tipo, valor))
    return resultado


# --------------------------------------------------------------------------- #
# Análisis sintáctico y evaluación
# --------------------------------------------------------------------------- #


class _Analizador:
    """Descenso recursivo sobre los elementos ya tokenizados."""

    def __init__(self, elementos: list[tuple[str, object]]) -> None:
        self.elementos = elementos
        self.posicion = 0

    def _mirar(self) -> tuple[str, object] | None:
        if self.posicion < len(self.elementos):
            return self.elementos[self.posicion]
        return None

    def analizar(self) -> Cantidad:
        resultado = self._suma()
        if self.posicion < len(self.elementos):
            raise ErrorMagnitud("La expresión con unidades está mal formada")
        return resultado

    def _suma(self) -> Cantidad:
        izquierda = self._producto()
        while True:
            actual = self._mirar()
            if actual is None or actual[0] != "op" or actual[1] not in "+-":
                return izquierda
            self.posicion += 1
            derecha = self._producto()
            izquierda = _sumar(izquierda, derecha, str(actual[1]))

    def _producto(self) -> Cantidad:
        izquierda = self._unario()
        while True:
            actual = self._mirar()
            if actual is None or actual[0] != "op" or actual[1] not in "*/":
                return izquierda
            self.posicion += 1
            derecha = self._unario()
            izquierda = _multiplicar(izquierda, derecha, str(actual[1]))

    def _unario(self) -> Cantidad:
        actual = self._mirar()
        if actual is not None and actual[0] == "op" and actual[1] in "+-":
            self.posicion += 1
            valor = self._unario()
            if actual[1] == "-":
                return Cantidad(-valor.valor, valor.categoria, valor.unidad)
            return valor
        return self._primario()

    def _primario(self) -> Cantidad:
        actual = self._mirar()
        if actual is None:
            raise ErrorMagnitud("Falta un valor en la expresión")

        if actual[0] == "paren" and actual[1] == "(":
            self.posicion += 1
            interior = self._suma()
            cierre = self._mirar()
            if cierre is None or cierre[0] != "paren" or cierre[1] != ")":
                raise ErrorMagnitud("Falta cerrar un paréntesis")
            self.posicion += 1
            return interior

        if actual[0] == "cantidad":
            self.posicion += 1
            return actual[1]  # type: ignore[return-value]

        raise ErrorMagnitud("La expresión con unidades está mal formada")


def _exigir_operable(cantidad: Cantidad, operacion: str) -> None:
    if cantidad.categoria in _SOLO_CONVERSION:
        raise ErrorMagnitud(
            f"No se pueden {operacion} temperaturas: las escalas °C y °F no "
            f"empiezan en el cero absoluto, así que la operación no significaría "
            f"nada. Sí puede convertirlas: «20 °C a °F»."
        )


def _sumar(a: Cantidad, b: Cantidad, signo: str) -> Cantidad:
    factor = 1.0 if signo == "+" else -1.0
    verbo = "sumar" if signo == "+" else "restar"

    if a.es_numero and b.es_numero:
        return Cantidad(a.valor + factor * b.valor)

    if a.es_numero or b.es_numero:
        con_unidad = b if a.es_numero else a
        raise ErrorMagnitud(
            f"No se puede {verbo} un número suelto y una magnitud "
            f"({con_unidad.unidad.simbolo}): falta la unidad en uno de los dos."
        )

    _exigir_operable(a, verbo)
    if a.categoria != b.categoria:
        raise ErrorMagnitud(
            f"No se puede {verbo} {a.categoria.lower()} y {b.categoria.lower()}: "
            f"«{a.unidad.simbolo}» y «{b.unidad.simbolo}» miden cosas distintas."
        )

    # El resultado se expresa en la unidad del primer operando, que es lo que
    # espera quien escribe «5 km + 300 m».
    en_unidad_de_a = a.unidad.desde_base(b.en_base())
    return Cantidad(a.valor + factor * en_unidad_de_a, a.categoria, a.unidad)


def _multiplicar(a: Cantidad, b: Cantidad, signo: str) -> Cantidad:
    if signo == "/" and b.valor == 0:
        raise ErrorMagnitud("No se puede dividir entre cero")

    if a.es_numero and b.es_numero:
        return Cantidad(a.valor * b.valor if signo == "*" else a.valor / b.valor)

    # Magnitud por (o entre) un número: la unidad se conserva.
    if b.es_numero:
        _exigir_operable(a, "multiplicar" if signo == "*" else "dividir")
        nuevo = a.valor * b.valor if signo == "*" else a.valor / b.valor
        return Cantidad(nuevo, a.categoria, a.unidad)

    if a.es_numero:
        if signo == "*":
            _exigir_operable(b, "multiplicar")
            return Cantidad(a.valor * b.valor, b.categoria, b.unidad)
        raise ErrorMagnitud(
            f"Dividir un número entre una magnitud daría una unidad inversa "
            f"(1/{b.unidad.simbolo}), que esta calculadora no maneja."
        )

    # Las dos llevan unidad.
    if signo == "/" and a.categoria == b.categoria:
        _exigir_operable(a, "dividir")
        if b.en_base() == 0:
            raise ErrorMagnitud("No se puede dividir entre cero")
        return Cantidad(a.en_base() / b.en_base())

    operacion = "multiplicar" if signo == "*" else "dividir"
    raise ErrorMagnitud(
        f"No se pueden {operacion} «{a.unidad.simbolo}» y «{b.unidad.simbolo}»: "
        f"haría falta una unidad derivada. Muchas ya existen en el módulo de "
        f"Conversiones (por ejemplo km/h o kWh)."
    )


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #


def _separar_conversion(expresion: str) -> tuple[str, str | None]:
    """Separa «expresión a unidad» en sus dos partes."""
    texto = expresion.strip()
    for conversor in _CONVERSORES:
        posicion = texto.rfind(conversor)
        if posicion <= 0:
            continue
        izquierda = texto[:posicion].strip()
        derecha = texto[posicion + len(conversor):].strip()
        if izquierda and derecha:
            return izquierda, derecha
    return texto, None


def evaluar(expresion: str, decimales: int = 6) -> Cantidad:
    """Evalúa una expresión con unidades y devuelve el resultado.

    >>> evaluar("5 km + 300 m").texto()
    '5.3 km'
    >>> evaluar("20 °C a °F").texto()
    '68 °F'
    """
    cuerpo, destino = _separar_conversion(expresion)

    elementos = _tokenizar(cuerpo)
    if not elementos:
        raise ErrorMagnitud("Introduzca una expresión")
    resultado = _Analizador(elementos).analizar()

    if destino is None:
        return resultado

    simbolo = _casar_simbolo(destino, 0)
    if simbolo is None or simbolo != destino.strip():
        raise ErrorMagnitud(f"No se reconoce la unidad de destino «{destino}»")
    if resultado.unidad is None:
        raise ErrorMagnitud("El resultado no tiene unidad, así que no hay nada que convertir")

    categoria, unidad = _resolver_unidad(simbolo, resultado.categoria)
    if categoria != resultado.categoria:
        raise ErrorMagnitud(
            f"No se puede convertir {resultado.categoria.lower()} a "
            f"{categoria.lower()}: «{resultado.unidad.simbolo}» y «{simbolo}» "
            f"miden cosas distintas."
        )
    return resultado.convertida_a(unidad)
