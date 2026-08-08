"""Graficador de funciones: varias curvas a la vez, con cortes y análisis."""

from __future__ import annotations

import numpy as np
import sympy as sp
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QGridLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QSplitter,
    QVBoxLayout, QWidget,
)

from ..core import simbolico as sim
from ..core.config import config
from . import tema
from .comunes import PanelModulo, CampoNumerico, aviso, boton, etiqueta, separador, tarjeta
from .grafica import CICLO, PanelGrafica, cortar_saltos, muestrear

MAX_FUNCIONES = 4
PUNTOS = 2000

EJEMPLOS = [
    ["sin(x)", "cos(x)", "", ""],
    ["x^2 - 4", "2x + 1", "", ""],
    ["1/x", "", "", ""],
    ["exp(-x^2)", "", "", ""],
    ["x^3 - 3x", "3x^2 - 3", "", ""],
]


class PanelGraficador(PanelModulo):
    MODULO = "graficador"
    TITULO_HISTORIAL = "Historial"

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.paleta = tema.paleta(config["tema"])
        self._ejemplo_actual = -1
        self._construir()
        self._cargar_ejemplo()

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_izquierda())
        division.addWidget(self._crear_columna_derecha())
        division.setSizes([380, 760])
        raiz.addWidget(division)

    def _crear_columna_izquierda(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Funciones de x", "seccion"))

        self.campos: list[QLineEdit] = []
        for i in range(MAX_FUNCIONES):
            fila = QHBoxLayout()
            fila.setSpacing(6)
            punto = etiqueta("●")
            punto.setStyleSheet(f"color: {CICLO[i]}; font-size: 18px;")
            punto.setFixedWidth(16)
            fila.addWidget(punto)

            campo = QLineEdit()
            campo.setPlaceholderText("f(x) = " + ("sin(x)" if i == 0 else "…"))
            campo.returnPressed.connect(self.dibujar)
            self.campos.append(campo)
            fila.addWidget(campo, 1)
            col.addLayout(fila)

        col.addWidget(separador())
        col.addWidget(etiqueta("Intervalo", "seccion"))

        rejilla = QGridLayout()
        rejilla.setHorizontalSpacing(8)
        rejilla.addWidget(etiqueta("x desde", "subtitulo"), 0, 0)
        self.x_min = CampoNumerico("-10")
        self.x_min.setText("-10")
        self.x_min.aceptado.connect(self.dibujar)
        rejilla.addWidget(self.x_min, 0, 1)

        rejilla.addWidget(etiqueta("hasta", "subtitulo"), 0, 2)
        self.x_max = CampoNumerico("10")
        self.x_max.setText("10")
        self.x_max.aceptado.connect(self.dibujar)
        rejilla.addWidget(self.x_max, 0, 3)
        col.addLayout(rejilla)

        self.chk_auto_y = QCheckBox("Ajustar el eje Y automáticamente")
        self.chk_auto_y.setChecked(True)
        self.chk_auto_y.setToolTip(
            "Recorta los picos de las asíntotas para que la curva se vea bien"
        )
        self.chk_auto_y.stateChanged.connect(self.dibujar)
        col.addWidget(self.chk_auto_y)

        self.chk_cortes = QCheckBox("Marcar los cortes con el eje X")
        self.chk_cortes.setChecked(True)
        self.chk_cortes.stateChanged.connect(self.dibujar)
        col.addWidget(self.chk_cortes)

        self.chk_derivada = QCheckBox("Superponer la derivada de la primera")
        self.chk_derivada.stateChanged.connect(self.dibujar)
        col.addWidget(self.chk_derivada)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Dibujar", "primario", self.dibujar))
        acciones.addWidget(boton("Ejemplo", "", self._cargar_ejemplo))
        acciones.addWidget(boton("Limpiar", "", self.limpiar))
        col.addLayout(acciones)
        col.addStretch()
        columna.addWidget(marco, 1)

        return contenedor

    def _crear_columna_derecha(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        self.grafica = PanelGrafica(self.paleta, 6.0, 4.0)
        self.grafica.setMinimumHeight(340)
        col.addWidget(self.grafica, 1)
        columna.addWidget(marco, 3)

        marco_info, col_info = tarjeta()
        col_info.addWidget(etiqueta("Datos de las funciones", "seccion"))
        self.informacion = QPlainTextEdit()
        self.informacion.setProperty("clase", "mono")
        self.informacion.setReadOnly(True)
        self.informacion.setPlaceholderText(
            "Escriba una función y pulse «Dibujar» para ver sus cortes, extremos y límites."
        )
        col_info.addWidget(self.informacion, 1)
        columna.addWidget(marco_info, 2)

        return contenedor

    # -------------------------------------------------------------- dibujo -- #

    def _leer_intervalo(self) -> tuple[float, float]:
        try:
            minimo = self.x_min.valor()
            maximo = self.x_max.valor()
        except ValueError as e:
            raise sim.ErrorSimbolico(str(e)) from None
        if minimo >= maximo:
            raise sim.ErrorSimbolico("El extremo izquierdo debe ser menor que el derecho")
        if maximo - minimo > 1e7:
            raise sim.ErrorSimbolico("El intervalo es demasiado ancho")
        return minimo, maximo

    def dibujar(self) -> None:
        textos = [c.text().strip() for c in self.campos]
        activos = [(i, t) for i, t in enumerate(textos) if t]

        if not activos:
            self.grafica.lienzo.limpiar("Escriba al menos una función")
            self.informacion.clear()
            return

        try:
            minimo, maximo = self._leer_intervalo()
        except sim.ErrorSimbolico as e:
            aviso(self, str(e), "Intervalo")
            return

        variable = sp.Symbol("x")
        curvas: list[tuple[int, str, sp.Expr]] = []
        for indice, texto_funcion in activos:
            try:
                expresion = sim.analizar(texto_funcion)
            except sim.ErrorSimbolico as e:
                aviso(self, f"Función {indice + 1}: {e}", "No se entiende la función")
                return
            libres = sim.incognitas(expresion)
            if len(libres) > 1:
                aviso(self, f"La función {indice + 1} tiene más de una variable "
                            f"({', '.join(s.name for s in libres)}). Use sólo «x».",
                      "Varias variables")
                return
            if libres:
                variable = libres[0]
            curvas.append((indice, texto_funcion, expresion))

        if self.chk_derivada.isChecked() and curvas:
            indice, texto_funcion, expresion = curvas[0]
            derivada = sp.diff(expresion, variable)
            curvas.append((MAX_FUNCIONES, f"d/d{variable}({texto_funcion})", derivada))

        eje = self.grafica.lienzo.nuevo_eje()
        xs = np.linspace(minimo, maximo, PUNTOS)
        todos_los_valores: list[np.ndarray] = []
        informe: list[str] = []

        for indice, texto_funcion, expresion in curvas:
            try:
                funcion = sim.a_funcion(expresion, variable)
            except sim.ErrorSimbolico:
                informe.append(f"f{indice + 1}({variable}) = {texto_funcion}"
                               f"\n   no se puede representar\n")
                continue

            ys = cortar_saltos(muestrear(funcion, xs))
            if np.all(np.isnan(ys)):
                informe.append(f"f{indice + 1}({variable}) = {texto_funcion}"
                               f"\n   no toma valores reales en este intervalo\n")
                continue

            todos_los_valores.append(ys)
            es_derivada = indice == MAX_FUNCIONES
            eje.plot(
                xs, ys,
                color=CICLO[indice % len(CICLO)],
                linewidth=1.6,
                linestyle="--" if es_derivada else "-",
                label=texto_funcion if es_derivada else f"f{indice + 1} = {texto_funcion}",
            )

            if not es_derivada:
                informe.append(self._describir(texto_funcion, expresion, variable,
                                               minimo, maximo, eje, indice))

        if not todos_los_valores:
            self.grafica.lienzo.limpiar("Ninguna función se puede representar aquí")
            self.informacion.setPlainText("\n".join(informe))
            return

        if self.chk_auto_y.isChecked():
            self.grafica.lienzo.acotar_vertical(eje, np.concatenate(todos_los_valores))

        self.grafica.lienzo.estilizar(
            eje, etiqueta_x=str(variable), etiqueta_y="y", leyenda=True
        )
        self.informacion.setPlainText("\n".join(informe))
        self._guardar(textos, minimo, maximo)

    def _describir(self, texto_funcion: str, expresion: sp.Expr, variable: sp.Symbol,
                   minimo: float, maximo: float, eje, indice: int) -> str:
        """Cortes, extremos y límites de una curva, marcándolos en la gráfica."""
        lineas = [f"f{indice + 1}({variable}) = {sim.texto(expresion)}"]

        raices: list[float] = []
        try:
            candidatas = sp.solve(sp.Eq(expresion, 0), variable)
            for candidata in candidatas:
                if candidata.free_symbols or not sim.es_real(candidata):
                    continue
                valor = float(sp.re(sp.N(candidata)))
                if minimo <= valor <= maximo:
                    raices.append(valor)
        except (ValueError, TypeError, NotImplementedError):
            pass

        if raices:
            lineas.append("   cortes con el eje X: " +
                          ", ".join(f"{v:.6g}" for v in sorted(raices)[:10]))
            if self.chk_cortes.isChecked():
                eje.plot(sorted(raices), [0] * len(raices), "o",
                         color=CICLO[indice % len(CICLO)], markersize=6,
                         markeredgecolor=self.paleta.grafico_fondo, zorder=5)
        else:
            lineas.append("   cortes con el eje X: ninguno en este intervalo")

        try:
            corte_y = sp.N(expresion.subs(variable, 0), 8)
            if corte_y.is_real:
                lineas.append(f"   corte con el eje Y: {corte_y}")
        except (TypeError, ValueError, ZeroDivisionError):
            lineas.append("   corte con el eje Y: no está definida en 0")

        try:
            criticos = sp.solve(sp.Eq(sp.diff(expresion, variable), 0), variable)
            extremos = []
            for punto in criticos:
                if punto.free_symbols or not sim.es_real(punto):
                    continue
                valor = float(sp.re(sp.N(punto)))
                if not minimo <= valor <= maximo:
                    continue
                curvatura = sp.N(sp.diff(expresion, variable, 2).subs(variable, punto))
                tipo = "mín" if curvatura > 0 else "máx" if curvatura < 0 else "inflexión"
                extremos.append(f"{tipo} en x={valor:.6g}")
            if extremos:
                lineas.append("   extremos: " + ", ".join(extremos[:8]))
        except (ValueError, TypeError, NotImplementedError):
            pass

        for etiqueta_limite, destino in (("+∞", sp.oo), ("−∞", -sp.oo)):
            try:
                limite = sp.limit(expresion, variable, destino)
                lineas.append(f"   límite en {etiqueta_limite}: {limite}")
            except (ValueError, TypeError, NotImplementedError):
                pass

        return "\n".join(lineas) + "\n"

    # ---------------------------------------------------------------- varios -- #

    def _guardar(self, textos: list[str], minimo: float, maximo: float) -> None:
        activas = [t for t in textos if t]
        operacion = f"{'  |  '.join(activas)}   en [{minimo:g}, {maximo:g}]"
        self.guardar_en_historial(operacion, {
            "funciones": textos,
            "x_min": minimo,
            "x_max": maximo,
        })

    def limpiar(self) -> None:
        for campo in self.campos:
            campo.clear()
        self.informacion.clear()
        self.grafica.lienzo.limpiar("Escriba una función y pulse «Dibujar»")
        self.campos[0].setFocus()

    def _cargar_ejemplo(self) -> None:
        self._ejemplo_actual = (self._ejemplo_actual + 1) % len(EJEMPLOS)
        for campo, texto_funcion in zip(self.campos, EJEMPLOS[self._ejemplo_actual]):
            campo.setText(texto_funcion)
        self.x_min.setText("-10")
        self.x_max.setText("10")
        self.dibujar()

    def restaurar_datos(self, datos: dict) -> None:
        funciones = datos.get("funciones") or []
        for campo, texto_funcion in zip(self.campos, funciones):
            campo.setText(str(texto_funcion))
        if "x_min" in datos:
            self.x_min.poner(float(datos["x_min"]))
        if "x_max" in datos:
            self.x_max.poner(float(datos["x_max"]))
        self.dibujar()

    def aplicar_paleta(self, paleta) -> None:
        self.paleta = paleta
        self.grafica.aplicar_paleta(paleta)
        self.dibujar()
