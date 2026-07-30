"""Conversor de unidades: grupo → categoría → unidades, con tabla completa."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLineEdit, QSplitter, QVBoxLayout,
    QWidget,
)

from ..core import historial as hist
from ..core import unidades as uni
from ..core.config import config
from ..core.formato import formatear
from .comunes import (
    CampoNumerico, PanelHistorial, TablaResultados, aviso, boton, etiqueta,
    separador, tarjeta,
)


class PanelConversiones(QWidget):
    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._cargando = False
        self._construir()
        self._cargar_grupos()

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_conversion())

        marco_hist, col_hist = tarjeta()
        self.historial = PanelHistorial("conversiones", "Historial de conversiones")
        self.historial.restaurar.connect(self._restaurar)
        col_hist.addWidget(self.historial)
        division.addWidget(marco_hist)

        division.setStretchFactor(0, 3)
        division.setStretchFactor(1, 2)
        division.setSizes([680, 380])
        raiz.addWidget(division)

    def _crear_columna_conversion(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()

        # -- buscador de unidades ------------------------------------------- #
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText(
            "Buscar una unidad por nombre o símbolo (p. ej. «nudo», «kWh», «psi»)…"
        )
        self.buscador.setClearButtonEnabled(True)
        self.buscador.returnPressed.connect(self._buscar_unidad)
        fila_busqueda = QHBoxLayout()
        fila_busqueda.addWidget(self.buscador, 1)
        fila_busqueda.addWidget(boton("Buscar", "", self._buscar_unidad))
        col.addLayout(fila_busqueda)
        col.addWidget(separador())

        # -- selectores ------------------------------------------------------ #
        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(10)
        rejilla.setVerticalSpacing(6)

        rejilla.addWidget(etiqueta("Grupo", "seccion"), 0, 0)
        self.combo_grupo = QComboBox()
        self.combo_grupo.currentTextChanged.connect(self._cambiar_grupo)
        rejilla.addWidget(self.combo_grupo, 1, 0)

        rejilla.addWidget(etiqueta("Magnitud", "seccion"), 0, 1)
        self.combo_categoria = QComboBox()
        self.combo_categoria.currentTextChanged.connect(self._cambiar_categoria)
        rejilla.addWidget(self.combo_categoria, 1, 1)
        rejilla.setColumnStretch(0, 1)
        rejilla.setColumnStretch(1, 2)
        col.addLayout(rejilla)

        self.nota_categoria = etiqueta("", "nota", ajustar=True)
        col.addWidget(self.nota_categoria)

        # -- valor y unidades ------------------------------------------------ #
        conversion = QGridLayout()
        conversion.setHorizontalSpacing(10)
        conversion.setVerticalSpacing(6)

        conversion.addWidget(etiqueta("Valor", "seccion"), 0, 0)
        self.campo_valor = CampoNumerico("1")
        self.campo_valor.setText("1")
        self.campo_valor.textChanged.connect(self._convertir_en_vivo)
        self.campo_valor.aceptado.connect(self.convertir)
        conversion.addWidget(self.campo_valor, 1, 0)

        conversion.addWidget(etiqueta("De", "seccion"), 0, 1)
        self.combo_origen = QComboBox()
        self.combo_origen.currentIndexChanged.connect(self._convertir_en_vivo)
        conversion.addWidget(self.combo_origen, 1, 1)

        self.btn_invertir = boton("⇄", "", self._invertir,
                                  tooltip="Intercambiar las unidades de origen y destino")
        self.btn_invertir.setFixedWidth(42)
        conversion.addWidget(self.btn_invertir, 1, 2)

        conversion.addWidget(etiqueta("A", "seccion"), 0, 3)
        self.combo_destino = QComboBox()
        self.combo_destino.currentIndexChanged.connect(self._convertir_en_vivo)
        conversion.addWidget(self.combo_destino, 1, 3)

        conversion.setColumnStretch(0, 1)
        conversion.setColumnStretch(1, 2)
        conversion.setColumnStretch(3, 2)
        col.addLayout(conversion)

        # -- resultado ------------------------------------------------------- #
        self.resultado = etiqueta("", "resultado", ajustar=True)
        self.resultado.setMinimumHeight(28)
        col.addWidget(self.resultado)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Convertir y guardar", "primario", self.convertir))
        acciones.addWidget(boton("Copiar resultado", "", self._copiar))
        acciones.addStretch()
        col.addLayout(acciones)
        columna.addWidget(marco)

        # -- tabla con todas las unidades ------------------------------------ #
        marco_tabla, col_tabla = tarjeta()
        col_tabla.addWidget(etiqueta("Equivalencia en todas las unidades", "seccion"))
        self.tabla = TablaResultados()
        self.tabla.setHorizontalHeaderLabels(["Unidad", "Valor"])
        col_tabla.addWidget(self.tabla)
        columna.addWidget(marco_tabla, 1)

        return contenedor

    # ------------------------------------------------------------ selectores -- #

    def _cargar_grupos(self) -> None:
        self._cargando = True
        self.combo_grupo.clear()
        self.combo_grupo.addItems(list(uni.GRUPOS.keys()))
        self._cargando = False
        self._cambiar_grupo(self.combo_grupo.currentText())

    def _cambiar_grupo(self, grupo: str) -> None:
        if self._cargando or not grupo:
            return
        self._cargando = True
        self.combo_categoria.clear()
        self.combo_categoria.addItems(uni.GRUPOS.get(grupo, []))
        self._cargando = False
        self._cambiar_categoria(self.combo_categoria.currentText())

    def _cambiar_categoria(self, nombre: str) -> None:
        if self._cargando or not nombre:
            return
        categoria = uni.categoria(nombre)
        self._cargando = True
        self.combo_origen.clear()
        self.combo_destino.clear()
        for unidad in categoria.unidades:
            self.combo_origen.addItem(unidad.etiqueta, unidad.simbolo)
            self.combo_destino.addItem(unidad.etiqueta, unidad.simbolo)
        self.combo_origen.setCurrentIndex(0)
        self.combo_destino.setCurrentIndex(1 if len(categoria.unidades) > 1 else 0)
        self.nota_categoria.setText(categoria.nota)
        self.nota_categoria.setVisible(bool(categoria.nota))
        self._cargando = False
        self._convertir_en_vivo()

    def _invertir(self) -> None:
        origen, destino = self.combo_origen.currentIndex(), self.combo_destino.currentIndex()
        self._cargando = True
        self.combo_origen.setCurrentIndex(destino)
        self.combo_destino.setCurrentIndex(origen)
        self._cargando = False
        self._convertir_en_vivo()

    # -------------------------------------------------------------- cálculo -- #

    def _datos_actuales(self) -> tuple[float, str, str, str] | None:
        """(valor, símbolo origen, símbolo destino, categoría) o ``None``."""
        nombre_categoria = self.combo_categoria.currentText()
        origen = self.combo_origen.currentData()
        destino = self.combo_destino.currentData()
        if not (nombre_categoria and origen and destino):
            return None
        try:
            valor = self.campo_valor.valor()
        except ValueError:
            return None
        return valor, origen, destino, nombre_categoria

    def _convertir_en_vivo(self) -> None:
        """Actualiza el resultado y la tabla sin escribir en el historial."""
        if self._cargando:
            return
        datos = self._datos_actuales()
        if datos is None:
            self.resultado.clear()
            self.tabla.limpiar()
            return

        valor, origen, destino, nombre_categoria = datos
        decimales = config["decimales"]
        try:
            resultado = uni.convertir(valor, origen, destino, nombre_categoria)
        except uni.ErrorConversion as e:
            self.resultado.setText(str(e))
            self.resultado.setProperty("clase", "error")
            self._refrescar_estilo(self.resultado)
            self.tabla.limpiar()
            return

        self.resultado.setProperty("clase", "resultado")
        self._refrescar_estilo(self.resultado)
        self.resultado.setText(
            f"{formatear(valor, decimales)} {origen}  =  "
            f"{formatear(resultado, decimales)} {destino}"
        )

        try:
            filas = uni.tabla_completa(valor, origen, nombre_categoria)
        except uni.ErrorConversion:
            filas = []
        self.tabla.mostrar([
            (unidad.etiqueta, formatear(v, decimales)) for unidad, v in filas
        ])

    def convertir(self) -> None:
        datos = self._datos_actuales()
        if datos is None:
            aviso(self, "Introduzca un valor numérico válido.", "Conversión")
            return

        valor, origen, destino, nombre_categoria = datos
        try:
            resultado = uni.convertir(valor, origen, destino, nombre_categoria)
        except uni.ErrorConversion as e:
            aviso(self, str(e), "Conversión")
            return

        self._convertir_en_vivo()
        decimales = config["decimales"]
        operacion = (
            f"{formatear(valor, decimales)} {origen} → "
            f"{formatear(resultado, decimales)} {destino}  ({nombre_categoria})"
        )
        try:
            entrada = hist.guardar("conversiones", operacion, {
                "valor": valor,
                "origen": origen,
                "destino": destino,
                "categoria": nombre_categoria,
                "grupo": self.combo_grupo.currentText(),
            })
            self.historial.anadir(entrada)
        except hist.ErrorHistorial as e:
            aviso(self, str(e), "Historial")

    # -------------------------------------------------------------- búsqueda -- #

    def _buscar_unidad(self) -> None:
        consulta = self.buscador.text().strip()
        if not consulta:
            return
        coincidencias = uni.buscar(consulta)
        if not coincidencias:
            aviso(self, f"No se encontró ninguna unidad que contenga «{consulta}».", "Búsqueda")
            return

        nombre_categoria, unidad = coincidencias[0]
        self._ir_a(nombre_categoria, unidad.simbolo)
        if len(coincidencias) > 1:
            otras = ", ".join(
                f"{u.simbolo} ({c})" for c, u in coincidencias[1:6]
            )
            self.nota_categoria.setText(f"Otras coincidencias: {otras}")
            self.nota_categoria.setVisible(True)

    def _ir_a(self, nombre_categoria: str, simbolo: str) -> None:
        categoria = uni.categoria(nombre_categoria)
        self.combo_grupo.setCurrentText(categoria.grupo)
        self.combo_categoria.setCurrentText(nombre_categoria)
        indice = self.combo_origen.findData(simbolo)
        if indice >= 0:
            self.combo_origen.setCurrentIndex(indice)

    # ---------------------------------------------------------------- varios -- #

    @staticmethod
    def _refrescar_estilo(widget: QWidget) -> None:
        """Fuerza a Qt a releer el selector ``[clase="…"]`` tras cambiarlo."""
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.resultado.text())

    def _restaurar(self, datos: dict) -> None:
        nombre_categoria = datos.get("categoria")
        if not nombre_categoria or nombre_categoria not in uni.CATEGORIAS:
            return
        self._ir_a(nombre_categoria, datos.get("origen", ""))
        indice_destino = self.combo_destino.findData(datos.get("destino", ""))
        if indice_destino >= 0:
            self.combo_destino.setCurrentIndex(indice_destino)
        valor = datos.get("valor")
        if valor is not None:
            self.campo_valor.poner(float(valor))

    def aplicar_paleta(self, paleta) -> None:
        return
