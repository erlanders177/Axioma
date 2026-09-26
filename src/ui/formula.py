"""Fórmulas dibujadas como en el cuaderno: fracciones con raya, raíces con signo.

Dibuja el mismo árbol que devuelven el editor y el cálculo exacto del núcleo
(``{"t": "frac", "n": …, "d": …}``, ``{"t": "raiz", …}``, texto, huecos y
cursor), que también dibujan la web y Android. Aquí sólo se decide dónde va
cada trozo; qué hay que dibujar lo dice el núcleo.

Todo se alinea sobre un eje horizontal, como en la web: una fracción tiene el
numerador por encima del eje y el denominador por debajo, y el texto va
centrado en él.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from PyQt5.QtCore import QPointF, QRectF, QSize, Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QFont, QFontMetricsF, QKeySequence, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QSizePolicy, QWidget

__all__ = ["Formula", "EntradaNatural", "espaciar_operadores"]

_OPERADOR = re.compile(r"\s*([+−×÷=])\s*")


def espaciar_operadores(texto: str, primero: bool) -> str:
    """«1+2» se lee mejor con un poco de aire: «1 + 2». El signo de delante, no."""
    def poner(coincidencia: re.Match) -> str:
        operador = coincidencia.group(1)
        if primero and coincidencia.start() == 0:
            return coincidencia.group(0).lstrip()
        return f" {operador} "
    return _OPERADOR.sub(poner, texto)


@dataclass
class _Medida:
    ancho: float
    arriba: float     # por encima del eje
    abajo: float      # por debajo del eje


class _Maquetador:
    """Mide y dibuja un árbol con una fuente base."""

    def __init__(self, familia: str, colores: dict) -> None:
        self.familia = familia
        self.colores = colores
        self.cursor_x: float | None = None
        self.cursor_visible = True

    # ------------------------------------------------------------- fuentes -- #

    def fuente(self, tamano: float) -> QFont:
        fuente = QFont(self.familia)
        fuente.setPixelSize(max(9, round(tamano)))
        return fuente

    def metricas(self, tamano: float) -> QFontMetricsF:
        return QFontMetricsF(self.fuente(tamano))

    # -------------------------------------------------------------- medir -- #

    def medir_fila(self, fila: list, tamano: float) -> _Medida:
        ancho, arriba, abajo = 0.0, 0.0, 0.0
        for i, nodo in enumerate(fila):
            m = self.medir(nodo, tamano, i == 0)
            ancho += m.ancho
            arriba = max(arriba, m.arriba)
            abajo = max(abajo, m.abajo)
        if not fila:
            alto = self.metricas(tamano).height() / 2
            return _Medida(0.0, alto, alto)
        return _Medida(ancho, arriba, abajo)

    def medir(self, nodo: dict, tamano: float, primero: bool = False) -> _Medida:
        tipo = nodo["t"]
        metricas = self.metricas(tamano)
        mitad = metricas.height() / 2
        if tipo == "txt":
            texto = espaciar_operadores(nodo["v"], primero)
            return _Medida(metricas.horizontalAdvance(texto), mitad, mitad)
        if tipo == "cursor":
            return _Medida(2.0, mitad, mitad)
        if tipo == "hueco":
            return _Medida(tamano * 0.62 + 4, tamano * 0.42, tamano * 0.42)
        if tipo == "frac":
            interior = tamano * 0.9
            arriba = self.medir_fila(nodo["n"], interior)
            abajo = self.medir_fila(nodo["d"], interior)
            hueco = max(2.0, tamano * 0.08)
            return _Medida(max(arriba.ancho, abajo.ancho) + tamano * 0.3,
                           arriba.arriba + arriba.abajo + hueco,
                           abajo.arriba + abajo.abajo + hueco)
        if tipo == "raiz":
            dentro = self.medir_fila(nodo["r"], tamano)
            signo = tamano * 0.55 + (tamano * 0.15 if nodo.get("i") else 0)
            return _Medida(signo + dentro.ancho + tamano * 0.12,
                           dentro.arriba + tamano * 0.12, dentro.abajo)
        return _Medida(0.0, mitad, mitad)

    # ------------------------------------------------------------ dibujar -- #

    def dibujar_fila(self, pintor: QPainter, fila: list, x: float, eje: float,
                     tamano: float, color: QColor) -> float:
        for i, nodo in enumerate(fila):
            x = self.dibujar(pintor, nodo, x, eje, tamano, color, i == 0)
        return x

    def dibujar(self, pintor: QPainter, nodo: dict, x: float, eje: float, tamano: float,
                color: QColor, primero: bool = False) -> float:
        tipo = nodo["t"]
        medida = self.medir(nodo, tamano, primero)
        grosor = max(1.2, tamano / 15)

        if tipo == "txt":
            metricas = self.metricas(tamano)
            pintor.setFont(self.fuente(tamano))
            pintor.setPen(color)
            linea_base = eje - metricas.height() / 2 + metricas.ascent()
            pintor.drawText(QPointF(x, linea_base), espaciar_operadores(nodo["v"], primero))

        elif tipo == "cursor":
            self.cursor_x = x
            if self.cursor_visible:
                pintor.fillRect(QRectF(x, eje - medida.arriba, 2.0, medida.arriba + medida.abajo),
                                self.colores["acento"])

        elif tipo == "hueco":
            caja = QRectF(x + 2, eje - medida.arriba, medida.ancho - 4,
                          medida.arriba + medida.abajo)
            if nodo.get("activo"):
                pintor.fillRect(caja, self.colores["acento_tenue"])
                pintor.setPen(QPen(self.colores["acento"], 1.5))
            else:
                pintor.setPen(QPen(self.colores["suave"], 1.2, Qt.DashLine))
            pintor.setBrush(Qt.NoBrush)
            pintor.drawRoundedRect(caja, 3, 3)

        elif tipo == "frac":
            interior = tamano * 0.9
            arriba = self.medir_fila(nodo["n"], interior)
            abajo = self.medir_fila(nodo["d"], interior)
            hueco = max(2.0, tamano * 0.08)
            pintor.setPen(QPen(color, grosor))
            pintor.drawLine(QPointF(x + tamano * 0.06, eje), QPointF(x + medida.ancho - tamano * 0.06, eje))
            centro = x + medida.ancho / 2
            self.dibujar_fila(pintor, nodo["n"], centro - arriba.ancho / 2,
                              eje - hueco - arriba.abajo, interior, color)
            self.dibujar_fila(pintor, nodo["d"], centro - abajo.ancho / 2,
                              eje + hueco + abajo.arriba, interior, color)

        elif tipo == "raiz":
            inicio = x + (tamano * 0.15 if nodo.get("i") else 0)
            signo = tamano * 0.55
            alto = eje - medida.arriba + grosor / 2
            bajo = eje + medida.abajo
            camino = QPainterPath(QPointF(inicio, eje + tamano * 0.05))
            camino.lineTo(QPointF(inicio + signo * 0.25, eje - tamano * 0.02))
            camino.lineTo(QPointF(inicio + signo * 0.5, bajo))
            camino.lineTo(QPointF(inicio + signo * 0.95, alto))
            camino.lineTo(QPointF(x + medida.ancho, alto))
            pintor.setPen(QPen(color, grosor, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            pintor.setBrush(Qt.NoBrush)
            pintor.drawPath(camino)
            if nodo.get("i"):
                pintor.setFont(self.fuente(tamano * 0.45))
                pintor.setPen(color)
                pintor.drawText(QPointF(x, eje - tamano * 0.1), nodo["i"])
            self.dibujar_fila(pintor, nodo["r"], inicio + signo, eje, tamano, color)

        return x + medida.ancho


class Formula(QWidget):
    """Un árbol del núcleo dibujado, alineado a la derecha como una calculadora."""

    def __init__(self, tamano: float = 28, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._arbol: list = []
        self._tamano = tamano
        self._suave = False
        self._marcador = ""
        self._color: str | None = None
        self._colores = {
            "texto": QColor("#e6edf3"), "suave": QColor("#8b98ac"),
            "acento": QColor("#4a9eff"), "acento_tenue": QColor("#1e3a5f"),
            "error": QColor("#ff6b6b"),
        }
        self._familia = "Segoe UI"
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._ajustar_alto()

    # ------------------------------------------------------------ contenido -- #

    def poner(self, arbol: list, suave: bool = False, marcador: str = "",
              color: str | None = None) -> None:
        """Dibuja un árbol. `color`: "suave" o "error" en lugar del de siempre."""
        self._arbol = list(arbol or [])
        self._suave = suave
        self._marcador = marcador
        self._color = color
        self._ajustar_alto()
        self.update()

    def poner_texto(self, texto: str, suave: bool = False, color: str | None = None) -> None:
        self.poner([{"t": "txt", "v": texto}] if texto else [], suave, color=color)

    def arbol(self) -> list:
        return list(self._arbol)

    def poner_tamano(self, tamano: float) -> None:
        self._tamano = tamano
        self._ajustar_alto()
        self.update()

    def aplicar_paleta(self, paleta) -> None:
        self._colores = {
            "texto": QColor(paleta.texto), "suave": QColor(paleta.texto_suave),
            "acento": QColor(paleta.acento), "error": QColor(paleta.peligro),
            "acento_tenue": QColor(paleta.fondo_control_hover),
        }
        self.update()

    # --------------------------------------------------------------- medida -- #

    def _maquetador(self) -> _Maquetador:
        return _Maquetador(self._familia, self._colores)

    def _ajustar_alto(self) -> None:
        medida = self._maquetador().medir_fila(self._arbol or [{"t": "txt", "v": "0"}],
                                                self._tamano)
        alto = int(medida.arriba + medida.abajo + 10)
        self.setFixedHeight(max(int(self._tamano * 1.5), alto))

    def sizeHint(self) -> QSize:                                    # noqa: N802
        return QSize(200, self.height())

    # --------------------------------------------------------------- dibujo -- #

    def _desplazamiento(self, maquetador: _Maquetador, ancho_total: float) -> float:
        """Dónde empieza la fila: a la derecha si cabe; si no, que se vea el cursor."""
        margen = 6
        return self.width() - margen - ancho_total

    def paintEvent(self, _evento) -> None:                         # noqa: N802
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        pintor.setRenderHint(QPainter.TextAntialiasing)
        maquetador = self._maquetador()
        maquetador.cursor_visible = self._cursor_visible()
        color = self._colores[self._color or ("suave" if self._suave else "texto")]
        fila = self._arbol
        if not fila and self._marcador:
            fila = [{"t": "txt", "v": self._marcador}]
            color = self._colores["suave"]
        medida = maquetador.medir_fila(fila, self._tamano)
        eje = (self.height() - (medida.arriba + medida.abajo)) / 2 + medida.arriba
        x = self._desplazamiento(maquetador, medida.ancho)
        maquetador.dibujar_fila(pintor, fila, x, eje, self._tamano, color)
        pintor.end()

    def _cursor_visible(self) -> bool:
        return False


class EntradaNatural(Formula):
    """La línea en la que se escribe: dibuja lo del editor y recoge el teclado.

    No guarda texto: cada tecla sale por la señal `tecla` hacia el núcleo, que
    devuelve cómo queda, y se vuelve a dibujar.
    """

    #: (orden, argumento) para :meth:`Calculadora.tecla`.
    tecla = pyqtSignal(str, str)
    #: Flecha arriba (−1) o abajo (+1): el panel decide si es de la fracción o
    #: del historial.
    vertical = pyqtSignal(int)
    copiar = pyqtSignal()

    def __init__(self, tamano: float = 28, padre: QWidget | None = None) -> None:
        super().__init__(tamano, padre)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_InputMethodEnabled, True)
        self.setCursor(Qt.IBeamCursor)
        self._parpadeo = True
        self._reloj = QTimer(self)
        self._reloj.setInterval(530)
        self._reloj.timeout.connect(self._parpadear)
        self._reloj.start()

    def _parpadear(self) -> None:
        self._parpadeo = not self._parpadeo
        if self.hasFocus():
            self.update()

    def poner(self, arbol: list, suave: bool = False, marcador: str = "",
              color: str | None = None) -> None:
        # Tras cada tecla, el cursor se ve: parpadear justo al escribir despista.
        self._parpadeo = True
        self._reloj.start()
        super().poner(arbol, suave, marcador, color)

    def _cursor_visible(self) -> bool:
        return self.hasFocus() and self._parpadeo

    def _desplazamiento(self, maquetador: _Maquetador, ancho_total: float) -> float:
        margen = 6
        x = self.width() - margen - ancho_total
        if x >= margen:
            return x
        # No cabe: se desplaza lo justo para que el cursor quede a la vista.
        posicion = self._x_del_cursor(maquetador)
        if posicion is None:
            return x
        desde = self.width() - margen - 40 - posicion
        return max(x, min(margen, desde))

    def _x_del_cursor(self, maquetador: _Maquetador) -> float | None:
        """Dónde cae el cursor contando desde el principio de la fila."""
        x = 0.0
        for i, nodo in enumerate(self._arbol):
            posicion = self._buscar_cursor(maquetador, nodo, x, self._tamano, i == 0)
            if posicion is not None:
                return posicion
            x += maquetador.medir(nodo, self._tamano, i == 0).ancho
        return None

    def _buscar_cursor(self, maquetador, nodo, x, tamano, primero):
        tipo = nodo["t"]
        if tipo == "cursor" or (tipo == "hueco" and nodo.get("activo")):
            return x
        if tipo == "frac":
            interior = tamano * 0.9
            medida = maquetador.medir(nodo, tamano)
            for clave in ("n", "d"):
                fila = nodo[clave]
                ancho = maquetador.medir_fila(fila, interior).ancho
                inicio = x + (medida.ancho - ancho) / 2
                for i, hijo in enumerate(fila):
                    encontrado = self._buscar_cursor(maquetador, hijo, inicio, interior, i == 0)
                    if encontrado is not None:
                        return encontrado
                    inicio += maquetador.medir(hijo, interior, i == 0).ancho
        if tipo == "raiz":
            inicio = x + tamano * 0.55 + (tamano * 0.15 if nodo.get("i") else 0)
            for i, hijo in enumerate(nodo["r"]):
                encontrado = self._buscar_cursor(maquetador, hijo, inicio, tamano, i == 0)
                if encontrado is not None:
                    return encontrado
                inicio += maquetador.medir(hijo, tamano, i == 0).ancho
        return None

    # -------------------------------------------------------------- teclado -- #

    _ORDENES = {
        Qt.Key_Return: "calcular", Qt.Key_Enter: "calcular",
        Qt.Key_Left: "izquierda", Qt.Key_Right: "derecha",
        Qt.Key_Home: "inicio", Qt.Key_End: "fin",
        Qt.Key_Backspace: "borrar", Qt.Key_Escape: "limpiar",
    }

    def keyPressEvent(self, evento) -> None:                       # noqa: N802
        if evento.matches(QKeySequence.Paste):
            texto = QApplication.clipboard().text()
            if texto.strip():
                self.tecla.emit("escribir", texto.strip())
            return
        if evento.matches(QKeySequence.Copy):
            self.copiar.emit()
            return
        if evento.key() in (Qt.Key_Up, Qt.Key_Down):
            self.vertical.emit(-1 if evento.key() == Qt.Key_Up else 1)
            return
        orden = self._ORDENES.get(evento.key())
        if orden:
            self.tecla.emit(orden, "")
            return
        texto = evento.text()
        if texto and texto.isprintable() and not texto.isspace() \
                and not evento.modifiers() & (Qt.ControlModifier | Qt.AltModifier):
            self.tecla.emit("insertar" if len(texto) == 1 else "escribir", texto)
            return
        super().keyPressEvent(evento)

    def inputMethodEvent(self, evento) -> None:                    # noqa: N802
        # Las teclas muertas («^» en un teclado español) y los métodos de
        # entrada llegan por aquí ya compuestas.
        texto = evento.commitString()
        if texto.strip():
            self.tecla.emit("escribir", texto.strip())
        evento.accept()

    def focusInEvent(self, evento) -> None:                        # noqa: N802
        super().focusInEvent(evento)
        self.update()

    def focusOutEvent(self, evento) -> None:                       # noqa: N802
        super().focusOutEvent(evento)
        self.update()
