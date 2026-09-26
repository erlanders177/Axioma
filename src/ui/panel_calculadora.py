"""Calculadora científica con historial, fracciones de dos huecos y resultado exacto.

Qué hace cada tecla lo decide el núcleo (:class:`core.calculadora.Calculadora`),
el mismo que usan la web y Android. Este panel le pasa las teclas y dibuja la
pantalla que devuelve: lo escrito con sus fracciones, y el resultado exacto
(√2/2, 3/4) o en decimal con la tecla S⇔D.
"""

from __future__ import annotations

from PyQt5.QtCore import QEvent, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap
from PyQt5.QtWidgets import (
    QComboBox, QFrame, QGridLayout, QHBoxLayout, QShortcut, QSizePolicy,
    QVBoxLayout, QWidget,
)

from ..core import historial as hist
from ..core import variables as vars_compartidas
from ..core.calculadora import Calculadora
from ..core.config import config
from ..core.evaluador import ErrorExpresion, evaluar
from ..core.formato import formatear
from .comunes import PanelModulo, boton, etiqueta, tarjeta
from .formula import EntradaNatural, Formula
from .paso_a_paso import PasoAPaso

#: Cada tecla es (etiqueta, clase, orden, etiqueta alterna, orden alterna).
#: Una orden que empieza por ``#`` es una tecla de la calculadora del núcleo
#: (``#fraccion``, ``#sd``…) o del panel (``#segunda``); el resto es texto que
#: se escribe tal cual.
_TECLAS: list[list[tuple]] = [
    [("◄", "tecla-funcion", "#izquierda"), ("►", "tecla-funcion", "#derecha"),
     ("", "tecla-operador", "#fraccion"), ("S⇔D", "tecla-funcion", "#sd"),
     ("▲", "tecla-funcion", "#arriba"), ("▼", "tecla-funcion", "#abajo")],

    [("2ⁿᵈ", "tecla-funcion", "#segunda"), ("π", "tecla-funcion", "π"),
     ("e", "tecla-funcion", "e"), ("(", "tecla-operador", "("),
     (")", "tecla-operador", ")"), ("C", "tecla-borrar", "#limpiar")],

    [("sin", "tecla-funcion", "sin(", "asin", "asin("),
     ("cos", "tecla-funcion", "cos(", "acos", "acos("),
     ("tan", "tecla-funcion", "tan(", "atan", "atan("),
     ("xʸ", "tecla-operador", "^"),
     ("√", "tecla-funcion", "√(", "∛", "∛("),
     ("⌫", "tecla-borrar", "#borrar")],

    [("ln", "tecla-funcion", "ln(", "eˣ", "e^("),
     ("log", "tecla-funcion", "log(", "10ˣ", "10^("),
     ("x²", "tecla-funcion", "²", "x³", "³"),
     ("1/x", "tecla-funcion", "#inverso"),
     ("|x|", "tecla-funcion", "abs("),
     ("mod", "tecla-funcion", "mod(")],

    [("7", "tecla", "7"), ("8", "tecla", "8"), ("9", "tecla", "9"),
     ("÷", "tecla-operador", "÷"), ("n!", "tecla-funcion", "!"),
     ("%", "tecla-funcion", "%")],

    [("4", "tecla", "4"), ("5", "tecla", "5"), ("6", "tecla", "6"),
     ("×", "tecla-operador", "×"), ("floor", "tecla-funcion", "floor(", "ceil", "ceil("),
     ("Ans", "tecla-funcion", "Ans")],

    [("1", "tecla", "1"), ("2", "tecla", "2"), ("3", "tecla", "3"),
     ("−", "tecla-operador", "−"), ("sinh", "tecla-funcion", "sinh(", "cosh", "cosh("),
     ("τ", "tecla-funcion", "τ")],

    [("(−)", "tecla-funcion", "#negativo"), ("0", "tecla", "0"), (",", "tecla", "."),
     ("+", "tecla-operador", "+"), ("=", "tecla-igual", "#calcular")],
]

#: Órdenes del núcleo que tienen tecla propia.
_ORDENES_DEL_NUCLEO = {
    "#izquierda": "izquierda", "#derecha": "derecha", "#arriba": "arriba",
    "#abajo": "abajo", "#fraccion": "fraccion", "#sd": "sd", "#limpiar": "limpiar",
    "#borrar": "borrar", "#negativo": "negativo", "#calcular": "calcular",
}


def _icono_fraccion(color: str, tamano: int = 22) -> QIcon:
    """La tecla de fracción: dos huecos y la raya, que es lo que hace."""
    lienzo = QPixmap(tamano, tamano)
    lienzo.fill(Qt.transparent)
    pintor = QPainter(lienzo)
    pintor.setRenderHint(QPainter.Antialiasing)
    pintor.setPen(QPen(QColor(color), 1.6))
    caja_ancho, caja_alto = tamano * 0.46, tamano * 0.32
    izquierda = (tamano - caja_ancho) / 2
    pintor.drawRoundedRect(QRectF(izquierda, 1, caja_ancho, caja_alto), 2, 2)
    pintor.drawRoundedRect(QRectF(izquierda, tamano - caja_alto - 1, caja_ancho, caja_alto), 2, 2)
    pintor.drawLine(QPointF(tamano * 0.18, tamano / 2), QPointF(tamano * 0.82, tamano / 2))
    pintor.end()
    return QIcon(lienzo)


class _Pantalla(QFrame):
    """Lo escrito arriba y el resultado debajo, como en una calculadora escolar.

    Conserva ``setText``, ``text`` y ``clear`` de la antigua línea de texto:
    así el resto de la aplicación (el historial, las pruebas) la sigue usando
    igual.
    """

    def __init__(self, panel: PanelCalculadora) -> None:
        super().__init__()
        self._panel = panel
        self.setProperty("clase", "pantalla")
        columna = QVBoxLayout(self)
        columna.setContentsMargins(12, 8, 12, 8)
        columna.setSpacing(2)
        self.entrada = EntradaNatural(28)
        self.entrada.setToolTip(
            "Escriba con el teclado: «/» hace una fracción y las flechas se mueven\n"
            "por ella. Funciones: sin, cos, tan, ln, log, sqrt, abs, mod, gcd…\n"
            "Variables: escriba «r = 5» y luego podrá usar r en otras expresiones."
        )
        self.resultado = Formula(30)
        columna.addWidget(self.entrada)
        columna.addWidget(self.resultado)

    def setText(self, texto: str) -> None:                          # noqa: N802
        self._panel.cargar(texto)

    def text(self) -> str:
        return self._panel.texto_en_pantalla()

    def clear(self) -> None:
        self._panel.limpiar()

    def setFocus(self, *args) -> None:                               # noqa: N802
        self.entrada.setFocus(*args)


class PanelCalculadora(PanelModulo):
    MODULO = "calculadora"
    TITULO_HISTORIAL = "Historial de operaciones"

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.calc = Calculadora(config["modo_angulo"], config["decimales"])
        self.segunda_activa = False
        self._teclas_alternas: list[tuple] = []
        self._paleta = None
        self._estado: dict = {}
        #: Las variables son compartidas con la barra de cálculo y con el resto
        #: de módulos, así que viven en `core.variables`, no aquí.
        #: Expresiones ya calculadas, para recorrerlas con las flechas ↑/↓.
        self._expresiones: list[str] = []
        self._posicion_historial = 0
        self._borrador = ""
        self._construir()
        self._atajos()
        self._cargar_expresiones_previas()
        self._pintar(self.calc.estado())

    # --------------------------------------------------- memoria y Ans -- #

    @property
    def memoria(self) -> float:
        return self.calc.memoria

    @memoria.setter
    def memoria(self, valor: float) -> None:
        self.calc.memoria = valor

    @property
    def ultimo_resultado(self) -> float:
        return self.calc.ans

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.addWidget(self._crear_columna_calculadora())

    def _crear_columna_calculadora(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        # -- pantalla ------------------------------------------------------- #
        self.pantalla = _Pantalla(self)
        self.pantalla.entrada.tecla.connect(self._tecla)
        self.pantalla.entrada.vertical.connect(self._vertical)
        self.pantalla.entrada.copiar.connect(self._copiar)
        columna.addWidget(self.pantalla)

        self.etiqueta_variables = etiqueta("", "nota", ajustar=True)
        self.etiqueta_variables.setVisible(False)
        columna.addWidget(self.etiqueta_variables)

        # -- barra de modo, memoria y paso a paso --------------------------- #
        columna.addLayout(self._crear_barra_modo())

        columna.addWidget(self.paso_a_paso.caja)

        # -- teclado -------------------------------------------------------- #
        marco_teclas, col_teclas = tarjeta(margen=10, espaciado=0)
        col_teclas.addLayout(self._crear_teclado())
        columna.addWidget(marco_teclas, 1)
        return contenedor

    def _crear_barra_modo(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(6)

        self.combo_angulo = QComboBox()
        self.combo_angulo.addItems(["DEG — grados", "RAD — radianes", "GRAD — gradianes"])
        modos = ["DEG", "RAD", "GRAD"]
        actual = config["modo_angulo"]
        self.combo_angulo.setCurrentIndex(modos.index(actual) if actual in modos else 0)
        self.combo_angulo.currentIndexChanged.connect(self._cambiar_angulo)
        self.combo_angulo.setToolTip("Unidad de ángulo para las funciones trigonométricas")
        self.combo_angulo.setMinimumWidth(96)
        self.combo_angulo.setMaximumWidth(150)
        fila.addWidget(self.combo_angulo)

        fila.addWidget(boton("MC", "", self._memoria_limpiar, tooltip="Borrar la memoria"))
        fila.addWidget(boton("MR", "", self._memoria_leer, tooltip="Insertar el valor guardado"))
        fila.addWidget(boton("M+", "", lambda: self._memoria_sumar(1),
                             tooltip="Sumar el resultado a la memoria"))
        fila.addWidget(boton("M−", "", lambda: self._memoria_sumar(-1),
                             tooltip="Restar el resultado de la memoria"))

        self.etiqueta_memoria = etiqueta("M = 0", "subtitulo")
        fila.addWidget(self.etiqueta_memoria)
        fila.addStretch()

        self.paso_a_paso = PasoAPaso("calculadora", self.calc.pasos)
        self.boton_pasos = self.paso_a_paso.boton
        fila.addWidget(self.boton_pasos)
        # El botón de borrar variables está en la barra de cálculo, que se ve
        # desde aquí: tenerlo dos veces sólo ocupa sitio.
        fila.addWidget(boton("Copiar", "", self._copiar,
                             tooltip="Copiar el resultado (o lo escrito)"))
        return fila

    def _crear_teclado(self) -> QGridLayout:
        rejilla = QGridLayout()
        rejilla.setSpacing(6)

        for fila, teclas in enumerate(_TECLAS):
            for columna, especificacion in enumerate(teclas):
                titulo, clase, orden = especificacion[0], especificacion[1], especificacion[2]
                widget = boton(titulo, clase)
                widget.setMinimumHeight(42)
                # Ignored: las teclas se reparten el ancho que haya en lugar de
                # exigir el de su texto. Con la calculadora compartiendo
                # pantalla con otros apartados, ese ancho puede ser poco.
                widget.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
                widget.setFocusPolicy(Qt.NoFocus)
                widget.clicked.connect(lambda _, o=orden: self._pulsar(o))

                if orden == "#fraccion":
                    self.boton_fraccion = widget
                    widget.setIcon(_icono_fraccion("#4a9eff"))
                    widget.setToolTip("Fracción: un hueco arriba y otro abajo.\n"
                                      "Las flechas pasan de uno a otro y salen.")
                elif orden == "#sd":
                    self.boton_sd = widget
                    widget.setCheckable(True)
                    widget.setToolTip("Resultado exacto (√2/2) o decimal (0.707107)")

                # La tecla «=» ocupa las dos últimas columnas de su fila.
                if clase == "tecla-igual":
                    rejilla.addWidget(widget, fila, columna, 1, 2)
                else:
                    rejilla.addWidget(widget, fila, columna)

                if len(especificacion) == 5:
                    self._teclas_alternas.append(
                        (widget, titulo, orden, especificacion[3], especificacion[4])
                    )

        for columna in range(6):
            rejilla.setColumnStretch(columna, 1)
        for fila in range(len(_TECLAS)):
            rejilla.setRowStretch(fila, 1)
        return rejilla

    def _atajos(self) -> None:
        # El contexto debe limitarse a este panel: con el predeterminado
        # (WindowShortcut) la tecla seguiría actuando desde los demás módulos.
        escape = QShortcut(QKeySequence("Escape"), self, self.limpiar)
        escape.setContext(Qt.WidgetWithChildrenShortcut)

    # ------------------------------------------------ historial de expresiones -- #

    def eventFilter(self, objeto, evento):  # noqa: N802 (nombre impuesto por Qt)
        if objeto in (self.pantalla, self.pantalla.entrada) and evento.type() == QEvent.KeyPress:
            if evento.key() == Qt.Key_Up:
                self._vertical(-1)
                return True
            if evento.key() == Qt.Key_Down:
                self._vertical(1)
                return True
        return super().eventFilter(objeto, evento)

    def _vertical(self, salto: int) -> None:
        """↑/↓: dentro de una fracción, de un hueco a otro; fuera, el historial."""
        if not self.calc.calculado and self.calc.editor._padre() is not None:
            self._tecla("arriba" if salto < 0 else "abajo")
        else:
            self._recorrer_historial(salto)

    def _cargar_expresiones_previas(self) -> None:
        """Rellena la lista de flechas con lo que ya había guardado en disco."""
        try:
            entradas = hist.cargar("calculadora")
        except hist.ErrorHistorial:
            return
        # `cargar` devuelve de la más reciente a la más antigua; aquí interesa el
        # orden cronológico para que ↑ vaya hacia atrás en el tiempo.
        for entrada in reversed(entradas):
            expresion = (entrada.get("datos") or {}).get("expresion")
            if expresion:
                self._recordar(str(expresion))
        self._posicion_historial = len(self._expresiones)

    def _recordar(self, expresion: str) -> None:
        """Añade una expresión al final, sin repetir la anterior."""
        if not expresion or (self._expresiones and self._expresiones[-1] == expresion):
            return
        self._expresiones.append(expresion)
        del self._expresiones[:-200]

    def _recorrer_historial(self, salto: int) -> None:
        if not self._expresiones:
            return

        # Al salir por primera vez de la línea actual se guarda lo escrito, para
        # poder recuperarlo bajando del todo.
        if self._posicion_historial == len(self._expresiones):
            self._borrador = self.calc.texto()

        destino = self._posicion_historial + salto
        destino = max(0, min(len(self._expresiones), destino))
        if destino == self._posicion_historial:
            return
        self._posicion_historial = destino

        texto = (self._borrador if destino == len(self._expresiones)
                 else self._expresiones[destino])
        self.cargar(texto)

    # -------------------------------------------------------------- órdenes -- #

    def _pulsar(self, orden: str) -> None:
        if orden in _ORDENES_DEL_NUCLEO:
            self._tecla(_ORDENES_DEL_NUCLEO[orden])
        elif orden == "#segunda":
            self._alternar_segunda()
        elif orden == "#inverso":
            self._tecla("escribir", "^(−1)")
        else:
            self._tecla("insertar", orden)
        self.pantalla.entrada.setFocus()

    def _tecla(self, orden: str, argumento: str = "") -> None:
        """Una tecla al núcleo, y a dibujar cómo queda la pantalla."""
        self.calc.modo = config["modo_angulo"]
        self.calc.decimales = config["decimales"]
        self._pintar(self.calc.tecla(orden, argumento))

    def calcular(self) -> None:
        self._tecla("calcular")

    def cargar(self, texto: str) -> None:
        """Pone un texto en la pantalla (del historial, de las flechas…)."""
        self._tecla("cargar", str(texto))
        self.pantalla.entrada.setFocus()

    def limpiar(self) -> None:
        self._tecla("limpiar")
        self.pantalla.entrada.setFocus()

    def texto_en_pantalla(self) -> str:
        """El resultado si se acaba de calcular; si no, lo escrito."""
        visible = self._estado.get("resultado")
        if self._estado.get("calculado") and visible:
            return visible["texto"]
        return self.calc.texto()

    def error(self) -> str:
        """El aviso de error que hay en pantalla, o vacío."""
        return self._estado.get("error") or ""

    def _alternar_segunda(self) -> None:
        self.segunda_activa = not self.segunda_activa
        for widget, titulo, orden, titulo_alt, orden_alt in self._teclas_alternas:
            usar_alterna = self.segunda_activa
            widget.setText(titulo_alt if usar_alterna else titulo)
            destino = orden_alt if usar_alterna else orden
            widget.clicked.disconnect()
            widget.clicked.connect(lambda _, o=destino: self._pulsar(o))

    def _cambiar_angulo(self, indice: int) -> None:
        config["modo_angulo"] = ["DEG", "RAD", "GRAD"][indice]
        self.calc.modo = config["modo_angulo"]
        self._pintar(self.calc.estado())

    # ------------------------------------------------------------- pantalla -- #

    @property
    def _modo(self) -> str:
        return config["modo_angulo"]

    @property
    def variables(self) -> dict:
        """Vista de las variables compartidas (la usan las pruebas)."""
        return vars_compartidas.valores()

    def _pintar(self, estado: dict) -> None:
        self._estado = estado
        entrada, resultado = self.pantalla.entrada, self.pantalla.resultado

        entrada.poner_tamano(20 if estado["calculado"] else 28)
        entrada.poner(estado["entrada"], suave=estado["calculado"])

        visible = estado["resultado"]
        if estado["error"]:
            resultado.poner_tamano(15)
            resultado.poner_texto(estado["error"], color="error")
        elif visible:
            resultado.poner_tamano(30)
            resultado.poner(visible["arbol"])
        else:
            resultado.poner_tamano(15)
            resultado.poner_texto(estado["previa"], color="suave")

        self.boton_sd.setEnabled(bool(visible and visible["tiene_exacto"]))
        self.boton_sd.setChecked(bool(visible and visible["en_decimal"]))

        anotar = estado["anotar"]
        if anotar:
            self._recordar(anotar["expresion"])
            self._posicion_historial = len(self._expresiones)
            self._borrador = ""
            self.guardar_en_historial(anotar["texto"], {
                "expresion": anotar["expresion"],
                "resultado": anotar["resultado"],
                "modo_angulo": self._modo,
            })
            if visible and visible["variable"]:
                self._refrescar_variables()
            self.paso_a_paso.refrescar()

    # ------------------------------------------------------------- variables -- #

    def _refrescar_variables(self) -> None:
        resumen = vars_compartidas.resumen(config["decimales"])
        self.etiqueta_variables.setText(f"Variables:   {resumen}" if resumen else "")
        self.etiqueta_variables.setVisible(bool(resumen))

    def variables_actualizadas(self) -> None:
        """La barra de cálculo ha cambiado las variables: refrescar la vista."""
        self._refrescar_variables()

    def _borrar_variables(self) -> None:
        """Olvida las variables. La acción vive en la barra; esto la comparte."""
        vars_compartidas.borrar_todas()
        self._refrescar_variables()
        self.pantalla.entrada.setFocus()

    # ------------------------------------------------------------- memoria -- #

    def _valor_en_pantalla(self) -> float:
        visible = self._estado.get("resultado")
        if self._estado.get("calculado") and visible:
            return visible["valor"]
        try:
            entorno = {"ans": self.calc.ans, "Ans": self.calc.ans, "mem": self.calc.memoria}
            entorno.update(vars_compartidas.valores())
            return evaluar(self.calc.editor.lineal(), self._modo, entorno)
        except (ErrorExpresion, ValueError):
            return self.calc.ans

    def _memoria_limpiar(self) -> None:
        self.calc.memoria = 0.0
        self._refrescar_memoria()

    def _memoria_leer(self) -> None:
        self._tecla("escribir", formatear(self.calc.memoria, 12))

    def _memoria_sumar(self, signo: int) -> None:
        self.calc.memoria += signo * self._valor_en_pantalla()
        self._refrescar_memoria()

    def _refrescar_memoria(self) -> None:
        self.etiqueta_memoria.setText(f"M = {formatear(self.calc.memoria, 6)}")

    # --------------------------------------------------------------- varios -- #

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.texto_en_pantalla())

    def restaurar_datos(self, datos: dict) -> None:
        expresion = datos.get("expresion")
        if expresion:
            self.cargar(str(expresion))

    def aplicar_paleta(self, paleta) -> None:
        self._paleta = paleta
        self.pantalla.entrada.aplicar_paleta(paleta)
        self.pantalla.resultado.aplicar_paleta(paleta)
        self.boton_fraccion.setIcon(_icono_fraccion(paleta.acento))
        self.paso_a_paso.aplicar_paleta(paleta)

