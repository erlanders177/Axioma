"""El editor de la calculadora, con fracciones de dos huecos.

Como en las calculadoras escolares: se pulsa la tecla de fracción y aparecen un
hueco arriba y otro abajo. Lo que se escribe en cada hueco va entero al
numerador o al denominador, sin paréntesis. «2 + 3» sobre «4 + 5» es 5/9, no
2 + 3/4 + 5.

Por qué está en el núcleo y no en cada interfaz
-----------------------------------------------
El comportamiento del cursor —dónde va al pulsar la flecha, qué borra la tecla
de borrar dentro de una fracción— es fácil de hacer distinto sin querer. Si lo
escribiera cada versión por su cuenta, habría tres editores que se comportan
cada uno a su manera. Aquí se escribe una vez: cada interfaz sólo le pasa las
teclas y dibuja el árbol que devuelve.

Cómo se guarda
--------------
Una fila es una lista de piezas. Cada pieza es un trozo de texto tal como se ve
(«7», «sin(», «π», «×») o una :class:`Fraccion`, que a su vez tiene dos filas.
Al borrar se quita una pieza entera, así que «sin(» se va de una vez.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

__all__ = ["Editor", "Fraccion", "ErrorEditor"]


class ErrorEditor(ValueError):
    """La expresión del editor no se puede calcular tal como está."""


@dataclass
class Fraccion:
    numerador: list = field(default_factory=list)
    denominador: list = field(default_factory=list)
    #: La abrió una «/» tecleada, no la tecla de fracción. Cambia cómo se sale
    #: del denominador: ver :meth:`Editor.insertar`.
    tecleada: bool = False


#: Al escribir una de estas en el denominador de una fracción tecleada, se sale
#: de él primero: en «1/2+1/3» el «+» ya no es del denominador.
_SALEN_DEL_DENOMINADOR = {"+", "−", "-", "×", "*", "÷", "=", ")", ",", "/", " "}


#: Lo que se puede llevar al numerador al pulsar la tecla de fracción justo
#: después: cifras, la coma decimal, letras (nombres de variables) y «Ans».
def _es_de_numero(pieza) -> bool:
    return isinstance(pieza, str) and bool(pieza) and (pieza.isalnum() or pieza in ".π")


def _equilibrada(fila: list) -> bool:
    """¿Se cierran todos los paréntesis que se abren en esta fila?"""
    profundidad = 0
    for pieza in fila:
        if isinstance(pieza, str):
            profundidad += pieza.count("(") - pieza.count(")")
    return profundidad == 0


#: Lo que va detrás de su operando: 5!, 3², 50%.
_POSFIJOS = ("!", "²", "³", "%")

#: Las raíces van delante: en «√2/2» el numerador es √2, no el 2 suelto.
_PREFIJOS = ("√", "∛")


def _es_pieza(fila: list, i: int, *opciones: str) -> bool:
    return 0 <= i < len(fila) and isinstance(fila[i], str) and fila[i] in opciones


def _inicio_operando(fila: list, fin: int) -> int:
    """Dónde empieza el operando que termina justo antes de `fin`.

    Un operando es un número o un nombre, un paréntesis con su función delante
    («sin(30)», «√(2)»), una fracción ya hecha, y todo ello con sus potencias y
    sus posfijos: en «2^3/4» el numerador es 2^3, y en «5!/3», 5!.
    """
    inicio = fin
    while _es_pieza(fila, inicio - 1, *_POSFIJOS):
        inicio -= 1
    sin_posfijos = inicio

    if inicio > 0 and isinstance(fila[inicio - 1], Fraccion):
        inicio -= 1
    elif inicio > 0 and isinstance(fila[inicio - 1], str) and fila[inicio - 1].endswith(")"):
        profundidad = 0
        for i in range(inicio - 1, -1, -1):
            pieza = fila[i]
            if not isinstance(pieza, str):
                continue
            profundidad += pieza.count(")") - pieza.count("(")
            if profundidad == 0:
                inicio = i
                break
        # El nombre de la función, si se tecleó letra a letra: s, i, n, (
        while inicio > 0 and isinstance(fila[inicio - 1], str) and fila[inicio - 1].isalpha():
            inicio -= 1
    else:
        while inicio > 0 and _es_de_numero(fila[inicio - 1]):
            inicio -= 1

    if inicio == sin_posfijos:
        # Un «!» suelto no tiene nada que llevarse al numerador.
        return fin
    while _es_pieza(fila, inicio - 1, *_PREFIJOS):
        inicio -= 1
    if 1 < inicio < fin and fila[inicio - 1] == "^":
        return _inicio_operando(fila, inicio - 1)
    return inicio


def _sin_parentesis_externos(fila: list) -> list:
    """«(2+3)» dentro de un hueco de fracción sobra: la raya ya agrupa."""
    if len(fila) < 2 or fila[0] != "(" or fila[-1] != ")":
        return fila
    # Que el primero cierre con el último, y no «(1)+(2)».
    profundidad = 0
    for i, pieza in enumerate(fila):
        if isinstance(pieza, str):
            profundidad += pieza.count("(") - pieza.count(")")
        if profundidad == 0 and i < len(fila) - 1:
            return fila
    return fila[1:-1]


#: Cómo se ven al escribirlas desde un teclado físico.
_BONITAS = {"*": "×", "-": "−"}

#: Un hueco que se puede escribir tal cual delante o detrás de «/» sin cambiar
#: lo que significa: un número, un nombre, o algo ya entre paréntesis.
_SUELTO = re.compile(r"[\w.π]+")

#: Una fracción escrita en una línea sólo necesita paréntesis alrededor si lo
#: que tiene al lado la «engancharía» por un lado: 2^(1/2), 6÷(1/2).
_ANTES_SIN_PARENTESIS = ("+", "−", "-", "×", "*", "(", ",", "=")
_DESPUES_SIN_PARENTESIS = ("+", "−", "-", "×", "*", "÷", ")", ",", "=")


def _agrupado(texto: str) -> str:
    """El hueco tal cual si ya es una pieza, o entre paréntesis si no."""
    if _SUELTO.fullmatch(texto):
        return texto
    # Una llamada entera, «sqrt(2)» o «√(2)»: el nombre y un solo paréntesis.
    abre = texto.find("(")
    nombre = texto[:abre]
    if abre >= 0 and (nombre == "" or _SUELTO.fullmatch(nombre) or nombre in _PREFIJOS):
        cola = list(texto[abre:])
        if _sin_parentesis_externos(cola) != cola:
            return texto
    return f"({texto})"


class Editor:
    """Una línea de la calculadora, con su cursor."""

    def __init__(self) -> None:
        self.raiz: list = []
        #: Fila en la que está el cursor, y en qué posición de esa fila.
        self.fila: list = self.raiz
        self.pos = 0

    # ---------------------------------------------------------------- estado -- #

    @property
    def vacio(self) -> bool:
        return not self.raiz

    def _camino(self, objetivo: list, fila: list | None = None, camino=None):
        """Las fracciones que hay que atravesar desde la raíz hasta `objetivo`.

        Devuelve una lista de (fila_padre, índice_de_la_fracción, "n" | "d").
        """
        fila = self.raiz if fila is None else fila
        camino = [] if camino is None else camino
        if fila is objetivo:
            return camino
        for i, pieza in enumerate(fila):
            if isinstance(pieza, Fraccion):
                for lado, hija in (("n", pieza.numerador), ("d", pieza.denominador)):
                    encontrado = self._camino(objetivo, hija, camino + [(fila, i, lado)])
                    if encontrado is not None:
                        return encontrado
        return None

    def _padre(self):
        """(fila_padre, índice, lado) de la fracción que contiene al cursor."""
        camino = self._camino(self.fila)
        return camino[-1] if camino else None

    # -------------------------------------------------------------- escribir -- #

    def insertar(self, texto: str) -> None:
        """Escribe algo en el cursor.

        La «/» tecleada abre una fracción, pero se comporta como en una línea
        normal: en «1/2+1/3» el «+» saca del denominador, porque la división
        va antes que la suma. La tecla de fracción, en cambio, deja el cursor
        en el hueco hasta que se sale con la flecha, como en una Casio.
        """
        self._salir_si_toca(texto)
        if texto.isspace():
            # Los espacios cuentan («20 °C a °F»), pero uno basta, y al
            # principio de un hueco no pintan nada.
            if self.pos == 0 or self.fila[self.pos - 1] == " ":
                return
            texto = " "
        if texto == "/":
            # «1 /2»: el espacio de antes no es el numerador.
            while self.pos > 0 and self.fila[self.pos - 1] == " ":
                del self.fila[self.pos - 1]
                self.pos -= 1
            self.fraccion(tecleada=True)
            return
        texto = _BONITAS.get(texto, texto)
        self.fila.insert(self.pos, texto)
        self.pos += 1

    def _salir_si_toca(self, texto: str) -> None:
        """Sale del denominador de una fracción tecleada si lo que viene no es suyo."""
        while texto in _SALEN_DEL_DENOMINADOR:
            padre = self._padre()
            if padre is None or padre[2] != "d":
                return
            fila_padre, indice, _ = padre
            fraccion = fila_padre[indice]
            if (not fraccion.tecleada or not fraccion.denominador
                    or self.pos != len(self.fila)
                    or not _equilibrada(fraccion.denominador)):
                return
            fraccion.denominador[:] = _sin_parentesis_externos(fraccion.denominador)
            self.fila, self.pos = fila_padre, indice + 1

    def escribir(self, texto: str) -> None:
        """Escribe un texto entero, letra a letra (lo pegado o lo tecleado)."""
        for caracter in texto:
            self.insertar(caracter)

    def fraccion(self, tecleada: bool = False) -> None:
        """Abre una fracción.

        Si justo antes del cursor hay algo que pueda ser numerador (un número,
        un paréntesis, una potencia, otra fracción), pasa arriba y el cursor
        salta al denominador: escribir «12», pulsar la fracción y luego «5» da
        12/5, que es lo que se espera. Si no, la fracción sale vacía y el cursor
        va al numerador.
        """
        inicio = _inicio_operando(self.fila, self.pos)
        numerador = _sin_parentesis_externos(self.fila[inicio:self.pos])
        del self.fila[inicio:self.pos]
        nueva = Fraccion(list(numerador), [], tecleada)
        self.fila.insert(inicio, nueva)

        if numerador:
            self.fila, self.pos = nueva.denominador, 0
        else:
            self.fila, self.pos = nueva.numerador, 0

    # --------------------------------------------------------------- moverse -- #

    def derecha(self) -> None:
        if self.pos < len(self.fila):
            pieza = self.fila[self.pos]
            if isinstance(pieza, Fraccion):
                self.fila, self.pos = pieza.numerador, 0
            else:
                self.pos += 1
            return
        # Al final de un hueco: del numerador al denominador, y de ahí fuera.
        padre = self._padre()
        if padre is None:
            return
        fila_padre, indice, lado = padre
        fraccion = fila_padre[indice]
        if lado == "n":
            self.fila, self.pos = fraccion.denominador, 0
        else:
            self.fila, self.pos = fila_padre, indice + 1

    def izquierda(self) -> None:
        if self.pos > 0:
            pieza = self.fila[self.pos - 1]
            if isinstance(pieza, Fraccion):
                self.fila, self.pos = pieza.denominador, len(pieza.denominador)
            else:
                self.pos -= 1
            return
        padre = self._padre()
        if padre is None:
            return
        fila_padre, indice, lado = padre
        fraccion = fila_padre[indice]
        if lado == "d":
            self.fila, self.pos = fraccion.numerador, len(fraccion.numerador)
        else:
            self.fila, self.pos = fila_padre, indice

    def arriba(self) -> None:
        """Del denominador al numerador de la misma fracción."""
        padre = self._padre()
        if padre and padre[2] == "d":
            fraccion = padre[0][padre[1]]
            self.fila, self.pos = fraccion.numerador, len(fraccion.numerador)

    def abajo(self) -> None:
        """Del numerador al denominador de la misma fracción."""
        padre = self._padre()
        if padre and padre[2] == "n":
            fraccion = padre[0][padre[1]]
            self.fila, self.pos = fraccion.denominador, len(fraccion.denominador)

    def inicio(self) -> None:
        self.fila, self.pos = self.raiz, 0

    def fin(self) -> None:
        self.fila, self.pos = self.raiz, len(self.raiz)

    # ---------------------------------------------------------------- borrar -- #

    def borrar(self) -> None:
        """Borra lo que hay a la izquierda del cursor.

        Una fracción no se borra de golpe si tiene algo dentro: se entra en
        ella, para no perder de un toque lo que costó escribir.
        """
        if self.pos > 0:
            pieza = self.fila[self.pos - 1]
            if isinstance(pieza, Fraccion):
                if not pieza.numerador and not pieza.denominador:
                    del self.fila[self.pos - 1]
                    self.pos -= 1
                else:
                    self.fila, self.pos = pieza.denominador, len(pieza.denominador)
            else:
                del self.fila[self.pos - 1]
                self.pos -= 1
            return

        # Al principio de un hueco.
        padre = self._padre()
        if padre is None:
            return
        fila_padre, indice, lado = padre
        fraccion = fila_padre[indice]
        if not fraccion.numerador and not fraccion.denominador:
            del fila_padre[indice]
            self.fila, self.pos = fila_padre, indice
        elif lado == "d":
            self.fila, self.pos = fraccion.numerador, len(fraccion.numerador)
        else:
            self.fila, self.pos = fila_padre, indice

    def limpiar(self) -> None:
        self.raiz = []
        self.fila, self.pos = self.raiz, 0

    def cargar(self, texto: str) -> None:
        """Sustituye todo por un texto (un resultado, algo del historial).

        «(2+3)/(4+5)» queda como una fracción con 2+3 arriba y 4+5 abajo, sin
        los paréntesis, que en una fracción ya sobran.
        """
        self.limpiar()
        self.escribir(texto)
        self._quitar_parentesis_sobrantes(self.raiz)
        self.fin()

    def _quitar_parentesis_sobrantes(self, fila: list) -> None:
        for pieza in fila:
            if isinstance(pieza, Fraccion):
                pieza.numerador[:] = _sin_parentesis_externos(pieza.numerador)
                pieza.denominador[:] = _sin_parentesis_externos(pieza.denominador)
                self._quitar_parentesis_sobrantes(pieza.numerador)
                self._quitar_parentesis_sobrantes(pieza.denominador)

    # ------------------------------------------------------------- traducir -- #

    def lineal(self) -> str:
        """La expresión en una línea, para calcularla.

        Cada fracción va entre paréntesis por arriba y por abajo: es lo que
        hace que no haya que escribirlos a mano.
        """
        return self._lineal(self.raiz)

    def _lineal(self, fila: list) -> str:
        partes = []
        for pieza in fila:
            if isinstance(pieza, Fraccion):
                if not pieza.numerador:
                    raise ErrorEditor("Falta el numerador de una fracción")
                if not pieza.denominador:
                    raise ErrorEditor("Falta el denominador de una fracción")
                partes.append(f"(({self._lineal(pieza.numerador)})/"
                              f"({self._lineal(pieza.denominador)}))")
            else:
                partes.append(pieza)
        return "".join(partes)

    def texto(self) -> str:
        """La expresión en una línea para leerla: «(2+3)/(4+5)», «1/2+1/3».

        Es lo que se guarda en el historial. Lleva sólo los paréntesis que
        hacen falta, y vuelta a cargar con :meth:`cargar` da las mismas
        fracciones.
        """
        return self._texto(self.raiz)

    def _texto(self, fila: list) -> str:
        partes = []
        for i, pieza in enumerate(fila):
            if not isinstance(pieza, Fraccion):
                partes.append(pieza)
                continue
            if not pieza.numerador or not pieza.denominador:
                raise ErrorEditor("Falta un hueco de una fracción por rellenar")
            escrita = (f"{_agrupado(self._texto(pieza.numerador))}/"
                       f"{_agrupado(self._texto(pieza.denominador))}")
            # Los vecinos de verdad, saltando espacios: en «6 ÷ 1/2» manda el «÷».
            antes = next((p for p in reversed(fila[:i]) if p != " "), None)
            despues = next((p for p in fila[i + 1:] if p != " "), None)
            suelta = ((antes is None or (isinstance(antes, str)
                                         and antes.endswith(_ANTES_SIN_PARENTESIS)))
                      and (despues is None or (isinstance(despues, str)
                                               and despues.startswith(_DESPUES_SIN_PARENTESIS))))
            partes.append(escrita if suelta else f"({escrita})")
        return "".join(partes)

    def arbol(self, con_cursor: bool = True) -> list:
        """La fila lista para dibujar, en el mismo formato que los resultados.

        Nodos: ``{"t": "txt", "v": "2 + "}``, ``{"t": "frac", "n": fila,
        "d": fila}``, ``{"t": "cursor"}`` y ``{"t": "hueco"}`` para un hueco
        vacío, que hay que ver para saber dónde se escribe.
        """
        return self._arbol(self.raiz, con_cursor)

    def _arbol(self, fila: list, con_cursor: bool) -> list:
        nodos: list = []

        def texto(valor: str) -> None:
            if nodos and nodos[-1]["t"] == "txt":
                nodos[-1]["v"] += valor
            else:
                nodos.append({"t": "txt", "v": valor})

        for i, pieza in enumerate(fila):
            if con_cursor and fila is self.fila and i == self.pos:
                nodos.append({"t": "cursor"})
            if isinstance(pieza, Fraccion):
                nodos.append({
                    "t": "frac",
                    "n": self._arbol(pieza.numerador, con_cursor) or [{"t": "hueco"}],
                    "d": self._arbol(pieza.denominador, con_cursor) or [{"t": "hueco"}],
                })
            else:
                texto(pieza)
        if con_cursor and fila is self.fila and self.pos == len(fila):
            nodos.append({"t": "cursor"})

        # Un hueco vacío con el cursor dentro se dibuja como hueco resaltado:
        # si sólo se viera el cursor, no se sabría que ahí falta algo.
        if not fila and fila is not self.raiz and con_cursor and fila is self.fila:
            return [{"t": "hueco", "activo": True}]
        return nodos

    # -------------------------------------------------------------- órdenes -- #

    def accion(self, orden: str, argumento: str = "") -> None:
        """Punto de entrada único, para las interfaces que hablan por el puente."""
        ordenes = {
            "insertar": lambda: self.insertar(argumento),
            "escribir": lambda: self.escribir(argumento),
            "fraccion": self.fraccion,
            "izquierda": self.izquierda,
            "derecha": self.derecha,
            "arriba": self.arriba,
            "abajo": self.abajo,
            "inicio": self.inicio,
            "fin": self.fin,
            "borrar": self.borrar,
            "limpiar": self.limpiar,
            "cargar": lambda: self.cargar(argumento),
        }
        if orden not in ordenes:
            raise ErrorEditor(f"Orden desconocida: {orden}")
        ordenes[orden]()
