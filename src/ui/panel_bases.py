"""Conversión entre bases numéricas."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QSpinBox, QSplitter,
    QVBoxLayout, QWidget,
)

from ..core import bases
from .comunes import (
    PanelModulo,
    TablaResultados, aviso, boton, etiqueta, separador, tarjeta,
)

#: Atajos del desplegable de bases habituales.
BASES_HABITUALES = [
    ("Binario (2)", 2), ("Ternario (3)", 3), ("Octal (8)", 8),
    ("Decimal (10)", 10), ("Duodecimal (12)", 12), ("Hexadecimal (16)", 16),
    ("Base 32", 32), ("Base 36", 36),
]


class PanelBases(PanelModulo):
    MODULO = "bases"
    TITULO_HISTORIAL = "Historial de conversiones"

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._construir()
        self._convertir_en_vivo()

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna())


        division.setStretchFactor(0, 3)
        division.setSizes([660])
        raiz.addWidget(division)

    def _crear_columna(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()

        col.addWidget(etiqueta("Número a convertir", "seccion"))
        self.entrada = QLineEdit()
        self.entrada.setProperty("clase", "mono")
        self.entrada.setPlaceholderText("Admite signo, decimales y separadores: -1010.11")
        self.entrada.textChanged.connect(self._convertir_en_vivo)
        self.entrada.returnPressed.connect(self.convertir)
        col.addWidget(self.entrada)

        self.digitos_validos = etiqueta("", "nota", ajustar=True)
        col.addWidget(self.digitos_validos)
        col.addWidget(separador())

        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(10)
        rejilla.setVerticalSpacing(6)

        rejilla.addWidget(etiqueta("Base de origen", "seccion"), 0, 0)
        self.spin_origen, self.combo_origen = self._crear_selector_base(10)
        rejilla.addLayout(self._fila_base(self.spin_origen, self.combo_origen), 1, 0)

        self.btn_invertir = boton("⇄", "", self._invertir,
                                  tooltip="Intercambiar las bases de origen y destino")
        self.btn_invertir.setFixedWidth(42)
        rejilla.addWidget(self.btn_invertir, 1, 1)

        rejilla.addWidget(etiqueta("Base de destino", "seccion"), 0, 2)
        self.spin_destino, self.combo_destino = self._crear_selector_base(2)
        rejilla.addLayout(self._fila_base(self.spin_destino, self.combo_destino), 1, 2)

        rejilla.addWidget(etiqueta("Decimales", "seccion"), 0, 3)
        self.spin_decimales = QSpinBox()
        self.spin_decimales.setRange(0, bases.MAX_DECIMALES)
        self.spin_decimales.setValue(12)
        self.spin_decimales.setToolTip(
            "Dígitos de la parte fraccionaria en la base de destino"
        )
        self.spin_decimales.valueChanged.connect(self._convertir_en_vivo)
        rejilla.addWidget(self.spin_decimales, 1, 3)

        rejilla.setColumnStretch(0, 3)
        rejilla.setColumnStretch(2, 3)
        col.addLayout(rejilla)

        self.resultado = etiqueta("", "resultado", ajustar=True)
        self.resultado.setMinimumHeight(28)
        self.resultado.setTextInteractionFlags(Qt.TextSelectableByMouse)
        col.addWidget(self.resultado)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Convertir y guardar", "primario", self.convertir))
        acciones.addWidget(boton("Copiar resultado", "", self._copiar))
        acciones.addStretch()
        col.addLayout(acciones)
        columna.addWidget(marco)

        columna.addWidget(self._crear_bloque_bits())

        marco_detalle, col_detalle = tarjeta()
        col_detalle.addWidget(etiqueta("Detalle", "seccion"))
        self.tabla = TablaResultados()
        self.tabla.setHorizontalHeaderLabels(["Representación", "Valor"])
        col_detalle.addWidget(self.tabla)
        columna.addWidget(marco_detalle, 1)

        return contenedor

    def _crear_bloque_bits(self) -> QWidget:
        """Operaciones bit a bit, útiles al trabajar con máscaras y registros."""
        marco, col = tarjeta()
        col.addWidget(etiqueta("Operaciones bit a bit", "seccion"))

        fila = QHBoxLayout()
        fila.setSpacing(6)

        self.bits_a = QLineEdit()
        self.bits_a.setPlaceholderText("A (decimal)")
        self.bits_a.setText("12")
        self.bits_a.returnPressed.connect(self.calcular_bits)
        fila.addWidget(self.bits_a, 2)

        self.combo_bits = QComboBox()
        self.combo_bits.addItems(bases.OPERACIONES_BITS)
        self.combo_bits.currentTextChanged.connect(self._actualizar_campos_bits)
        self.combo_bits.setFixedWidth(76)
        fila.addWidget(self.combo_bits)

        self.bits_b = QLineEdit()
        self.bits_b.setPlaceholderText("B (decimal)")
        self.bits_b.setText("10")
        self.bits_b.returnPressed.connect(self.calcular_bits)
        fila.addWidget(self.bits_b, 2)

        self.combo_ancho = QComboBox()
        self.combo_ancho.addItem("auto", 0)
        for ancho in bases.ANCHOS:
            self.combo_ancho.addItem(f"{ancho} bits", ancho)
        self.combo_ancho.setFixedWidth(88)
        self.combo_ancho.setToolTip("Tamaño de palabra con el que se opera")
        fila.addWidget(self.combo_ancho)

        fila.addWidget(boton("Calcular", "", self.calcular_bits))
        col.addLayout(fila)

        self.nota_bits = etiqueta(
            "Los operandos se escriben en decimal y no pueden ser negativos. "
            "NOT necesita un tamaño de palabra concreto.",
            "nota", ajustar=True,
        )
        col.addWidget(self.nota_bits)
        return marco

    def _actualizar_campos_bits(self, operacion: str) -> None:
        es_not = operacion == "NOT"
        self.bits_b.setVisible(not es_not)
        if operacion in ("<<", ">>"):
            self.bits_b.setPlaceholderText("desplazamiento")
        else:
            self.bits_b.setPlaceholderText("B (decimal)")

    def calcular_bits(self) -> None:
        operacion = self.combo_bits.currentText()
        try:
            a = int(self.bits_a.text().strip() or "0")
            b = int(self.bits_b.text().strip() or "0") if operacion != "NOT" else 0
        except ValueError:
            aviso(self, "Los operandos deben ser números enteros en decimal.",
                  "Operaciones bit a bit")
            return

        ancho = self.combo_ancho.currentData() or None
        if operacion == "NOT" and ancho is None:
            ancho = 8 if a < 256 else 32

        try:
            filas = bases.operacion_bits(operacion, a, b, ancho)
        except bases.ErrorBase as e:
            aviso(self, str(e), "Operaciones bit a bit")
            return

        self.tabla.mostrar(filas)
        resultado = dict(filas).get("Resultado (decimal)", "")
        etiqueta_operacion = (f"NOT {a}" if operacion == "NOT"
                              else f"{a} {operacion} {b}")
        self.guardar_en_historial(f"{etiqueta_operacion} = {resultado}", {
            "modo": "bits",
            "operacion": operacion,
            "a": a,
            "b": b,
            "ancho": ancho or 0,
        })

    def _crear_selector_base(self, inicial: int) -> tuple[QSpinBox, QComboBox]:
        spin = QSpinBox()
        spin.setRange(bases.BASE_MINIMA, bases.BASE_MAXIMA)
        spin.setValue(inicial)
        spin.setToolTip(f"Base entre {bases.BASE_MINIMA} y {bases.BASE_MAXIMA}")

        combo = QComboBox()
        combo.addItem("—", 0)
        for texto, valor in BASES_HABITUALES:
            combo.addItem(texto, valor)

        def desde_combo(indice: int) -> None:
            valor = combo.itemData(indice)
            if valor:
                spin.setValue(int(valor))

        combo.currentIndexChanged.connect(desde_combo)
        spin.valueChanged.connect(self._convertir_en_vivo)
        return spin, combo

    @staticmethod
    def _fila_base(spin: QSpinBox, combo: QComboBox) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(6)
        spin.setFixedWidth(64)
        fila.addWidget(spin)
        fila.addWidget(combo, 1)
        return fila

    # -------------------------------------------------------------- cálculo -- #

    def _invertir(self) -> None:
        origen, destino = self.spin_origen.value(), self.spin_destino.value()
        self.spin_origen.setValue(destino)
        self.spin_destino.setValue(origen)

    def _convertir_en_vivo(self) -> None:
        base_origen = self.spin_origen.value()
        validos = bases.DIGITOS[:base_origen]
        self.digitos_validos.setText(
            f"Dígitos válidos en {bases.nombre_base(base_origen)}: {validos}"
        )

        texto = self.entrada.text().strip()
        if not texto:
            self.resultado.clear()
            self.tabla.limpiar()
            return

        base_destino = self.spin_destino.value()
        decimales = self.spin_decimales.value()
        try:
            valor = bases.a_decimal(texto, base_origen)
            resultado = bases.desde_decimal(valor, base_destino, decimales)
        except bases.ErrorBase as e:
            self.resultado.setProperty("clase", "error")
            self._refrescar_estilo(self.resultado)
            self.resultado.setText(str(e))
            self.tabla.limpiar()
            return

        self.resultado.setProperty("clase", "resultado")
        self._refrescar_estilo(self.resultado)
        self.resultado.setText(
            f"{texto.upper()}₍{base_origen}₎  =  {resultado}₍{base_destino}₎"
        )
        self._llenar_detalle(texto, base_origen, valor, decimales)

    def _llenar_detalle(self, texto: str, base_origen: int, valor, decimales: int) -> None:
        filas: list[tuple[str, str]] = []
        for base, representacion in bases.tabla_bases(texto, base_origen, decimales):
            filas.append((bases.nombre_base(base).capitalize(), representacion))

        if isinstance(valor, int):
            filas.extend(bases.info_entero(valor))
        else:
            filas.append(("Valor decimal exacto", repr(valor)))

        try:
            filas.append(("Desglose posicional",
                          bases.desglose_posicional(texto, base_origen)))
        except bases.ErrorBase:
            pass

        self.tabla.mostrar(filas)

    def convertir(self) -> None:
        texto = self.entrada.text().strip()
        if not texto:
            aviso(self, "Introduzca un número.", "Cambio de base")
            return

        base_origen = self.spin_origen.value()
        base_destino = self.spin_destino.value()
        decimales = self.spin_decimales.value()
        try:
            resultado = bases.convertir(texto, base_origen, base_destino, decimales)
        except bases.ErrorBase as e:
            aviso(self, str(e), "Cambio de base")
            return

        self._convertir_en_vivo()
        operacion = (
            f"{texto.upper()} (base {base_origen}) → {resultado} (base {base_destino})"
        )
        self.guardar_en_historial(operacion, {
            "numero": texto,
            "base_origen": base_origen,
            "base_destino": base_destino,
            "decimales": decimales,
            "resultado": resultado,
        })

    # ---------------------------------------------------------------- varios -- #

    @staticmethod
    def _refrescar_estilo(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.resultado.text())

    def restaurar_datos(self, datos: dict) -> None:
        if datos.get("modo") == "bits":
            self.combo_bits.setCurrentText(str(datos.get("operacion", "AND")))
            self.bits_a.setText(str(datos.get("a", "")))
            self.bits_b.setText(str(datos.get("b", "")))
            indice = self.combo_ancho.findData(int(datos.get("ancho") or 0))
            if indice >= 0:
                self.combo_ancho.setCurrentIndex(indice)
            self.calcular_bits()
            return

        if "base_origen" in datos:
            self.spin_origen.setValue(int(datos["base_origen"]))
        if "base_destino" in datos:
            self.spin_destino.setValue(int(datos["base_destino"]))
        if "decimales" in datos:
            self.spin_decimales.setValue(int(datos["decimales"]))
        if "numero" in datos:
            self.entrada.setText(str(datos["numero"]))
            self.entrada.setFocus()

    def aplicar_paleta(self, paleta) -> None:
        return
