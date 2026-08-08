"""Un módulo con su historial, listo para engancharse a la pantalla.

La aplicación es **una sola pantalla**: la calculadora en el centro y los demás
apartados enganchados a su alrededor, varios a la vez. No se cambia de página.
Cada apartado es un bloque que se puede mover, apilar con otro o soltar fuera de
la ventana, y lleva **su propio historial**, porque el historial de una figura
geométrica no pinta nada mezclado con el de la calculadora.

El historial va plegado de partida: ocupa sitio sólo cuando se pide.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QScrollArea, QSplitter, QVBoxLayout, QWidget,
)

from .comunes import PanelHistorial, boton, tarjeta

#: Al desplegar el historial se reparte la altura, no se le da un tamaño fijo:
#: un bloque bajo (dos apartados en la misma columna) se quedaba sin panel.
PARTE_DEL_HISTORIAL = 0.32
#: Aun así el historial necesita un mínimo para que se lea alguna línea.
ALTO_MINIMO_HISTORIAL = 140

#: Por debajo de este ancho, las columnas del panel se apilan en vez de ponerse
#: una al lado de otra. Los paneles nacieron para ocupar la pantalla entera y
#: piden unos 800 px; enganchados de lado hay que dejarlos estrecharse o no
#: caben tres apartados a la vez.
ANCHO_ESTRECHO = 620
#: Se vuelve a dos columnas algo más arriba, para que no oscile al arrastrar.
ANCHO_HOLGADO = 720


class Apartado(QWidget):
    """Envoltura de un panel: él arriba, su historial abajo cuando se pide."""

    #: El usuario ha pedido volver a cargar una operación en este panel.
    restaurar = pyqtSignal(dict)

    def __init__(self, panel: QWidget, clave: str, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.panel = panel
        self.clave = clave
        self._construir(clave)

    def _construir(self, clave: str) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(6)

        self.division = QSplitter(Qt.Vertical)
        self.division.setChildrenCollapsible(False)

        # El panel va dentro de un área desplazable: así el bloque se puede
        # estrechar todo lo que haga falta para que quepan varios a la vez, en
        # lugar de imponer su ancho y desbordar la pantalla.
        self._marco_panel = QScrollArea()
        self._marco_panel.setWidget(self.panel)
        self._marco_panel.setWidgetResizable(True)
        self._marco_panel.setFrameShape(QFrame.NoFrame)
        self._marco_panel.setMinimumWidth(320)
        self.division.addWidget(self._marco_panel)

        marco, interior = tarjeta()
        self.historial = PanelHistorial(
            clave, getattr(self.panel, "TITULO_HISTORIAL", "Historial")
        )
        # La lista pide de suyo bastante alto; en un bloque bajo eso dejaba al
        # panel sin sitio, así que se le permite quedarse en dos o tres líneas.
        self.historial.lista.setMinimumHeight(64)
        self.historial.restaurar.connect(self.restaurar)
        interior.addWidget(self.historial)
        marco.setVisible(False)
        self._marco_historial = marco
        self.division.addWidget(marco)
        columna.addWidget(self.division, 1)

        pie = QHBoxLayout()
        pie.setContentsMargins(0, 0, 0, 0)
        pie.addStretch()
        self.btn_historial = boton(
            "Historial ▾", "", self.alternar_historial,
            tooltip="Mostrar u ocultar el historial de este apartado",
        )
        pie.addWidget(self.btn_historial)
        columna.addLayout(pie)

        # Lo que guarde el panel aparece en su historial al momento.
        if hasattr(self.panel, "guardado"):
            self.panel.guardado.connect(self._anotar)

    def _anotar(self, entrada: dict) -> None:
        self.historial.anadir(entrada)
        # Si el historial está plegado, el contador del botón es la única señal
        # de que ahí se ha guardado algo.
        if not self._marco_historial.isVisible():
            self.btn_historial.setText(f"Historial ({self.historial.lista.count()}) ▾")

    def alternar_historial(self, mostrar: bool | None = None) -> None:
        """Despliega o pliega el historial de este apartado."""
        visible = (not self._marco_historial.isVisible()) if mostrar is None else mostrar
        self._marco_historial.setVisible(visible)
        if visible:
            alto = max(self.division.height(), 400)
            historial = max(ALTO_MINIMO_HISTORIAL, int(alto * PARTE_DEL_HISTORIAL))
            # El máximo es lo que de verdad impide que el historial se coma el
            # panel: setSizes por sí solo cede ante el mínimo de los hijos.
            self._marco_historial.setMaximumHeight(historial)
            self.division.setSizes([alto - historial, historial])
            self.historial.recargar()
            self.btn_historial.setText("Historial ▴")
        else:
            self.btn_historial.setText("Historial ▾")

    # ------------------------------------------------------ adaptar al hueco -- #

    def _divisiones_del_panel(self) -> list[QSplitter]:
        """Los divisores del panel, sin contar el que separa su historial."""
        return [d for d in self.panel.findChildren(QSplitter) if d is not self.division]

    def ajustar_al_ancho(self, ancho: int) -> None:
        """Apila las columnas del panel si el hueco se ha quedado estrecho."""
        divisiones = self._divisiones_del_panel()
        if not divisiones:
            return
        apilar = ancho < ANCHO_ESTRECHO
        if not apilar and ancho < ANCHO_HOLGADO:
            return                      # zona muerta: se queda como esté
        destino = Qt.Vertical if apilar else Qt.Horizontal
        for division in divisiones:
            if division.orientation() != destino:
                division.setOrientation(destino)

    def resizeEvent(self, evento) -> None:  # noqa: N802 (nombre impuesto por Qt)
        super().resizeEvent(evento)
        self.ajustar_al_ancho(evento.size().width())

    def aplicar_paleta(self, paleta) -> None:
        if hasattr(self.panel, "aplicar_paleta"):
            self.panel.aplicar_paleta(paleta)
