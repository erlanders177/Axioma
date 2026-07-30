"""Calculadora científica con historial."""

from __future__ import annotations

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QShortcut, QSplitter,
    QVBoxLayout, QWidget,
)

from ..core import historial as hist
from ..core import magnitudes
from ..core.config import config
from ..core.evaluador import ErrorExpresion, evaluar, parentesis_pendientes
from ..core.formato import formatear
from .comunes import PanelHistorial, aviso, boton, etiqueta, tarjeta

#: Cada tecla es (etiqueta, clase, inserción, etiqueta alterna, inserción alterna).
#: Las inserciones que empiezan por ``#`` son órdenes, no texto.
_TECLAS: list[list[tuple]] = [
    [("2ⁿᵈ", "tecla-funcion", "#segunda"), ("π", "tecla-funcion", "π"),
     ("e", "tecla-funcion", "e"), ("(", "tecla-operador", "("),
     (")", "tecla-operador", ")"), ("C", "tecla-borrar", "#limpiar")],

    [("sin", "tecla-funcion", "sin(", "asin", "asin("),
     ("cos", "tecla-funcion", "cos(", "acos", "acos("),
     ("tan", "tecla-funcion", "tan(", "atan", "atan("),
     ("xʸ", "tecla-operador", "^"),
     ("√", "tecla-funcion", "sqrt(", "∛", "cbrt("),
     ("⌫", "tecla-borrar", "#retroceso")],

    [("ln", "tecla-funcion", "ln(", "eˣ", "exp("),
     ("log", "tecla-funcion", "log10(", "10ˣ", "10^("),
     ("x²", "tecla-funcion", "^2", "x³", "^3"),
     ("1/x", "tecla-funcion", "#inverso"),
     ("|x|", "tecla-funcion", "abs("),
     ("mod", "tecla-funcion", "mod(")],

    [("7", "tecla", "7"), ("8", "tecla", "8"), ("9", "tecla", "9"),
     ("÷", "tecla-operador", "/"), ("n!", "tecla-funcion", "!"),
     ("%", "tecla-funcion", "%")],

    [("4", "tecla", "4"), ("5", "tecla", "5"), ("6", "tecla", "6"),
     ("×", "tecla-operador", "*"), ("floor", "tecla-funcion", "floor(", "ceil", "ceil("),
     ("Ans", "tecla-funcion", "ans")],

    [("1", "tecla", "1"), ("2", "tecla", "2"), ("3", "tecla", "3"),
     ("−", "tecla-operador", "-"), ("sinh", "tecla-funcion", "sinh(", "cosh", "cosh("),
     ("τ", "tecla-funcion", "tau")],

    [("±", "tecla-funcion", "#signo"), ("0", "tecla", "0"), (",", "tecla", "."),
     ("+", "tecla-operador", "+"), ("=", "tecla-igual", "#calcular")],
]


class PanelCalculadora(QWidget):
    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.memoria = 0.0
        self.ultimo_resultado = 0.0
        self.segunda_activa = False
        self._teclas_alternas: list[tuple] = []
        #: Variables que define el usuario con «nombre = expresión».
        self.variables: dict[str, float] = {}
        #: Expresiones ya calculadas, para recorrerlas con las flechas ↑/↓.
        self._expresiones: list[str] = []
        self._posicion_historial = 0
        self._borrador = ""
        self._construir()
        self._atajos()
        self._cargar_expresiones_previas()

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_calculadora())

        marco_hist, col_hist = tarjeta()
        self.historial = PanelHistorial("calculadora", "Historial de operaciones")
        self.historial.restaurar.connect(self._restaurar)
        col_hist.addWidget(self.historial)
        division.addWidget(marco_hist)

        division.setStretchFactor(0, 3)
        division.setStretchFactor(1, 2)
        division.setSizes([620, 400])
        raiz.addWidget(division)

    def _crear_columna_calculadora(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        # -- pantalla ------------------------------------------------------- #
        marco, col = tarjeta(espaciado=4)
        self.pantalla = QLineEdit()
        self.pantalla.setProperty("clase", "pantalla")
        self.pantalla.setAlignment(Qt.AlignRight)
        self.pantalla.setPlaceholderText("0")
        self.pantalla.setToolTip(
            "Puede escribir directamente con el teclado.\n"
            "Funciones: sin, cos, tan, ln, log, sqrt, abs, mod, gcd…\n"
            "Variables: escriba «r = 5» y luego podrá usar r en otras expresiones."
        )
        self.pantalla.textChanged.connect(self._actualizar_vista_previa)
        self.pantalla.returnPressed.connect(self.calcular)
        col.addWidget(self.pantalla)

        self.vista_previa = etiqueta("", "pantalla-previa")
        self.vista_previa.setAlignment(Qt.AlignRight)
        self.vista_previa.setMinimumHeight(20)
        col.addWidget(self.vista_previa)

        self.etiqueta_variables = etiqueta("", "nota", ajustar=True)
        self.etiqueta_variables.setVisible(False)
        col.addWidget(self.etiqueta_variables)
        columna.addWidget(marco)

        # -- barra de modo y memoria ---------------------------------------- #
        columna.addLayout(self._crear_barra_modo())

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
        self.combo_angulo.setFixedWidth(150)
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
        fila.addWidget(boton("Borrar variables", "", self._borrar_variables,
                             tooltip="Olvidar las variables definidas con «nombre = valor»"))
        fila.addWidget(boton("Copiar", "", self._copiar,
                             tooltip="Copiar el contenido de la pantalla"))
        return fila

    def _crear_teclado(self) -> QGridLayout:
        rejilla = QGridLayout()
        rejilla.setSpacing(6)

        for fila, teclas in enumerate(_TECLAS):
            for columna, especificacion in enumerate(teclas):
                titulo, clase, orden = especificacion[0], especificacion[1], especificacion[2]
                widget = boton(titulo, clase)
                widget.setMinimumHeight(46)
                widget.setFocusPolicy(Qt.NoFocus)
                widget.clicked.connect(lambda _, o=orden: self._pulsar(o))

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

        # Las flechas ↑/↓ recorren las expresiones anteriores, como en una
        # terminal. Se filtran en la pantalla porque un QLineEdit no las usa.
        self.pantalla.installEventFilter(self)

    # ------------------------------------------------ historial de expresiones -- #

    def eventFilter(self, objeto, evento):  # noqa: N802 (nombre impuesto por Qt)
        if objeto is self.pantalla and evento.type() == QEvent.KeyPress:
            if evento.key() == Qt.Key_Up:
                self._recorrer_historial(-1)
                return True
            if evento.key() == Qt.Key_Down:
                self._recorrer_historial(1)
                return True
        return super().eventFilter(objeto, evento)

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
            self._borrador = self.pantalla.text()

        destino = self._posicion_historial + salto
        destino = max(0, min(len(self._expresiones), destino))
        if destino == self._posicion_historial:
            return
        self._posicion_historial = destino

        texto = (self._borrador if destino == len(self._expresiones)
                 else self._expresiones[destino])
        self.pantalla.setText(texto)
        self.pantalla.setCursorPosition(len(texto))

    # -------------------------------------------------------------- órdenes -- #

    def _pulsar(self, orden: str) -> None:
        if not orden.startswith("#"):
            self._insertar(orden)
            return

        acciones = {
            "#calcular": self.calcular,
            "#limpiar": self.limpiar,
            "#retroceso": self._retroceso,
            "#signo": self._cambiar_signo,
            "#inverso": self._inverso,
            "#segunda": self._alternar_segunda,
        }
        accion = acciones.get(orden)
        if accion:
            accion()

    def _insertar(self, texto: str) -> None:
        self.pantalla.insert(texto)
        self.pantalla.setFocus()

    def limpiar(self) -> None:
        self.pantalla.clear()
        self.vista_previa.clear()
        self.pantalla.setFocus()

    def _retroceso(self) -> None:
        if self.pantalla.hasSelectedText():
            self.pantalla.del_()
        else:
            self.pantalla.backspace()
        self.pantalla.setFocus()

    def _cambiar_signo(self) -> None:
        texto = self.pantalla.text().strip()
        if not texto:
            self._insertar("-")
        elif texto.startswith("-(") and texto.endswith(")"):
            self.pantalla.setText(texto[2:-1])
        else:
            self.pantalla.setText(f"-({texto})")
        self.pantalla.setFocus()

    def _inverso(self) -> None:
        texto = self.pantalla.text().strip()
        if texto:
            self.pantalla.setText(f"1/({texto})")
        else:
            self._insertar("1/")
        self.pantalla.setFocus()

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
        self._actualizar_vista_previa()

    # ------------------------------------------------------------- cálculo -- #

    @property
    def _modo(self) -> str:
        return config["modo_angulo"]

    def _variables(self) -> dict:
        entorno = {"ans": self.ultimo_resultado, "mem": self.memoria}
        entorno.update(self.variables)
        return entorno

    @staticmethod
    def _separar_asignacion(expresion: str) -> tuple[str, str] | None:
        """Detecta «nombre = expresión» y devuelve (nombre, expresión).

        Se excluyen ``==``, ``<=`` y ``>=`` para no confundir una comparación con
        una asignación.
        """
        if expresion.count("=") != 1:
            return None
        izquierda, _, derecha = expresion.partition("=")
        if derecha.startswith("=") or izquierda.rstrip()[-1:] in "<>!":
            return None
        nombre = izquierda.strip()
        if not nombre.isidentifier() or not derecha.strip():
            return None
        return nombre, derecha.strip()

    def _actualizar_vista_previa(self) -> None:
        texto = self.pantalla.text().strip()
        if not texto:
            self.vista_previa.clear()
            return

        asignacion = self._separar_asignacion(texto)
        cuerpo = asignacion[1] if asignacion else texto

        # Se cierran los paréntesis pendientes para poder previsualizar mientras
        # el usuario sigue escribiendo.
        tentativa = cuerpo + ")" * parentesis_pendientes(cuerpo)

        if magnitudes.contiene_unidades(tentativa):
            try:
                cantidad = magnitudes.evaluar(tentativa)
            except magnitudes.ErrorMagnitud:
                self.vista_previa.clear()
                return
            prefijo = f"{asignacion[0]} = " if asignacion else "= "
            self.vista_previa.setText(prefijo + cantidad.texto(config["decimales"]))
            return

        try:
            valor = evaluar(tentativa, self._modo, self._variables())
        except ErrorExpresion:
            self.vista_previa.clear()
            return

        prefijo = f"{asignacion[0]} = " if asignacion else "= "
        self.vista_previa.setText(prefijo + formatear(valor, config["decimales"]))

    def calcular(self) -> None:
        expresion = self.pantalla.text().strip()
        if not expresion:
            return

        asignacion = self._separar_asignacion(expresion)
        if asignacion:
            self._asignar(*asignacion)
            return

        # Las expresiones con unidades («5 km + 300 m») las resuelve el motor de
        # magnitudes; el resto, el evaluador normal.
        if magnitudes.contiene_unidades(expresion):
            self._calcular_con_unidades(expresion)
            return

        try:
            valor = evaluar(expresion, self._modo, self._variables())
        except ErrorExpresion as e:
            aviso(self, str(e), "No se pudo calcular")
            return

        texto_resultado = formatear(valor, config["decimales"])
        self.ultimo_resultado = valor
        self.pantalla.setText(texto_resultado)
        self.pantalla.setCursorPosition(len(texto_resultado))
        self.vista_previa.setText(f"{expresion} =")

        self._recordar(expresion)
        self._posicion_historial = len(self._expresiones)
        self._borrador = ""

        operacion = f"{expresion} = {texto_resultado}"
        try:
            entrada = hist.guardar("calculadora", operacion, {
                "expresion": expresion,
                "resultado": texto_resultado,
                "modo_angulo": self._modo,
            })
            self.historial.anadir(entrada)
        except hist.ErrorHistorial as e:
            aviso(self, str(e), "Historial")

    def _calcular_con_unidades(self, expresion: str) -> None:
        try:
            cantidad = magnitudes.evaluar(expresion)
        except magnitudes.ErrorMagnitud as e:
            aviso(self, str(e), "Unidades")
            return

        texto_resultado = cantidad.texto(config["decimales"])
        # `ans` guarda el número sin unidad, para poder seguir operando con él.
        self.ultimo_resultado = cantidad.valor
        self.pantalla.setText(texto_resultado)
        self.pantalla.setCursorPosition(len(texto_resultado))
        self.vista_previa.setText(f"{expresion} =")

        self._recordar(expresion)
        self._posicion_historial = len(self._expresiones)
        self._borrador = ""

        try:
            entrada = hist.guardar("calculadora", f"{expresion} = {texto_resultado}", {
                "expresion": expresion,
                "resultado": texto_resultado,
                "modo_angulo": self._modo,
            })
            self.historial.anadir(entrada)
        except hist.ErrorHistorial as e:
            aviso(self, str(e), "Historial")

    def _asignar(self, nombre: str, cuerpo: str) -> None:
        """Guarda una variable del usuario: ``r = 5`` y luego ``pi*r^2``."""
        from ..core.evaluador import CONSTANTES, FUNCIONES

        if nombre in CONSTANTES or nombre in FUNCIONES or nombre in ("ans", "mem"):
            aviso(self, f"«{nombre}» es un nombre reservado: elija otro.", "Variable")
            return

        try:
            valor = evaluar(cuerpo, self._modo, self._variables())
        except ErrorExpresion as e:
            aviso(self, str(e), "No se pudo calcular")
            return

        self.variables[nombre] = valor
        self.ultimo_resultado = valor
        texto_valor = formatear(valor, config["decimales"])
        self.vista_previa.setText(f"{nombre} = {texto_valor}   (guardada)")
        self.pantalla.clear()
        self._refrescar_variables()

        operacion = f"{nombre} = {cuerpo} = {texto_valor}"
        try:
            entrada = hist.guardar("calculadora", operacion, {
                "expresion": f"{nombre} = {cuerpo}",
                "resultado": texto_valor,
                "modo_angulo": self._modo,
            })
            self.historial.anadir(entrada)
        except hist.ErrorHistorial:
            pass

    def _refrescar_variables(self) -> None:
        if not self.variables:
            self.etiqueta_variables.setText("")
            self.etiqueta_variables.setVisible(False)
            return
        resumen = "   ".join(
            f"{nombre} = {formatear(valor, 6)}" for nombre, valor in self.variables.items()
        )
        self.etiqueta_variables.setText("Variables:   " + resumen)
        self.etiqueta_variables.setVisible(True)

    def _borrar_variables(self) -> None:
        self.variables.clear()
        self._refrescar_variables()
        self.pantalla.setFocus()

    # ------------------------------------------------------------- memoria -- #

    def _memoria_limpiar(self) -> None:
        self.memoria = 0.0
        self._refrescar_memoria()

    def _memoria_leer(self) -> None:
        self._insertar(formatear(self.memoria, 12))

    def _memoria_sumar(self, signo: int) -> None:
        try:
            valor = evaluar(self.pantalla.text(), self._modo, self._variables())
        except ErrorExpresion:
            valor = self.ultimo_resultado
        self.memoria += signo * valor
        self._refrescar_memoria()

    def _refrescar_memoria(self) -> None:
        self.etiqueta_memoria.setText(f"M = {formatear(self.memoria, 6)}")

    # --------------------------------------------------------------- varios -- #

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.pantalla.text())

    def _restaurar(self, datos: dict) -> None:
        expresion = datos.get("expresion")
        if expresion:
            self.pantalla.setText(str(expresion))
            self.pantalla.setFocus()

    def aplicar_paleta(self, paleta) -> None:
        """La calculadora no dibuja gráficos: basta con la hoja de estilos global."""
        return
