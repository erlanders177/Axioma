"""Ajuste de curvas: qué modelo describe mejor unos datos."""

from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QPlainTextEdit, QSpinBox, QSplitter, QVBoxLayout,
    QWidget,
)

from ..core import ajuste as aj
from ..core import estadistica as est
from ..core import historial as hist
from ..core.config import config
from . import tema
from .comunes import (
    CampoNumerico, PanelHistorial, TablaResultados, aviso, boton, etiqueta,
    separador, tarjeta,
)
from .grafica import CICLO, PanelGrafica

EJEMPLO_X = "1, 2, 3, 4, 5, 6, 7, 8"
EJEMPLO_Y = "2.1, 4.4, 9.1, 17.5, 35.8, 71.2, 145.0, 288.5"


class PanelAjuste(QWidget):
    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.paleta = tema.paleta(config["tema"])
        self._ajustes: list[aj.Ajuste] = []
        self._construir()
        # `currentIndexChanged` no se dispara al construir con el índice ya en 0.
        self._cambiar_modelo(0)

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_entrada())
        division.addWidget(self._crear_columna_salida())

        marco_hist, col_hist = tarjeta()
        self.historial = PanelHistorial("ajuste", "Historial")
        self.historial.restaurar.connect(self._restaurar)
        col_hist.addWidget(self.historial)
        division.addWidget(marco_hist)

        division.setSizes([340, 540, 260])
        raiz.addWidget(division)

    def _crear_columna_entrada(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Variable X", "seccion"))
        self.datos_x = QPlainTextEdit()
        self.datos_x.setProperty("clase", "mono")
        self.datos_x.setPlaceholderText("1, 2, 3, 4…")
        col.addWidget(self.datos_x, 1)

        col.addWidget(etiqueta("Variable Y", "seccion"))
        self.datos_y = QPlainTextEdit()
        self.datos_y.setProperty("clase", "mono")
        self.datos_y.setPlaceholderText("2.1, 4.4, 9.1…")
        col.addWidget(self.datos_y, 1)

        self.contador = etiqueta("", "subtitulo")
        self.datos_x.textChanged.connect(self._actualizar_contador)
        self.datos_y.textChanged.connect(self._actualizar_contador)
        col.addWidget(self.contador)

        col.addWidget(separador())
        col.addWidget(etiqueta("Modelo", "seccion"))
        self.combo = QComboBox()
        self.combo.addItem("Comparar todos y recomendar", "comparar")
        for clave, titulo, _ in aj.MODELOS:
            self.combo.addItem(titulo, clave)
        self.combo.currentIndexChanged.connect(self._cambiar_modelo)
        col.addWidget(self.combo)

        fila_grado = QHBoxLayout()
        self.etiqueta_grado = etiqueta("Grado:", "subtitulo")
        self.spin_grado = QSpinBox()
        self.spin_grado.setRange(1, aj.MAX_GRADO)
        self.spin_grado.setValue(2)
        fila_grado.addWidget(self.etiqueta_grado)
        fila_grado.addWidget(self.spin_grado)
        fila_grado.addStretch()
        col.addLayout(fila_grado)

        fila_prediccion = QHBoxLayout()
        fila_prediccion.addWidget(etiqueta("Predecir en x =", "subtitulo"))
        self.campo_prediccion = CampoNumerico("")
        self.campo_prediccion.aceptado.connect(self.calcular)
        fila_prediccion.addWidget(self.campo_prediccion, 1)
        col.addLayout(fila_prediccion)

        self.nota = etiqueta(
            "Las dos series deben tener el mismo número de datos, emparejados "
            "en orden. A diferencia de la interpolación, la curva no pasa por "
            "todos los puntos: busca el mejor compromiso.",
            "nota", ajustar=True,
        )
        col.addWidget(self.nota)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Ajustar", "primario", self.calcular))
        acciones.addWidget(boton("Ejemplo", "", self._cargar_ejemplo))
        col.addLayout(acciones)

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
        col_graf.addWidget(etiqueta("Datos y curva ajustada", "seccion"))
        self.grafica = PanelGrafica(self.paleta, 5.0, 3.0, con_barra=False)
        self.grafica.setMinimumHeight(230)
        col_graf.addWidget(self.grafica, 1)
        columna.addWidget(marco_graf, 2)

        return contenedor

    # -------------------------------------------------------------- cálculo -- #

    def _actualizar_contador(self) -> None:
        try:
            x = est.analizar_datos(self.datos_x.toPlainText())
            y = est.analizar_datos(self.datos_y.toPlainText())
        except est.ErrorEstadistica:
            self.contador.setText("")
            return
        if len(x) == len(y):
            self.contador.setText(f"{len(x)} pares de datos")
        else:
            self.contador.setText(f"⚠ X tiene {len(x)} datos e Y tiene {len(y)}")

    def _cambiar_modelo(self, _indice: int) -> None:
        clave = self.combo.currentData()
        necesita_grado = clave == "polinomico"
        self.etiqueta_grado.setVisible(necesita_grado)
        self.spin_grado.setVisible(necesita_grado)

    def calcular(self) -> None:
        try:
            x = est.analizar_datos(self.datos_x.toPlainText(), "la serie X")
            y = est.analizar_datos(self.datos_y.toPlainText(), "la serie Y")
        except est.ErrorEstadistica as e:
            aviso(self, str(e), "Datos")
            return

        clave = self.combo.currentData()
        try:
            if clave == "comparar":
                self._ajustes, filas = aj.comparar(x, y)
                principal = self._ajustes[0]
            else:
                principal = aj.ajustar(x, y, clave, self.spin_grado.value())
                self._ajustes = [principal]
                filas = self._filas_de_uno(principal, len(x))
        except aj.ErrorAjuste as e:
            self.tabla.limpiar()
            self.grafica.lienzo.limpiar("Sin gráfica")
            aviso(self, str(e), "Ajuste de curvas")
            return

        filas = list(filas)
        prediccion = self.campo_prediccion.text().strip()
        if prediccion:
            try:
                valor = self.campo_prediccion.valor()
            except ValueError as e:
                aviso(self, str(e), "Predicción")
            else:
                filas.append(("", ""))
                filas.extend(aj.predecir(principal, [valor])[2:])

        self.tabla.mostrar(filas)
        self._dibujar(x, y)
        self._guardar(f"{principal.nombre}: {principal.formula}  (r² = {principal.r2:.4f})",
                      {"x": self.datos_x.toPlainText(),
                       "y": self.datos_y.toPlainText(),
                       "modelo": clave, "grado": self.spin_grado.value()})

    @staticmethod
    def _filas_de_uno(ajuste: aj.Ajuste, n: int) -> list[tuple[str, str]]:
        filas = [
            ("Número de pares", str(n)),
            ("", ""),
            ("Modelo", ajuste.nombre),
            ("Ecuación", ajuste.formula),
            ("Coeficiente de determinación r²", f"{ajuste.r2:.8f}"),
            ("Bondad del ajuste", aj._interpretar_r2(ajuste.r2)),
        ]
        if ajuste.linealizado:
            filas.append((
                "Aviso",
                "Se ajusta linealizando (tomando logaritmos): minimiza el error "
                "de la versión transformada, no el de la curva original.",
            ))
        return filas

    # -------------------------------------------------------------- gráfica -- #

    def _dibujar(self, x: list[float], y: list[float]) -> None:
        if not self._ajustes:
            self.grafica.lienzo.limpiar("Sin gráfica")
            return

        eje = self.grafica.lienzo.nuevo_eje()
        eje.plot(x, y, "o", color=self.paleta.aviso, markersize=7,
                 markeredgecolor=self.paleta.grafico_fondo, label="datos", zorder=5)

        margen = (max(x) - min(x)) * 0.08 or 1.0
        xs = np.linspace(min(x) - margen, max(x) + margen, 500)

        # Al comparar se dibujan los tres mejores, para ver la diferencia.
        for i, ajuste in enumerate(self._ajustes[:3]):
            try:
                funcion = ajuste.funcion()
                with np.errstate(all="ignore"):
                    ys = np.asarray(funcion(xs), dtype=float)
                if ys.shape != xs.shape:
                    ys = np.full(xs.shape, float(ys))
                ys = np.where(np.isfinite(ys), ys, np.nan)
            except Exception:
                continue

            eje.plot(xs, ys, color=CICLO[i % len(CICLO)],
                     linewidth=2.0 if i == 0 else 1.2,
                     linestyle="-" if i == 0 else "--",
                     alpha=1.0 if i == 0 else 0.7,
                     label=f"{ajuste.nombre}  (r²={ajuste.r2:.4f})")

        # El eje se ajusta a los datos, no a las colas de las curvas.
        rango = max(y) - min(y) or 1.0
        eje.set_ylim(min(y) - rango * 0.2, max(y) + rango * 0.2)
        self.grafica.lienzo.estilizar(eje, etiqueta_x="X", etiqueta_y="Y",
                                      leyenda=True, ejes_cero=False)

    # ---------------------------------------------------------------- varios -- #

    def _guardar(self, operacion: str, datos: dict) -> None:
        try:
            entrada = hist.guardar("ajuste", operacion, datos)
            self.historial.anadir(entrada)
        except hist.ErrorHistorial:
            pass

    def _cargar_ejemplo(self) -> None:
        self.datos_x.setPlainText(EJEMPLO_X)
        self.datos_y.setPlainText(EJEMPLO_Y)
        self.combo.setCurrentIndex(0)
        self.calcular()

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.tabla.texto_plano())

    def _restaurar(self, datos: dict) -> None:
        if datos.get("x"):
            self.datos_x.setPlainText(str(datos["x"]))
        if datos.get("y"):
            self.datos_y.setPlainText(str(datos["y"]))
        indice = self.combo.findData(datos.get("modelo"))
        if indice >= 0:
            self.combo.setCurrentIndex(indice)
        if "grado" in datos:
            try:
                self.spin_grado.setValue(int(datos["grado"]))
            except (TypeError, ValueError):
                pass
        self.calcular()

    def aplicar_paleta(self, paleta) -> None:
        self.paleta = paleta
        self.grafica.aplicar_paleta(paleta)
