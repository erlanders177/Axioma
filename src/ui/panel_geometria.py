"""Calculadora geométrica: figuras planas y cuerpos en el espacio."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QSplitter, QVBoxLayout,
    QWidget,
)

from ..core import figuras as geo
from ..core import historial as hist
from ..core.config import config
from ..core.formato import formatear, normalizar
from . import tema
from .comunes import (
    CampoNumerico, PanelHistorial, TablaResultados, aviso, boton, etiqueta,
    separador, tarjeta,
)
from .visualizador import LienzoFigura


class PanelGeometria(QWidget):
    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._campos: dict[str, CampoNumerico] = {}
        self._cargando = False
        self._ultimo_calculo: tuple | None = None
        self._construir()
        self._cargar_grupos()

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_datos())
        division.addWidget(self._crear_columna_resultados())

        marco_hist, col_hist = tarjeta()
        self.historial = PanelHistorial("geometria", "Historial")
        self.historial.restaurar.connect(self._restaurar)
        col_hist.addWidget(self.historial)
        division.addWidget(marco_hist)

        division.setSizes([330, 470, 320])
        raiz.addWidget(division)

    def _crear_columna_datos(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()

        col.addWidget(etiqueta("Tipo", "seccion"))
        self.combo_grupo = QComboBox()
        self.combo_grupo.currentTextChanged.connect(self._cambiar_grupo)
        col.addWidget(self.combo_grupo)

        col.addWidget(etiqueta("Figura", "seccion"))
        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Filtrar figuras…")
        self.buscador.setClearButtonEnabled(True)
        self.buscador.textChanged.connect(self._filtrar_figuras)
        col.addWidget(self.buscador)

        self.combo_figura = QComboBox()
        self.combo_figura.currentTextChanged.connect(self._cambiar_figura)
        col.addWidget(self.combo_figura)

        col.addWidget(separador())
        col.addWidget(etiqueta("Datos", "seccion"))

        self.formulario = QFormLayout()
        self.formulario.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.formulario.setHorizontalSpacing(10)
        self.formulario.setVerticalSpacing(7)
        # Con etiquetas largas, la fila pasa a dos líneas en lugar de recortarse.
        self.formulario.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.formulario.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        col.addLayout(self.formulario)

        self.nota_figura = etiqueta("", "nota", ajustar=True)
        col.addWidget(self.nota_figura)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Calcular y guardar", "primario", self._calcular_y_guardar))
        acciones.addWidget(boton("Ejemplo", "", self._rellenar_ejemplo,
                                 tooltip="Rellenar con valores de ejemplo"))
        col.addLayout(acciones)
        col.addStretch()

        columna.addWidget(marco, 1)
        return contenedor

    def _crear_columna_resultados(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco_vista, col_vista = tarjeta()
        col_vista.addWidget(etiqueta("Vista previa", "seccion"))
        self.lienzo = LienzoFigura(tema.paleta(config["tema"]))
        self.lienzo.setMinimumHeight(230)
        col_vista.addWidget(self.lienzo, 1)
        columna.addWidget(marco_vista, 1)

        marco_res, col_res = tarjeta()
        col_res.addWidget(etiqueta("Resultados", "seccion"))
        self.tabla = TablaResultados()
        col_res.addWidget(self.tabla, 1)

        self.formulas = etiqueta("", "nota", ajustar=True)
        col_res.addWidget(self.formulas)

        fila = QHBoxLayout()
        fila.addWidget(boton("Copiar resultados", "", self._copiar))
        fila.addStretch()
        col_res.addLayout(fila)
        columna.addWidget(marco_res, 1)

        return contenedor

    # ----------------------------------------------------------- selectores -- #

    def _cargar_grupos(self) -> None:
        self._cargando = True
        self.combo_grupo.clear()
        self.combo_grupo.addItem("Todas")
        self.combo_grupo.addItems(list(geo.GRUPOS.keys()))
        self._cargando = False
        self._cambiar_grupo("Todas")

    def _nombres_visibles(self) -> list[str]:
        grupo = self.combo_grupo.currentText()
        if grupo and grupo != "Todas":
            nombres = geo.GRUPOS.get(grupo, [])
        else:
            nombres = list(geo.FIGURAS.keys())

        filtro = normalizar(self.buscador.text().strip())
        if filtro:
            nombres = [n for n in nombres if filtro in normalizar(n)]
        return nombres

    def _cambiar_grupo(self, _grupo: str) -> None:
        if self._cargando:
            return
        self._recargar_figuras()

    def _filtrar_figuras(self, _texto: str) -> None:
        if self._cargando:
            return
        self._recargar_figuras()

    def _recargar_figuras(self) -> None:
        anterior = self.combo_figura.currentText()
        nombres = self._nombres_visibles()

        self._cargando = True
        self.combo_figura.clear()
        self.combo_figura.addItems(nombres)
        self._cargando = False

        if not nombres:
            self._limpiar_formulario()
            self.tabla.limpiar()
            self.lienzo.limpiar("Ningún resultado para ese filtro")
            self.formulas.clear()
            return

        indice = nombres.index(anterior) if anterior in nombres else 0
        self.combo_figura.setCurrentIndex(indice)
        self._cambiar_figura(nombres[indice])

    def _limpiar_formulario(self) -> None:
        self._campos.clear()
        while self.formulario.count():
            elemento = self.formulario.takeAt(0)
            widget = elemento.widget()
            if widget is not None:
                widget.deleteLater()

    def _cambiar_figura(self, nombre: str) -> None:
        if self._cargando or not nombre:
            return
        figura = geo.figura(nombre)

        self._limpiar_formulario()
        for parametro in figura.parametros:
            campo = CampoNumerico(_marcador(parametro))
            campo.aceptado.connect(self._calcular_y_guardar)
            if parametro.ayuda:
                campo.setToolTip(parametro.ayuda)
            self._campos[parametro.simbolo] = campo
            sufijo = f" ({parametro.unidad})" if parametro.unidad not in ("", "u") else ""
            self.formulario.addRow(f"{parametro.etiqueta}{sufijo}:", campo)

        self.nota_figura.setText(figura.nota)
        self.nota_figura.setVisible(bool(figura.nota))
        self.formulas.setText(
            "Fórmulas:  " + "     ".join(figura.formulas) if figura.formulas else ""
        )
        self.tabla.limpiar()
        self.lienzo.limpiar("Introduzca los datos y pulse «Calcular»")
        self._rellenar_ejemplo()

    def _rellenar_ejemplo(self) -> None:
        nombre = self.combo_figura.currentText()
        if not nombre:
            return
        for parametro in geo.figura(nombre).parametros:
            campo = self._campos.get(parametro.simbolo)
            if campo is not None:
                campo.poner(parametro.predeterminado)
        self.calcular(silencioso=True)

    # -------------------------------------------------------------- cálculo -- #

    def _leer_valores(self) -> dict | None:
        valores: dict[str, float] = {}
        for simbolo, campo in self._campos.items():
            try:
                valor = campo.valor(obligatorio=False)
            except ValueError as e:
                aviso(self, str(e), "Datos incorrectos")
                campo.setFocus()
                return None
            if valor is None:
                return None
            valores[simbolo] = valor
        return valores

    def calcular(self, *, silencioso: bool = False) -> None:
        nombre = self.combo_figura.currentText()
        if not nombre:
            return
        figura = geo.figura(nombre)
        # Se invalida antes de calcular para que un fallo no deje que se guarde en
        # el historial el resultado anterior.
        self._ultimo_calculo = None

        valores = self._leer_valores()
        if valores is None:
            self.tabla.limpiar()
            self.lienzo.limpiar("Faltan datos por rellenar")
            return

        try:
            resultados = figura.calcular(valores)
        except geo.ErrorFigura as e:
            self.tabla.limpiar()
            self.lienzo.limpiar(str(e))
            if not silencioso:
                aviso(self, str(e), "Datos incorrectos")
            return
        except (ValueError, ArithmeticError) as e:
            self.tabla.limpiar()
            self.lienzo.limpiar("No se pudo calcular")
            if not silencioso:
                aviso(self, f"No se pudo calcular: {e}", "Error")
            return

        decimales = config["decimales"]
        self.tabla.mostrar([
            (r.etiqueta, formatear(r.valor, decimales, unidad=r.unidad))
            for r in resultados
        ])

        try:
            self.lienzo.dibujar(figura.primitivas(valores), nombre)
        except Exception:
            # Un fallo al dibujar nunca debe impedir ver los resultados.
            self.lienzo.limpiar("No se pudo generar la vista previa")

        self._ultimo_calculo = (nombre, valores, resultados)

    def _calcular_y_guardar(self) -> None:
        """Acción del botón principal: calcular y registrar en el historial."""
        self.calcular()
        self._guardar_en_historial()

    def _guardar_en_historial(self) -> None:
        datos = self._ultimo_calculo
        if datos is None:
            return
        nombre, valores, resultados = datos
        decimales = config["decimales"]
        resumen = ", ".join(
            f"{r.etiqueta}: {formatear(r.valor, decimales, unidad=r.unidad)}"
            for r in resultados[:3]
        )
        try:
            entrada = hist.guardar("geometria", f"{nombre} → {resumen}", {
                "figura": nombre,
                "valores": valores,
            })
            self.historial.anadir(entrada)
        except hist.ErrorHistorial as e:
            aviso(self, str(e), "Historial")

    # ---------------------------------------------------------------- varios -- #

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            nombre = self.combo_figura.currentText()
            portapapeles.setText(f"{nombre}\n{self.tabla.texto_plano()}")

    def _restaurar(self, datos: dict) -> None:
        nombre = datos.get("figura")
        if not nombre or nombre not in geo.FIGURAS:
            return
        self.buscador.clear()
        self.combo_grupo.setCurrentText("Todas")
        self.combo_figura.setCurrentText(nombre)
        for simbolo, valor in (datos.get("valores") or {}).items():
            campo = self._campos.get(simbolo)
            if campo is not None:
                campo.poner(float(valor))
        self.calcular(silencioso=True)

    def aplicar_paleta(self, paleta) -> None:
        self.lienzo.aplicar_paleta(paleta)
        self.calcular(silencioso=True)


def _marcador(parametro: geo.Parametro) -> str:
    """Texto de ayuda dentro del campo, con el rango admitido."""
    if parametro.entero:
        return "número entero"
    if parametro.unidad == "°":
        return "grados"
    return "valor"
