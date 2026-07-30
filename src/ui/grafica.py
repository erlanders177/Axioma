"""Lienzo de matplotlib con el estilo de la aplicación.

Lo comparten el graficador, las ecuaciones, el cálculo, la estadística y el plano
complejo, de modo que todas las gráficas se ven igual y cambian de tema a la vez.
"""

from __future__ import annotations

import matplotlib
matplotlib.use("Qt5Agg")

import numpy as np
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg, NavigationToolbar2QT,
)
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QVBoxLayout, QWidget

from .tema import Paleta

#: Colores para superponer varias series; el primero es el de la paleta.
CICLO = ["#4c8dff", "#f0a020", "#2ecc71", "#e5484d", "#a78bfa", "#22d3ee"]


class Lienzo(FigureCanvasQTAgg):
    """Lienzo con los ejes ya estilizados según la paleta activa."""

    def __init__(self, paleta: Paleta, ancho: float = 5.0, alto: float = 3.2,
                 padre: QWidget | None = None) -> None:
        self.paleta = paleta
        self.figura = Figure(figsize=(ancho, alto), dpi=100, layout="constrained")
        super().__init__(self.figura)
        if padre is not None:
            self.setParent(padre)
        self.limpiar()

    # -- ciclo de vida ----------------------------------------------------- #

    def aplicar_paleta(self, paleta: Paleta) -> None:
        self.paleta = paleta

    def limpiar(self, mensaje: str = "") -> None:
        self.figura.clear()
        self.figura.patch.set_facecolor(self.paleta.grafico_fondo)
        if mensaje:
            eje = self.figura.add_subplot(111)
            eje.set_facecolor(self.paleta.grafico_fondo)
            eje.axis("off")
            eje.text(0.5, 0.5, mensaje, ha="center", va="center", wrap=True,
                     color=self.paleta.texto_suave, fontsize=10)
        self.draw_idle()

    def nuevo_eje(self, proyeccion: str | None = None):
        """Crea unos ejes limpios listos para dibujar."""
        self.figura.clear()
        self.figura.patch.set_facecolor(self.paleta.grafico_fondo)
        eje = self.figura.add_subplot(111, projection=proyeccion)
        eje.set_facecolor(self.paleta.grafico_fondo)
        return eje

    # -- estilo ------------------------------------------------------------ #

    def estilizar(self, eje, *, titulo: str = "", etiqueta_x: str = "",
                  etiqueta_y: str = "", leyenda: bool = False,
                  ejes_cero: bool = True) -> None:
        eje.grid(True, color=self.paleta.grafico_rejilla, linewidth=0.5, alpha=0.6)
        eje.set_axisbelow(True)
        for lado in eje.spines.values():
            lado.set_color(self.paleta.grafico_rejilla)
        eje.tick_params(colors=self.paleta.texto_suave, labelsize=8)

        if ejes_cero:
            eje.axhline(0, color=self.paleta.grafico_rejilla, linewidth=1.0)
            eje.axvline(0, color=self.paleta.grafico_rejilla, linewidth=1.0)

        if titulo:
            eje.set_title(titulo, color=self.paleta.texto, fontsize=10, pad=6)
        if etiqueta_x:
            eje.set_xlabel(etiqueta_x, color=self.paleta.texto_suave, fontsize=9)
        if etiqueta_y:
            eje.set_ylabel(etiqueta_y, color=self.paleta.texto_suave, fontsize=9)

        if leyenda:
            marco = eje.legend(fontsize=8, facecolor=self.paleta.grafico_fondo,
                               edgecolor=self.paleta.grafico_rejilla, framealpha=0.9)
            if marco is not None:
                for texto in marco.get_texts():
                    texto.set_color(self.paleta.texto_suave)

        self.draw_idle()

    def acotar_vertical(self, eje, valores: np.ndarray, margen: float = 0.25) -> None:
        """Limita el eje Y ignorando los picos de las asíntotas.

        Sin esto, una función como 1/x hace que el autoescalado comprima toda la
        curva contra el eje horizontal.
        """
        finitos = valores[np.isfinite(valores)]
        if finitos.size == 0:
            return
        bajo, alto = np.percentile(finitos, [2, 98])
        if bajo == alto:
            bajo, alto = bajo - 1, alto + 1
        holgura = max(abs(alto - bajo) * margen, 1e-9)
        eje.set_ylim(bajo - holgura, alto + holgura)


class PanelGrafica(QWidget):
    """Lienzo con la barra de herramientas de matplotlib (zoom, arrastre, guardar)."""

    def __init__(self, paleta: Paleta, ancho: float = 5.0, alto: float = 3.2,
                 con_barra: bool = True, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.lienzo = Lienzo(paleta, ancho, alto, self)

        columna = QVBoxLayout(self)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(2)
        columna.addWidget(self.lienzo, 1)

        self.barra = None
        if con_barra:
            self.barra = NavigationToolbar2QT(self.lienzo, self)
            self.barra.setIconSize(self.barra.iconSize() * 0.75)
            self.barra.setStyleSheet("QToolBar { border: none; }")
            columna.addWidget(self.barra)

    def aplicar_paleta(self, paleta: Paleta) -> None:
        self.lienzo.aplicar_paleta(paleta)


def muestrear(funcion, xs: np.ndarray) -> np.ndarray:
    """Evalúa una función sobre ``xs`` dejando en ``NaN`` lo que no sea real.

    Así los tramos fuera del dominio y las asíntotas quedan como huecos en la
    curva en lugar de unirse con una línea vertical falsa.
    """
    with np.errstate(all="ignore"):
        try:
            valores = np.asarray(funcion(xs), dtype=complex)
        except Exception:
            return np.full(xs.shape, np.nan)

    # Una expresión constante devuelve un único valor: hay que extenderlo.
    if valores.shape != xs.shape:
        try:
            valores = np.broadcast_to(valores, xs.shape).copy()
        except ValueError:
            return np.full(xs.shape, np.nan)

    reales = np.where(np.abs(valores.imag) < 1e-9, valores.real, np.nan)
    return np.where(np.isfinite(reales), reales, np.nan)


def cortar_saltos(ys: np.ndarray, umbral: float = 50.0) -> np.ndarray:
    """Rompe la curva donde pega un salto brusco (asíntotas verticales)."""
    resultado = ys.copy()
    finitos = resultado[np.isfinite(resultado)]
    if finitos.size < 2:
        return resultado
    escala = np.percentile(np.abs(finitos), 95) or 1.0
    saltos = np.abs(np.diff(resultado)) > umbral * escala
    indices = np.flatnonzero(saltos)
    resultado[indices] = np.nan
    return resultado
