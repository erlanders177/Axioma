"""Estadística descriptiva, regresión lineal y distribuciones de probabilidad."""

from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QPlainTextEdit, QSplitter, QTabWidget,
    QVBoxLayout, QWidget,
)

from ..core import estadistica as est
from ..core import historial as hist
from ..core.config import config
from . import tema
from .comunes import (
    CampoNumerico, PanelHistorial, TablaResultados, aviso, boton, etiqueta,
    separador, tarjeta,
)
from .grafica import CICLO, PanelGrafica

EJEMPLO_X = "12, 15, 17, 18, 20, 22, 23, 25, 28, 30"
EJEMPLO_Y = "25, 31, 34, 38, 41, 45, 46, 51, 56, 61"


class PanelEstadistica(QWidget):
    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.paleta = tema.paleta(config["tema"])
        self._construir()
        self._cambiar_distribucion(0)

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_entrada())
        division.addWidget(self._crear_columna_salida())

        marco_hist, col_hist = tarjeta()
        self.historial = PanelHistorial("estadistica", "Historial")
        self.historial.restaurar.connect(self._restaurar)
        col_hist.addWidget(self.historial)
        division.addWidget(marco_hist)

        division.setSizes([360, 500, 280])
        raiz.addWidget(division)

    def _crear_columna_entrada(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        self.pestanas = QTabWidget()
        self.pestanas.addTab(self._pestana_datos(), "Datos")
        self.pestanas.addTab(self._pestana_regresion(), "Regresión")
        self.pestanas.addTab(self._pestana_distribuciones(), "Distribuciones")
        self.pestanas.currentChanged.connect(self._cambiar_pestana)
        columna.addWidget(self.pestanas, 1)

        return contenedor

    def _pestana_datos(self) -> QWidget:
        marco, col = tarjeta()
        col.addWidget(etiqueta("Serie de datos", "seccion"))
        self.datos = QPlainTextEdit()
        self.datos.setProperty("clase", "mono")
        self.datos.setPlaceholderText(
            "Separe los valores con comas, espacios o saltos de línea.\n"
            "Puede pegar directamente una columna de una hoja de cálculo."
        )
        col.addWidget(self.datos, 1)

        self.contador = etiqueta("", "subtitulo")
        self.datos.textChanged.connect(self._actualizar_contador)
        col.addWidget(self.contador)

        col.addWidget(separador())
        col.addWidget(etiqueta("Gráfico", "seccion"))
        self.combo_grafico = QComboBox()
        self.combo_grafico.addItems([
            "Histograma", "Diagrama de caja", "Datos en orden", "Frecuencias acumuladas",
        ])
        self.combo_grafico.currentIndexChanged.connect(self._redibujar_datos)
        col.addWidget(self.combo_grafico)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Analizar", "primario", self.analizar_datos))
        acciones.addWidget(boton("Frecuencias", "", self.mostrar_frecuencias))
        acciones.addWidget(boton("Ejemplo", "", self._ejemplo_datos))
        col.addLayout(acciones)
        return marco

    def _pestana_regresion(self) -> QWidget:
        marco, col = tarjeta()
        col.addWidget(etiqueta("Variable X (independiente)", "seccion"))
        self.datos_x = QPlainTextEdit()
        self.datos_x.setProperty("clase", "mono")
        self.datos_x.setPlaceholderText("12, 15, 17, …")
        col.addWidget(self.datos_x, 1)

        col.addWidget(etiqueta("Variable Y (dependiente)", "seccion"))
        self.datos_y = QPlainTextEdit()
        self.datos_y.setProperty("clase", "mono")
        self.datos_y.setPlaceholderText("25, 31, 34, …")
        col.addWidget(self.datos_y, 1)

        self.nota_regresion = etiqueta(
            "Las dos series deben tener el mismo número de datos, emparejados en orden.",
            "nota", ajustar=True,
        )
        col.addWidget(self.nota_regresion)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Calcular regresión", "primario", self.analizar_regresion))
        acciones.addWidget(boton("Ejemplo", "", self._ejemplo_regresion))
        col.addLayout(acciones)
        return marco

    def _pestana_distribuciones(self) -> QWidget:
        marco, col = tarjeta()
        col.addWidget(etiqueta("Distribución", "seccion"))
        self.combo_distribucion = QComboBox()
        self.combo_distribucion.addItems([t for _, t, _ in est.DISTRIBUCIONES])
        self.combo_distribucion.currentIndexChanged.connect(self._cambiar_distribucion)
        col.addWidget(self.combo_distribucion)

        col.addWidget(separador())
        self.formulario = QFormLayout()
        self.formulario.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.formulario.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.formulario.setHorizontalSpacing(10)
        self.formulario.setVerticalSpacing(7)
        col.addLayout(self.formulario)
        self._campos_distribucion: list[CampoNumerico] = []

        self.nota_distribucion = etiqueta("", "nota", ajustar=True)
        col.addWidget(self.nota_distribucion)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Calcular", "primario", self.analizar_distribucion))
        col.addLayout(acciones)
        col.addStretch()
        return marco

    def _crear_columna_salida(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco_res, col_res = tarjeta()
        col_res.addWidget(etiqueta("Resultados", "seccion"))
        self.tabla = TablaResultados()
        self.tabla.setHorizontalHeaderLabels(["Medida", "Valor"])
        col_res.addWidget(self.tabla, 1)
        fila = QHBoxLayout()
        fila.addWidget(boton("Copiar", "", self._copiar))
        fila.addStretch()
        col_res.addLayout(fila)
        columna.addWidget(marco_res, 3)

        marco_graf, col_graf = tarjeta()
        self.grafica = PanelGrafica(self.paleta, 5.0, 3.0, con_barra=False)
        self.grafica.setMinimumHeight(230)
        col_graf.addWidget(self.grafica, 1)
        columna.addWidget(marco_graf, 2)

        return contenedor

    # ---------------------------------------------------------------- datos -- #

    def _actualizar_contador(self) -> None:
        try:
            valores = est.analizar_datos(self.datos.toPlainText())
        except est.ErrorEstadistica:
            self.contador.setText("")
            return
        self.contador.setText(f"{len(valores)} datos leídos")

    def _leer_datos(self, widget: QPlainTextEdit, nombre: str) -> list[float] | None:
        try:
            return est.analizar_datos(widget.toPlainText(), nombre)
        except est.ErrorEstadistica as e:
            aviso(self, str(e), "Datos")
            return None

    def analizar_datos(self) -> None:
        valores = self._leer_datos(self.datos, "la serie de datos")
        if valores is None:
            return
        filas = est.descriptiva(valores, config["decimales"])
        self.tabla.mostrar(filas)
        self._redibujar_datos()

        resumen = dict(filas)
        operacion = (f"{len(valores)} datos · media {resumen.get('Media aritmética', '?')} · "
                     f"σ {resumen.get('Desviación típica poblacional', '?')}")
        self._guardar(operacion, {"modo": "datos", "datos": self.datos.toPlainText()})

    def mostrar_frecuencias(self) -> None:
        valores = self._leer_datos(self.datos, "la serie de datos")
        if valores is None:
            return
        self.tabla.mostrar(est.tabla_frecuencias(valores, config["decimales"]))
        self._redibujar_datos()

    def _redibujar_datos(self) -> None:
        try:
            valores = est.analizar_datos(self.datos.toPlainText())
        except est.ErrorEstadistica:
            self.grafica.lienzo.limpiar("Introduzca datos para ver el gráfico")
            return

        tipo = self.combo_grafico.currentText()
        eje = self.grafica.lienzo.nuevo_eje()
        color = self.paleta.grafico_relleno

        if tipo == "Histograma":
            # Regla de Sturges para el número de intervalos.
            intervalos = max(3, min(30, int(np.ceil(np.log2(len(valores)) + 1))))
            eje.hist(valores, bins=intervalos, color=color, alpha=0.75,
                     edgecolor=self.paleta.grafico_fondo)
            media = float(np.mean(valores))
            eje.axvline(media, color=self.paleta.aviso, linestyle="--", linewidth=1.4,
                        label=f"media = {media:.4g}")
            self.grafica.lienzo.estilizar(eje, etiqueta_x="valor", etiqueta_y="frecuencia",
                                          leyenda=True, ejes_cero=False)
        elif tipo == "Diagrama de caja":
            caja = eje.boxplot(valores, patch_artist=True, widths=0.5, **_horizontal())
            for parte in caja["boxes"]:
                parte.set_facecolor(color)
                parte.set_alpha(0.6)
            for grupo in ("whiskers", "caps", "medians"):
                for parte in caja[grupo]:
                    parte.set_color(self.paleta.grafico_linea)
            for parte in caja["fliers"]:
                parte.set_markerfacecolor(self.paleta.peligro)
                parte.set_markeredgecolor(self.paleta.peligro)
            eje.set_yticks([])
            self.grafica.lienzo.estilizar(eje, etiqueta_x="valor", ejes_cero=False)
        elif tipo == "Datos en orden":
            eje.plot(range(1, len(valores) + 1), valores, "o-", color=color,
                     markersize=4, linewidth=1.2)
            self.grafica.lienzo.estilizar(eje, etiqueta_x="posición", etiqueta_y="valor",
                                          ejes_cero=False)
        else:  # Frecuencias acumuladas
            ordenados = np.sort(valores)
            acumulada = np.arange(1, len(ordenados) + 1) / len(ordenados) * 100
            eje.step(ordenados, acumulada, where="post", color=color, linewidth=1.8)
            eje.set_ylim(0, 105)
            self.grafica.lienzo.estilizar(eje, etiqueta_x="valor", etiqueta_y="% acumulado",
                                          ejes_cero=False)

    def _ejemplo_datos(self) -> None:
        self.datos.setPlainText("12 15 17 18 20 20 21 22 23 25 25 25 28 30 34 41")
        self.analizar_datos()

    # ------------------------------------------------------------ regresión -- #

    def analizar_regresion(self) -> None:
        x = self._leer_datos(self.datos_x, "la serie X")
        y = self._leer_datos(self.datos_y, "la serie Y")
        if x is None or y is None:
            return

        try:
            filas = est.regresion_lineal(x, y, config["decimales"])
        except est.ErrorEstadistica as e:
            aviso(self, str(e), "Regresión")
            return

        self.tabla.mostrar(filas)
        self._dibujar_regresion(x, y)

        recta = dict(filas).get("Recta de regresión", "")
        self._guardar(f"Regresión · {recta}", {
            "modo": "regresion",
            "x": self.datos_x.toPlainText(),
            "y": self.datos_y.toPlainText(),
        })

    def _dibujar_regresion(self, x: list[float], y: list[float]) -> None:
        eje = self.grafica.lienzo.nuevo_eje()
        eje.plot(x, y, "o", color=CICLO[0], markersize=6, label="datos")

        arreglo_x = np.array(x)
        media_x, media_y = arreglo_x.mean(), np.mean(y)
        sxx = float(((arreglo_x - media_x) ** 2).sum())
        if sxx > 0:
            pendiente = float(((arreglo_x - media_x) * (np.array(y) - media_y)).sum() / sxx)
            ordenada = media_y - pendiente * media_x
            recta_x = np.linspace(arreglo_x.min(), arreglo_x.max(), 100)
            eje.plot(recta_x, pendiente * recta_x + ordenada, "-", color=CICLO[1],
                     linewidth=1.8, label="recta de regresión")

        self.grafica.lienzo.estilizar(eje, etiqueta_x="X", etiqueta_y="Y",
                                      leyenda=True, ejes_cero=False)

    def _ejemplo_regresion(self) -> None:
        self.datos_x.setPlainText(EJEMPLO_X)
        self.datos_y.setPlainText(EJEMPLO_Y)
        self.analizar_regresion()

    # -------------------------------------------------------- distribuciones -- #

    def _cambiar_distribucion(self, _indice: int) -> None:
        _, _, campos = est.DISTRIBUCIONES[self.combo_distribucion.currentIndex()]

        while self.formulario.count():
            elemento = self.formulario.takeAt(0)
            widget = elemento.widget()
            if widget is not None:
                widget.deleteLater()
        self._campos_distribucion.clear()

        predeterminados = {
            "media (μ)": "0", "desviación (σ)": "1", "valor (x)": "0",
            "ensayos (n)": "10", "probabilidad (p)": "0.5", "éxitos (k)": "5",
            "media (λ)": "2", "sucesos (k)": "2",
        }
        for nombre in campos:
            campo = CampoNumerico(predeterminados.get(nombre, ""))
            campo.setText(predeterminados.get(nombre, ""))
            campo.aceptado.connect(self.analizar_distribucion)
            self._campos_distribucion.append(campo)
            self.formulario.addRow(f"{nombre}:", campo)

        clave = est.DISTRIBUCIONES[self.combo_distribucion.currentIndex()][0]
        self.nota_distribucion.setText(_NOTAS_DISTRIBUCION.get(clave, ""))

    def analizar_distribucion(self) -> None:
        clave, _, _ = est.DISTRIBUCIONES[self.combo_distribucion.currentIndex()]
        try:
            valores = [c.valor() for c in self._campos_distribucion]
        except ValueError as e:
            aviso(self, str(e), "Distribución")
            return

        try:
            if clave == "normal":
                filas = est.normal(valores[0], valores[1], valores[2], config["decimales"])
            elif clave == "binomial":
                filas = est.binomial(int(valores[0]), valores[1], int(valores[2]),
                                     config["decimales"])
            else:
                filas = est.poisson(valores[0], int(valores[1]), config["decimales"])
        except est.ErrorEstadistica as e:
            aviso(self, str(e), "Distribución")
            return

        self.tabla.mostrar(filas)
        self._dibujar_distribucion(clave, valores)

        titulo = est.DISTRIBUCIONES[self.combo_distribucion.currentIndex()][1]
        probabilidad = dict(filas).get("P(X = k)") or dict(filas).get("P(X ≤ x)", "")
        self._guardar(f"{titulo} → {probabilidad}", {"modo": "distribucion"})

    def _dibujar_distribucion(self, clave: str, valores: list[float]) -> None:
        eje = self.grafica.lienzo.nuevo_eje()
        color = self.paleta.grafico_relleno

        if clave == "normal":
            media, desviacion, x = valores
            xs = np.linspace(media - 4 * desviacion, media + 4 * desviacion, 400)
            ys = np.exp(-0.5 * ((xs - media) / desviacion) ** 2) / (desviacion * np.sqrt(2 * np.pi))
            eje.plot(xs, ys, color=CICLO[0], linewidth=1.8)
            eje.fill_between(xs[xs <= x], 0, ys[xs <= x], color=color, alpha=0.35,
                             label="P(X ≤ x)")
            eje.axvline(x, color=self.paleta.aviso, linestyle="--", linewidth=1.3)
            self.grafica.lienzo.estilizar(eje, etiqueta_x="x", etiqueta_y="densidad",
                                          leyenda=True, ejes_cero=False)
            return

        if clave == "binomial":
            n, p, k = int(valores[0]), valores[1], int(valores[2])
            n_mostrar = min(n, 60)
            xs = np.arange(n_mostrar + 1)
            from math import comb
            ys = np.array([comb(n, int(i)) * p ** int(i) * (1 - p) ** (n - int(i))
                           for i in xs])
            etiqueta_x, resaltado = "k (éxitos)", k
        else:
            lam, k = valores[0], int(valores[1])
            n_mostrar = int(min(60, max(10, lam * 3 + 10)))
            xs = np.arange(n_mostrar + 1)
            from math import exp, lgamma, log
            ys = np.array([exp(-lam + int(i) * log(lam) - lgamma(int(i) + 1)) for i in xs])
            etiqueta_x, resaltado = "k (sucesos)", k

        colores = [self.paleta.aviso if int(i) == resaltado else color for i in xs]
        eje.bar(xs, ys, color=colores, alpha=0.85, edgecolor=self.paleta.grafico_fondo)
        self.grafica.lienzo.estilizar(eje, etiqueta_x=etiqueta_x, etiqueta_y="probabilidad",
                                      ejes_cero=False)

    # ---------------------------------------------------------------- varios -- #

    def _cambiar_pestana(self, indice: int) -> None:
        self.tabla.limpiar()
        if indice == 0:
            self._redibujar_datos()
        else:
            self.grafica.lienzo.limpiar("Pulse «Calcular» para ver el gráfico")

    def _guardar(self, operacion: str, datos: dict) -> None:
        try:
            entrada = hist.guardar("estadistica", operacion, datos)
            self.historial.anadir(entrada)
        except hist.ErrorHistorial:
            pass

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.tabla.texto_plano())

    def _restaurar(self, datos: dict) -> None:
        modo = datos.get("modo")
        if modo == "datos" and datos.get("datos"):
            self.pestanas.setCurrentIndex(0)
            self.datos.setPlainText(str(datos["datos"]))
            self.analizar_datos()
        elif modo == "regresion":
            self.pestanas.setCurrentIndex(1)
            self.datos_x.setPlainText(str(datos.get("x", "")))
            self.datos_y.setPlainText(str(datos.get("y", "")))
            self.analizar_regresion()

    def aplicar_paleta(self, paleta) -> None:
        self.paleta = paleta
        self.grafica.aplicar_paleta(paleta)
        if self.pestanas.currentIndex() == 0:
            self._redibujar_datos()


def _horizontal() -> dict:
    """Argumento para orientar el diagrama de caja, según la versión de matplotlib.

    En matplotlib 3.10 el parámetro ``vert`` quedó obsoleto en favor de
    ``orientation``; se usa uno u otro para no depender de una versión concreta.
    """
    from matplotlib import __version__ as version_mpl

    partes = version_mpl.split(".")
    mayor, menor = int(partes[0]), int(partes[1]) if len(partes) > 1 else 0
    if (mayor, menor) >= (3, 10):
        return {"orientation": "horizontal"}
    return {"vert": False}


_NOTAS_DISTRIBUCION = {
    "normal": "Distribución continua. x es el valor cuya probabilidad acumulada se calcula.",
    "binomial": "Número de éxitos en n ensayos independientes con probabilidad p cada uno.",
    "poisson": "Número de sucesos en un intervalo, cuando ocurren a un ritmo medio λ.",
}
