"""Números complejos: aritmética, forma polar, De Moivre y plano de Argand."""

from __future__ import annotations

import math

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QSplitter, QVBoxLayout, QWidget,
)

from ..core import complejos as cpx
from ..core.config import config
from . import tema
from .comunes import (
    PanelModulo,
    CampoNumerico, TablaResultados, aviso, boton, etiqueta,
    separador, tarjeta,
)
from .grafica import CICLO, PanelGrafica


class PanelComplejos(PanelModulo):
    MODULO = "complejos"
    TITULO_HISTORIAL = "Historial"

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.paleta = tema.paleta(config["tema"])
        self._construir()
        self._cambiar_operacion(0)

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_entrada())
        division.addWidget(self._crear_columna_salida())


        division.setSizes([340, 520])
        raiz.addWidget(division)

    def _crear_columna_entrada(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Operación", "seccion"))
        self.combo = QComboBox()
        self.combo.addItems([titulo for _, titulo, _, _ in cpx.OPERACIONES])
        self.combo.currentIndexChanged.connect(self._cambiar_operacion)
        col.addWidget(self.combo)

        col.addWidget(separador())

        formulario = QFormLayout()
        formulario.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        formulario.setHorizontalSpacing(10)
        formulario.setVerticalSpacing(7)

        self.campo_z1 = QLineEdit()
        self.campo_z1.setPlaceholderText("3+4i    ·    5∠53.13")
        self.campo_z1.setText("3+4i")
        self.campo_z1.returnPressed.connect(self.calcular)
        formulario.addRow("z₁ =", self.campo_z1)

        self.campo_z2 = QLineEdit()
        self.campo_z2.setPlaceholderText("1-2i")
        self.campo_z2.setText("1-2i")
        self.campo_z2.returnPressed.connect(self.calcular)
        self.etiqueta_z2 = etiqueta("z₂ =")
        formulario.addRow(self.etiqueta_z2, self.campo_z2)

        self.campo_extra = CampoNumerico("2")
        self.campo_extra.setText("2")
        self.campo_extra.aceptado.connect(self.calcular)
        self.etiqueta_extra = etiqueta("n =")
        formulario.addRow(self.etiqueta_extra, self.campo_extra)

        col.addLayout(formulario)

        self.ayuda = etiqueta(
            "Formas admitidas: binómica (3+4i, -2i, 5) y polar en grados (5∠53.13). "
            "Para radianes añada «rad»: 5∠0.927rad.",
            "nota", ajustar=True,
        )
        col.addWidget(self.ayuda)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Calcular", "primario", self.calcular))
        acciones.addWidget(boton("Intercambiar", "", self._intercambiar,
                                 tooltip="Intercambiar z₁ y z₂"))
        col.addLayout(acciones)
        col.addStretch()

        columna.addWidget(marco, 1)
        return contenedor

    def _crear_columna_salida(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco_res, col_res = tarjeta()
        col_res.addWidget(etiqueta("Resultado", "seccion"))
        self.tabla = TablaResultados()
        self.tabla.setHorizontalHeaderLabels(["Concepto", "Valor"])
        col_res.addWidget(self.tabla, 1)
        fila = QHBoxLayout()
        fila.addWidget(boton("Copiar", "", self._copiar))
        fila.addStretch()
        col_res.addLayout(fila)
        columna.addWidget(marco_res, 3)

        marco_graf, col_graf = tarjeta()
        col_graf.addWidget(etiqueta("Plano de Argand", "seccion"))
        self.grafica = PanelGrafica(self.paleta, 4.2, 3.4, con_barra=False)
        self.grafica.setMinimumHeight(250)
        col_graf.addWidget(self.grafica, 1)
        columna.addWidget(marco_graf, 2)

        return contenedor

    # ---------------------------------------------------------- operaciones -- #

    def _operacion_actual(self) -> tuple[str, str, int, str | None]:
        return cpx.OPERACIONES[self.combo.currentIndex()]

    def _cambiar_operacion(self, _indice: int) -> None:
        clave, _, operandos, extra = self._operacion_actual()

        necesita_z2 = operandos == 2
        self.campo_z2.setVisible(necesita_z2)
        self.etiqueta_z2.setVisible(necesita_z2)

        self.campo_extra.setVisible(bool(extra))
        self.etiqueta_extra.setVisible(bool(extra))
        if extra:
            self.etiqueta_extra.setText(f"{extra} =")
            self.campo_extra.setText("2" if clave == "potencia" else "3")

        self.tabla.limpiar()
        self.grafica.lienzo.limpiar("Pulse «Calcular»")

    def calcular(self) -> None:
        clave, titulo, operandos, extra = self._operacion_actual()
        decimales = config["decimales"]

        try:
            z1 = cpx.analizar_complejo(self.campo_z1.text(), "z₁")
            z2 = cpx.analizar_complejo(self.campo_z2.text(), "z₂") if operandos == 2 else None
            n = self.campo_extra.valor() if extra else None
        except (cpx.ErrorComplejo, ValueError) as e:
            aviso(self, str(e), "Números complejos")
            return

        try:
            if clave == "ficha":
                filas = cpx.ficha(z1, decimales)
            elif clave == "potencia":
                filas = cpx.potencia(z1, n, decimales)
            elif clave == "raices":
                filas = cpx.raices(z1, int(n), decimales)
            else:
                filas = cpx.operar(clave, z1, z2, decimales)
        except cpx.ErrorComplejo as e:
            aviso(self, str(e), "Números complejos")
            return

        self.tabla.mostrar(filas)
        self._dibujar(clave, z1, z2, n)

        resumen = next((v for k, v in filas if k in (
            "Resultado", "z₁ + z₂", "z₁ − z₂", "z₁ · z₂", "z₁ / z₂", "Forma polar",
        )), "")
        self._guardar(f"{titulo}: {cpx.binomica(z1, 4)}  →  {resumen}", {
            "operacion": clave,
            "z1": self.campo_z1.text(),
            "z2": self.campo_z2.text(),
            "extra": self.campo_extra.text(),
        })

    # -------------------------------------------------------------- gráfica -- #

    def _dibujar(self, clave: str, z1: complex, z2: complex | None, n: float | None) -> None:
        eje = self.grafica.lienzo.nuevo_eje()
        puntos: list[tuple[complex, str, str]] = []

        if clave == "raices" and n:
            raices = cpx.lista_raices(z1, int(n))
            radio = abs(raices[0]) if raices else abs(z1)
            # La circunferencia sobre la que se reparten todas las raíces.
            angulos = np.linspace(0, 2 * math.pi, 200)
            eje.plot(radio * np.cos(angulos), radio * np.sin(angulos),
                     color=self.paleta.grafico_rejilla, linewidth=1.0, linestyle="--")
            for i, raiz in enumerate(raices):
                puntos.append((raiz, f"w{i}", CICLO[i % len(CICLO)]))
        elif clave == "potencia" and n is not None:
            puntos.append((z1, "z", CICLO[0]))
            try:
                puntos.append((z1 ** n, "zⁿ", CICLO[1]))
            except (OverflowError, ValueError):
                pass
        elif z2 is not None:
            puntos.append((z1, "z₁", CICLO[0]))
            puntos.append((z2, "z₂", CICLO[1]))
            operaciones = {
                "sumar": (z1 + z2, "z₁+z₂"),
                "restar": (z1 - z2, "z₁−z₂"),
                "multiplicar": (z1 * z2, "z₁·z₂"),
                "dividir": ((z1 / z2, "z₁/z₂") if z2 != 0 else None),
            }
            resultado = operaciones.get(clave)
            if resultado:
                puntos.append((resultado[0], resultado[1], CICLO[2]))
        else:
            puntos.append((z1, "z", CICLO[0]))
            puntos.append((z1.conjugate(), "z̄", CICLO[1]))

        for valor, nombre, color in puntos:
            if not (math.isfinite(valor.real) and math.isfinite(valor.imag)):
                continue
            # Cada complejo se dibuja como el vector que va del origen al punto.
            eje.annotate(
                "", xy=(valor.real, valor.imag), xytext=(0, 0),
                arrowprops=dict(arrowstyle="->", color=color, linewidth=1.7),
            )
            eje.plot(valor.real, valor.imag, "o", color=color, markersize=7,
                     markeredgecolor=self.paleta.grafico_fondo, label=nombre)
            eje.annotate(nombre, xy=(valor.real, valor.imag),
                         xytext=(6, 6), textcoords="offset points",
                         color=color, fontsize=9)

        finitos = [p for p, _, _ in puntos
                   if math.isfinite(p.real) and math.isfinite(p.imag)]
        limite = max((max(abs(p.real), abs(p.imag)) for p in finitos), default=1.0)
        limite = max(limite, 1e-6) * 1.35
        eje.set_xlim(-limite, limite)
        eje.set_ylim(-limite, limite)
        eje.set_aspect("equal", adjustable="box")

        self.grafica.lienzo.estilizar(
            eje, etiqueta_x="parte real", etiqueta_y="parte imaginaria",
        )

    # ---------------------------------------------------------------- varios -- #

    def _intercambiar(self) -> None:
        z1, z2 = self.campo_z1.text(), self.campo_z2.text()
        self.campo_z1.setText(z2)
        self.campo_z2.setText(z1)
        self.calcular()

    def _guardar(self, operacion: str, datos: dict) -> None:
        self.guardar_en_historial(operacion, datos)

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.tabla.texto_plano())

    def restaurar_datos(self, datos: dict) -> None:
        claves = [c for c, _, _, _ in cpx.OPERACIONES]
        clave = datos.get("operacion")
        if clave in claves:
            self.combo.setCurrentIndex(claves.index(clave))
        if datos.get("z1"):
            self.campo_z1.setText(str(datos["z1"]))
        if datos.get("z2"):
            self.campo_z2.setText(str(datos["z2"]))
        if datos.get("extra"):
            self.campo_extra.setText(str(datos["extra"]))
        self.calcular()

    def aplicar_paleta(self, paleta) -> None:
        self.paleta = paleta
        self.grafica.aplicar_paleta(paleta)
