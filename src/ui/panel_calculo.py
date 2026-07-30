"""Cálculo: derivadas, integrales, límites, series y análisis de funciones."""

from __future__ import annotations

import numpy as np
import sympy as sp
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QSplitter, QVBoxLayout, QWidget,
)

from ..core import calculo
from ..core import historial as hist
from ..core import simbolico as sim
from ..core.config import config
from . import tema
from .comunes import (
    PanelHistorial, TablaResultados, aviso, boton, etiqueta, separador, tarjeta,
)
from .grafica import CICLO, PanelGrafica, cortar_saltos, muestrear

EJEMPLOS = {
    "derivada": ("x^3 - 3x^2 + 2x", "x"),
    "integral": ("2x*cos(x^2)", "x"),
    "integral_definida": ("x^2", "x"),
    "limite": ("sin(x)/x", "x"),
    "taylor": ("exp(x)", "x"),
    "criticos": ("x^3 - 3x", "x"),
    "analisis": ("(x^2 - 1)/(x - 2)", "x"),
}


class PanelCalculo(QWidget):
    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.paleta = tema.paleta(config["tema"])
        self._campos: dict[str, QWidget] = {}
        self._construir()
        self._cambiar_operacion(0)

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_datos())
        division.addWidget(self._crear_columna_resultados())

        marco_hist, col_hist = tarjeta()
        self.historial = PanelHistorial("calculo", "Historial")
        self.historial.restaurar.connect(self._restaurar)
        col_hist.addWidget(self.historial)
        division.addWidget(marco_hist)

        division.setSizes([340, 500, 300])
        raiz.addWidget(division)

    def _crear_columna_datos(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Operación", "seccion"))
        self.combo = QComboBox()
        self.combo.addItems([titulo for _, titulo, _ in calculo.OPERACIONES])
        self.combo.currentIndexChanged.connect(self._cambiar_operacion)
        col.addWidget(self.combo)

        col.addWidget(separador())
        col.addWidget(etiqueta("Datos", "seccion"))

        self.formulario = QFormLayout()
        self.formulario.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.formulario.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.formulario.setHorizontalSpacing(10)
        self.formulario.setVerticalSpacing(7)
        col.addLayout(self.formulario)

        self.ayuda = etiqueta("", "nota", ajustar=True)
        col.addWidget(self.ayuda)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Calcular", "primario", self.calcular))
        acciones.addWidget(boton("Ejemplo", "", self._cargar_ejemplo))
        col.addLayout(acciones)
        col.addStretch()

        columna.addWidget(marco, 1)
        return contenedor

    def _crear_columna_resultados(self) -> QWidget:
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
        col_graf.addWidget(etiqueta("Gráfica", "seccion"))
        self.grafica = PanelGrafica(self.paleta, 5.0, 2.8, con_barra=False)
        self.grafica.setMinimumHeight(200)
        col_graf.addWidget(self.grafica, 1)
        columna.addWidget(marco_graf, 2)

        return contenedor

    # ----------------------------------------------------------- formulario -- #

    @property
    def _clave(self) -> str:
        return calculo.OPERACIONES[self.combo.currentIndex()][0]

    def _cambiar_operacion(self, _indice: int) -> None:
        clave, _, campos = calculo.OPERACIONES[self.combo.currentIndex()]

        while self.formulario.count():
            elemento = self.formulario.takeAt(0)
            widget = elemento.widget()
            if widget is not None:
                widget.deleteLater()
        self._campos.clear()

        etiquetas = {
            "expresion": "f(x) =",
            "variable": "Variable:",
            "orden": "Orden:",
            "desde": "Desde:",
            "hasta": "Hasta:",
            "punto": "Punto:",
            "direccion": "Lado:",
        }
        marcadores = {
            "expresion": "por ejemplo  x^3 - 3x + 2",
            "variable": "x",
            "orden": "1",
            "desde": "0",
            "hasta": "1",
            "punto": "0   (admite oo y -oo)",
        }

        for nombre in campos:
            if nombre == "direccion":
                widget = QComboBox()
                widget.addItems(["ambos lados", "por la derecha (+)", "por la izquierda (−)"])
            else:
                widget = QLineEdit()
                widget.setPlaceholderText(marcadores.get(nombre, ""))
                widget.returnPressed.connect(self.calcular)
                if nombre == "variable":
                    widget.setText("x")
                elif nombre == "orden":
                    widget.setText("1" if clave == "derivada" else "5")
            self._campos[nombre] = widget
            self.formulario.addRow(etiquetas.get(nombre, nombre + ":"), widget)

        self.ayuda.setText(_AYUDAS.get(clave, ""))
        self.tabla.limpiar()
        self.grafica.lienzo.limpiar("Introduzca una función y pulse «Calcular»")

    def _texto(self, nombre: str) -> str:
        widget = self._campos.get(nombre)
        if widget is None:
            return ""
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return widget.text().strip()

    def _cargar_ejemplo(self) -> None:
        clave = self._clave
        expresion, variable = EJEMPLOS.get(clave, ("x^2", "x"))
        if "expresion" in self._campos:
            self._campos["expresion"].setText(expresion)
        if "variable" in self._campos:
            self._campos["variable"].setText(variable)
        if "desde" in self._campos:
            self._campos["desde"].setText("0")
        if "hasta" in self._campos:
            self._campos["hasta"].setText("3")
        if "punto" in self._campos:
            self._campos["punto"].setText("0")
        self.calcular()

    # -------------------------------------------------------------- cálculo -- #

    def calcular(self) -> None:
        clave = self._clave
        expresion_texto = self._texto("expresion")
        variable_texto = self._texto("variable")

        try:
            filas = self._ejecutar(clave, expresion_texto, variable_texto)
        except sim.ErrorSimbolico as e:
            self.tabla.limpiar()
            self.grafica.lienzo.limpiar("Sin gráfica")
            aviso(self, str(e), "No se pudo calcular")
            return
        except Exception as e:  # sympy lanza tipos muy variados
            self.tabla.limpiar()
            self.grafica.lienzo.limpiar("Sin gráfica")
            aviso(self, f"No se pudo calcular ({type(e).__name__}: {e})", "Error")
            return

        self.tabla.mostrar(filas)
        self._dibujar(clave, expresion_texto, variable_texto)

        titulo = calculo.OPERACIONES[self.combo.currentIndex()][1]
        resumen = next((v for k, v in filas if k not in ("Función", "Punto", "Intervalo")), "")
        try:
            entrada = hist.guardar("calculo", f"{titulo}: {expresion_texto}  →  {resumen}", {
                "operacion": clave,
                "expresion": expresion_texto,
                "variable": variable_texto,
                "orden": self._texto("orden"),
                "desde": self._texto("desde"),
                "hasta": self._texto("hasta"),
                "punto": self._texto("punto"),
            })
            self.historial.anadir(entrada)
        except hist.ErrorHistorial:
            pass

    def _ejecutar(self, clave: str, expresion: str, variable: str) -> list[tuple[str, str]]:
        if clave == "derivada":
            return calculo.derivar(expresion, variable, _entero(self._texto("orden"), 1))
        if clave == "integral":
            return calculo.integrar(expresion, variable)
        if clave == "integral_definida":
            return calculo.integrar_definida(
                expresion, variable, self._texto("desde") or "0", self._texto("hasta") or "1"
            )
        if clave == "limite":
            lado = self._texto("direccion")
            direccion = "+" if "derecha" in lado else "-" if "izquierda" in lado else "ambos"
            return calculo.limite(expresion, variable, self._texto("punto") or "0", direccion)
        if clave == "taylor":
            return calculo.serie_taylor(
                expresion, variable, self._texto("punto") or "0",
                _entero(self._texto("orden"), 5),
            )
        if clave == "criticos":
            return calculo.puntos_criticos(expresion, variable)
        if clave == "analisis":
            return calculo.analizar_funcion(expresion, variable)
        raise sim.ErrorSimbolico(f"Operación desconocida: {clave}")

    # -------------------------------------------------------------- gráfica -- #

    def _dibujar(self, clave: str, expresion_texto: str, variable_texto: str) -> None:
        try:
            expresion = sim.analizar(expresion_texto)
            variable = sim.variable_principal(expresion, variable_texto)
        except sim.ErrorSimbolico:
            self.grafica.lienzo.limpiar("Sin gráfica")
            return

        curvas: list[tuple[str, sp.Expr, str]] = [
            (f"f({variable})", expresion, "-"),
        ]

        # En derivadas y extremos ayuda mucho ver f y f' superpuestas.
        if clave in ("derivada", "criticos"):
            orden = _entero(self._texto("orden"), 1) if clave == "derivada" else 1
            try:
                curvas.append((f"f{'′' * min(orden, 3)}", sp.diff(expresion, variable, orden), "--"))
            except (ValueError, TypeError):
                pass
        elif clave == "taylor":
            try:
                serie = sp.series(
                    expresion, variable,
                    sim.analizar(self._texto("punto") or "0"),
                    _entero(self._texto("orden"), 5) + 1,
                ).removeO()
                curvas.append(("polinomio de Taylor", serie, "--"))
            except (ValueError, TypeError, NotImplementedError):
                pass

        limites = self._intervalo(clave, expresion, variable)
        eje = self.grafica.lienzo.nuevo_eje()
        xs = np.linspace(limites[0], limites[1], 1200)
        todos: list[np.ndarray] = []

        for i, (nombre, curva, estilo) in enumerate(curvas):
            try:
                funcion = sim.a_funcion(curva, variable)
            except sim.ErrorSimbolico:
                continue
            ys = cortar_saltos(muestrear(funcion, xs))
            if np.all(np.isnan(ys)):
                continue
            todos.append(ys)
            eje.plot(xs, ys, color=CICLO[i % len(CICLO)], linewidth=1.7,
                     linestyle=estilo, label=nombre)

        if not todos:
            self.grafica.lienzo.limpiar("Esta función no se puede representar")
            return

        # En la integral definida se sombrea el área calculada.
        if clave == "integral_definida":
            self._sombrear_area(eje, expresion, variable, xs)

        self.grafica.lienzo.acotar_vertical(eje, np.concatenate(todos))
        self.grafica.lienzo.estilizar(eje, etiqueta_x=str(variable), leyenda=len(curvas) > 1)

    def _intervalo(self, clave: str, expresion: sp.Expr, variable: sp.Symbol) -> tuple[float, float]:
        """Ventana de representación adaptada a la operación."""
        if clave == "integral_definida":
            try:
                a = float(sp.N(sim.analizar(self._texto("desde") or "0")))
                b = float(sp.N(sim.analizar(self._texto("hasta") or "1")))
                margen = max((b - a) * 0.35, 1.0)
                return a - margen, b + margen
            except (ValueError, TypeError, sim.ErrorSimbolico):
                pass

        if clave == "limite":
            try:
                punto = float(sp.N(sim.analizar(self._texto("punto") or "0")))
                return punto - 5, punto + 5
            except (ValueError, TypeError, sim.ErrorSimbolico):
                pass

        # Por defecto se centra en las raíces si las hay.
        try:
            raices = [float(sp.re(sp.N(r))) for r in sp.solve(sp.Eq(expresion, 0), variable)
                      if not r.free_symbols and sim.es_real(r)]
        except (ValueError, TypeError, NotImplementedError):
            raices = []

        if raices:
            centro = (min(raices) + max(raices)) / 2
            radio = max(max(raices) - min(raices), 2.0) * 1.4
            return centro - radio, centro + radio
        return -10.0, 10.0

    def _sombrear_area(self, eje, expresion: sp.Expr, variable: sp.Symbol,
                       xs: np.ndarray) -> None:
        try:
            a = float(sp.N(sim.analizar(self._texto("desde") or "0")))
            b = float(sp.N(sim.analizar(self._texto("hasta") or "1")))
            funcion = sim.a_funcion(expresion, variable)
        except (ValueError, TypeError, sim.ErrorSimbolico):
            return

        dentro = np.linspace(min(a, b), max(a, b), 600)
        alturas = muestrear(funcion, dentro)
        eje.fill_between(dentro, 0, alturas, color=self.paleta.grafico_relleno,
                         alpha=0.28, label="área")
        for extremo in (a, b):
            eje.axvline(extremo, color=self.paleta.aviso, linewidth=1.0, linestyle=":")

    # ---------------------------------------------------------------- varios -- #

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.tabla.texto_plano())

    def _restaurar(self, datos: dict) -> None:
        claves = [c for c, _, _ in calculo.OPERACIONES]
        clave = datos.get("operacion")
        if clave in claves:
            self.combo.setCurrentIndex(claves.index(clave))
        for nombre in ("expresion", "variable", "orden", "desde", "hasta", "punto"):
            widget = self._campos.get(nombre)
            valor = datos.get(nombre)
            if widget is not None and valor and not isinstance(widget, QComboBox):
                widget.setText(str(valor))
        self.calcular()

    def aplicar_paleta(self, paleta) -> None:
        self.paleta = paleta
        self.grafica.aplicar_paleta(paleta)
        if self._texto("expresion"):
            self._dibujar(self._clave, self._texto("expresion"), self._texto("variable"))


def _entero(texto: str, defecto: int) -> int:
    try:
        return int(float(texto.replace(",", ".")))
    except (ValueError, AttributeError):
        return defecto


_AYUDAS = {
    "derivada": "Puede escribir x^2 en vez de x**2 y 2x en vez de 2*x. "
                "El orden indica cuántas veces se deriva.",
    "integral": "Calcula la primitiva. Si no existe en términos elementales, "
                "use la integral definida.",
    "integral_definida": "Los límites admiten expresiones: pi, 2*pi, sqrt(2), oo…",
    "limite": "Para el infinito escriba oo o -oo. Con «ambos lados» se comprueba "
              "además si los límites laterales coinciden.",
    "taylor": "Con el punto 0 el desarrollo se llama serie de Maclaurin.",
    "criticos": "Resuelve f′ = 0 y clasifica cada punto con el signo de f″.",
    "analisis": "Dominio, recorrido, cortes, simetría y periodo de la función.",
}
