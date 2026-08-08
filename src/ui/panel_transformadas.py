"""Transformadas de Laplace y de Fourier, y series de Fourier."""

from __future__ import annotations

import numpy as np
import sympy as sp
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QSpinBox, QSplitter,
    QVBoxLayout, QWidget,
)

from ..core import simbolico as sim
from ..core import transformadas as tr
from ..core.config import config
from . import tema
from .comunes import (
    PanelModulo,
    TablaResultados, aviso, boton, etiqueta, separador, tarjeta,
)
from .grafica import CICLO, PanelGrafica, cortar_saltos, muestrear

EJEMPLOS = {
    "laplace": "t^2",
    "laplace_inversa": "1/(s^2 + 4)",
    "fourier": "exp(-x^2)",
    "fourier_inversa": "exp(-k^2)",
    "serie": "x",
}


class PanelTransformadas(PanelModulo):
    MODULO = "transformadas"
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


        division.setSizes([350, 520])
        raiz.addWidget(division)

    def _crear_columna_entrada(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Operación", "seccion"))
        self.combo = QComboBox()
        self.combo.addItems([titulo for _, titulo, _ in tr.OPERACIONES])
        self.combo.currentIndexChanged.connect(self._cambiar_operacion)
        col.addWidget(self.combo)

        col.addWidget(separador())

        self.formulario = QFormLayout()
        self.formulario.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.formulario.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.formulario.setHorizontalSpacing(10)
        self.formulario.setVerticalSpacing(7)

        self.entrada = QLineEdit()
        self.entrada.returnPressed.connect(self.calcular)
        self.etiqueta_entrada = etiqueta("f(t) =")
        self.formulario.addRow(self.etiqueta_entrada, self.entrada)

        self.desde = QLineEdit("-pi")
        self.desde.returnPressed.connect(self.calcular)
        self.etiqueta_desde = etiqueta("Desde:")
        self.formulario.addRow(self.etiqueta_desde, self.desde)

        self.hasta = QLineEdit("pi")
        self.hasta.returnPressed.connect(self.calcular)
        self.etiqueta_hasta = etiqueta("Hasta:")
        self.formulario.addRow(self.etiqueta_hasta, self.hasta)

        self.spin_orden = QSpinBox()
        self.spin_orden.setRange(1, 30)
        self.spin_orden.setValue(5)
        self.etiqueta_orden = etiqueta("Orden:")
        self.formulario.addRow(self.etiqueta_orden, self.spin_orden)
        col.addLayout(self.formulario)

        self.nota = etiqueta("", "nota", ajustar=True)
        col.addWidget(self.nota)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Calcular", "primario", self.calcular))
        acciones.addWidget(boton("Ejemplo", "", self._cargar_ejemplo))
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

        self.marco_grafica, col_graf = tarjeta()
        col_graf.addWidget(etiqueta("Aproximación de la serie", "seccion"))
        self.grafica = PanelGrafica(self.paleta, 5.0, 2.8, con_barra=False)
        self.grafica.setMinimumHeight(210)
        col_graf.addWidget(self.grafica, 1)
        columna.addWidget(self.marco_grafica, 2)

        return contenedor

    # ---------------------------------------------------------- operaciones -- #

    @property
    def _clave(self) -> str:
        return tr.OPERACIONES[self.combo.currentIndex()][0]

    def _cambiar_operacion(self, _indice: int) -> None:
        clave = self._clave
        es_serie = clave == "serie"
        es_tabla = clave == "tabla"

        self.entrada.setVisible(not es_tabla)
        self.etiqueta_entrada.setVisible(not es_tabla)
        for widget in (self.desde, self.etiqueta_desde, self.hasta,
                       self.etiqueta_hasta, self.spin_orden, self.etiqueta_orden):
            widget.setVisible(es_serie)

        etiquetas = {
            "laplace": "f(t) =", "laplace_inversa": "F(s) =",
            "fourier": "f(x) =", "fourier_inversa": "F(k) =",
            "serie": "f(x) =",
        }
        self.etiqueta_entrada.setText(etiquetas.get(clave, "f ="))
        marcadores = {
            "laplace": "t^2     ·     exp(3*t)     ·     sin(2*t)",
            "laplace_inversa": "1/(s-2)     ·     1/(s^2+4)",
            "fourier": "exp(-x^2)",
            "fourier_inversa": "exp(-k^2)",
            "serie": "x     ·     x^2     ·     abs(x)",
        }
        self.entrada.setPlaceholderText(marcadores.get(clave, ""))
        self.entrada.setText(EJEMPLOS.get(clave, ""))

        self.marco_grafica.setVisible(es_serie)
        self.nota.setText(_NOTAS.get(clave, ""))
        self.tabla.limpiar()

        if es_tabla:
            self._mostrar_tabla_laplace()

    def calcular(self) -> None:
        clave = self._clave
        if clave == "tabla":
            self._mostrar_tabla_laplace()
            return

        expresion = self.entrada.text().strip()
        try:
            if clave == "laplace":
                filas = tr.laplace(expresion)
            elif clave == "laplace_inversa":
                filas = tr.laplace_inversa(expresion)
            elif clave == "fourier":
                filas = tr.fourier(expresion)
            elif clave == "fourier_inversa":
                filas = tr.fourier_inversa(expresion)
            else:
                filas = tr.serie_fourier(expresion, self.desde.text().strip() or "-pi",
                                         self.hasta.text().strip() or "pi",
                                         self.spin_orden.value())
        except tr.ErrorTransformada as e:
            self.tabla.limpiar()
            aviso(self, str(e), "Transformadas")
            return
        except sim.ErrorSimbolico as e:
            self.tabla.limpiar()
            aviso(self, str(e), "Transformadas")
            return
        except Exception as e:
            self.tabla.limpiar()
            aviso(self, f"No se pudo calcular ({type(e).__name__}: {e})", "Error")
            return

        self.tabla.mostrar(filas)

        if clave == "serie":
            self._dibujar_serie(expresion)

        resultado = next((v for k, v in filas
                          if k.startswith(("Transformada", "Serie truncada"))), "")
        self._guardar(f"{self.combo.currentText()}: {expresion} → {resultado}",
                      {"operacion": clave, "expresion": expresion,
                       "desde": self.desde.text(), "hasta": self.hasta.text(),
                       "orden": self.spin_orden.value()})

    def _mostrar_tabla_laplace(self) -> None:
        self.tabla.setHorizontalHeaderLabels(["f(t)", "F(s)  ·  condición"])
        self.tabla.mostrar([
            (funcion, f"{transformada}      ({condicion})")
            for funcion, transformada, condicion in tr.TABLA_LAPLACE
        ])

    # -------------------------------------------------------------- gráfica -- #

    def _dibujar_serie(self, expresion_texto: str) -> None:
        """Superpone la función original y su serie truncada.

        Es donde se ve el fenómeno de Gibbs: los picos que la serie no consigue
        eliminar en los saltos, por muchos términos que se añadan.
        """
        try:
            serie, _ = tr.coeficientes_fourier(
                expresion_texto, self.desde.text().strip() or "-pi",
                self.hasta.text().strip() or "pi", self.spin_orden.value(),
            )
            x = sp.Symbol("x", real=True)
            original = sim.analizar(expresion_texto, frozenset({"x"}), {"x": x})
            a = float(sp.N(sim.analizar(self.desde.text().strip() or "-pi")))
            b = float(sp.N(sim.analizar(self.hasta.text().strip() or "pi")))
            f_original = sp.lambdify(x, original, "numpy")
            f_serie = sp.lambdify(x, serie, "numpy")
        except Exception:
            self.grafica.lienzo.limpiar("No se pudo representar")
            return

        xs = np.linspace(a, b, 800)
        ys_original = cortar_saltos(muestrear(f_original, xs))
        ys_serie = cortar_saltos(muestrear(f_serie, xs))

        if np.all(np.isnan(ys_original)) and np.all(np.isnan(ys_serie)):
            self.grafica.lienzo.limpiar("No se pudo representar")
            return

        eje = self.grafica.lienzo.nuevo_eje()
        eje.plot(xs, ys_original, color=CICLO[0], linewidth=2.0, label="f(x)")
        eje.plot(xs, ys_serie, color=CICLO[1], linewidth=1.5, linestyle="--",
                 label=f"serie (orden {self.spin_orden.value()})")

        valores = np.concatenate([ys_original[np.isfinite(ys_original)],
                                  ys_serie[np.isfinite(ys_serie)]])
        if valores.size:
            self.grafica.lienzo.acotar_vertical(eje, valores)
        self.grafica.lienzo.estilizar(eje, etiqueta_x="x", leyenda=True)

    # ---------------------------------------------------------------- varios -- #

    def _guardar(self, operacion: str, datos: dict) -> None:
        self.guardar_en_historial(operacion, datos)

    def _cargar_ejemplo(self) -> None:
        self.entrada.setText(EJEMPLOS.get(self._clave, "t^2"))
        self.calcular()

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.tabla.texto_plano())

    def restaurar_datos(self, datos: dict) -> None:
        claves = [c for c, _, _ in tr.OPERACIONES]
        clave = datos.get("operacion")
        if clave in claves:
            self.combo.setCurrentIndex(claves.index(clave))
        if datos.get("expresion"):
            self.entrada.setText(str(datos["expresion"]))
        if datos.get("desde"):
            self.desde.setText(str(datos["desde"]))
        if datos.get("hasta"):
            self.hasta.setText(str(datos["hasta"]))
        if "orden" in datos:
            try:
                self.spin_orden.setValue(int(datos["orden"]))
            except (TypeError, ValueError):
                pass
        self.calcular()

    def aplicar_paleta(self, paleta) -> None:
        self.paleta = paleta
        self.grafica.aplicar_paleta(paleta)


_NOTAS = {
    "laplace": "Convierte una función del tiempo en una de s. Es lo que permite "
               "resolver ecuaciones diferenciales como si fueran algebraicas.",
    "laplace_inversa": "De vuelta al dominio del tiempo. Se descompone en "
                       "fracciones simples y se busca cada trozo en la tabla.",
    "fourier": "Descompone una señal en las frecuencias que la forman. Convenio "
               "F(k) = ∫ f(x)·e^(−2πikx) dx.",
    "fourier_inversa": "Reconstruye la señal a partir de su espectro.",
    "serie": "Aproxima una función periódica como suma de senos y cosenos. Suba "
             "el orden para ver cómo se ajusta mejor.",
    "tabla": "Los pares f(t) ↔ F(s) que se usan constantemente. La condición "
             "indica dónde converge la integral.",
}
