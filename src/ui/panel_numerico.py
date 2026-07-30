"""Métodos numéricos, con la tabla de iteraciones y la gráfica de convergencia."""

from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView, QComboBox, QFormLayout, QHBoxLayout, QHeaderView,
    QLineEdit, QPlainTextEdit, QSpinBox, QSplitter, QTableWidget,
    QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget,
)

from ..core import historial as hist
from ..core import numerico
from ..core import simbolico as sim
from ..core.config import config
from ..core.formato import formatear
from . import tema
from .comunes import aviso, boton, etiqueta, separador, tarjeta
from .comunes import PanelHistorial
from .grafica import CICLO, PanelGrafica, cortar_saltos, muestrear


class PanelNumerico(QWidget):
    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.paleta = tema.paleta(config["tema"])
        self._campos: dict[str, QWidget] = {}
        self._construir()
        self._cambiar_metodo(0)

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_entrada())
        division.addWidget(self._crear_columna_salida())

        marco_hist, col_hist = tarjeta()
        self.historial = PanelHistorial("numerico", "Historial")
        self.historial.restaurar.connect(self._restaurar)
        col_hist.addWidget(self.historial)
        division.addWidget(marco_hist)

        division.setSizes([360, 520, 270])
        raiz.addWidget(division)

    def _crear_columna_entrada(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Método", "seccion"))
        self.combo = QComboBox()
        for _, titulo, _ in self._catalogo():
            self.combo.addItem(titulo)
        self.combo.currentIndexChanged.connect(self._cambiar_metodo)
        col.addWidget(self.combo)

        col.addWidget(separador())
        col.addWidget(etiqueta("Datos", "seccion"))

        self.formulario = QFormLayout()
        self.formulario.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.formulario.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.formulario.setHorizontalSpacing(10)
        self.formulario.setVerticalSpacing(7)
        col.addLayout(self.formulario)

        # Los puntos de la interpolación necesitan más sitio que un campo.
        self.contenedor_puntos = QWidget()
        col_puntos = QVBoxLayout(self.contenedor_puntos)
        col_puntos.setContentsMargins(0, 0, 0, 0)
        col_puntos.addWidget(etiqueta("Puntos (x, y) — uno por línea", "seccion"))
        self.puntos = QPlainTextEdit()
        self.puntos.setProperty("clase", "mono")
        self.puntos.setPlaceholderText("0, 1\n1, 3\n2, 7")
        self.puntos.setMaximumHeight(130)
        col_puntos.addWidget(self.puntos)
        col.addWidget(self.contenedor_puntos)

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
        self.resultado = etiqueta("", "resultado", ajustar=True)
        self.resultado.setMinimumHeight(26)
        col_res.addWidget(self.resultado)
        self.detalle = etiqueta("", "nota", ajustar=True)
        col_res.addWidget(self.detalle)

        self.pestanas = QTabWidget()
        contenedor_tabla = QWidget()
        col_tabla = QVBoxLayout(contenedor_tabla)
        col_tabla.setContentsMargins(0, 8, 0, 0)
        self.tabla = QTableWidget(0, 0)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setShowGrid(False)
        self.tabla.verticalHeader().setVisible(False)
        col_tabla.addWidget(self.tabla)
        self.pestanas.addTab(contenedor_tabla, "Iteraciones")

        contenedor_graf = QWidget()
        col_graf = QVBoxLayout(contenedor_graf)
        col_graf.setContentsMargins(0, 8, 0, 0)
        self.grafica = PanelGrafica(self.paleta, 5.0, 3.0, con_barra=False)
        col_graf.addWidget(self.grafica, 1)
        self.pestanas.addTab(contenedor_graf, "Gráfica")

        col_res.addWidget(self.pestanas, 1)

        fila = QHBoxLayout()
        fila.addWidget(boton("Copiar", "", self._copiar))
        fila.addStretch()
        col_res.addLayout(fila)
        columna.addWidget(marco_res, 1)

        return contenedor

    # ------------------------------------------------------------- métodos -- #

    @staticmethod
    def _catalogo() -> list[tuple[str, str, list[str]]]:
        """Todos los métodos, con los campos que pide cada uno."""
        return [
            ("biseccion", "Raíces · Bisección", ["expresion", "a", "b", "tolerancia"]),
            ("newton", "Raíces · Newton-Raphson", ["expresion", "x0", "tolerancia"]),
            ("secante", "Raíces · Secante", ["expresion", "x0", "x1", "tolerancia"]),
            ("trapecio", "Integración · Trapecio", ["expresion", "a", "b", "n"]),
            ("simpson", "Integración · Simpson", ["expresion", "a", "b", "n"]),
            ("lagrange", "Interpolación · Lagrange", ["puntos"]),
            ("newton_interp", "Interpolación · Diferencias divididas", ["puntos"]),
            ("euler", "EDO · Euler", ["fxy", "x0", "y0", "h", "pasos"]),
            ("rk4", "EDO · Runge-Kutta 4", ["fxy", "x0", "y0", "h", "pasos"]),
        ]

    @property
    def _clave(self) -> str:
        return self._catalogo()[self.combo.currentIndex()][0]

    def _cambiar_metodo(self, _indice: int) -> None:
        clave, _, campos = self._catalogo()[self.combo.currentIndex()]

        while self.formulario.count():
            elemento = self.formulario.takeAt(0)
            widget = elemento.widget()
            if widget is not None:
                widget.deleteLater()
        self._campos.clear()

        etiquetas = {
            "expresion": "f(x) =", "fxy": "y′ = f(x,y) =",
            "a": "Extremo a =", "b": "Extremo b =",
            "x0": "x₀ =", "x1": "x₁ =", "y0": "y₀ =",
            "tolerancia": "Tolerancia:", "n": "Subintervalos n:",
            "h": "Paso h =", "pasos": "Número de pasos:",
        }
        predeterminados = {
            "expresion": "x^2 - 2", "fxy": "x - y",
            "a": "0", "b": "2", "x0": "1", "x1": "2", "y0": "1",
            "tolerancia": "1e-10", "n": "100", "h": "0.1", "pasos": "20",
        }

        for nombre in campos:
            if nombre == "puntos":
                continue
            if nombre in ("n", "pasos"):
                widget = QSpinBox()
                widget.setRange(1, 10000)
                widget.setValue(int(predeterminados[nombre]))
            else:
                widget = QLineEdit(predeterminados.get(nombre, ""))
                widget.returnPressed.connect(self.calcular)
            self._campos[nombre] = widget
            self.formulario.addRow(etiquetas.get(nombre, nombre + ":"), widget)

        self.contenedor_puntos.setVisible("puntos" in campos)
        self.nota.setText(_NOTAS.get(clave, ""))
        self.resultado.clear()
        self.detalle.clear()
        self.tabla.setRowCount(0)
        self.tabla.setColumnCount(0)
        self.grafica.lienzo.limpiar("Pulse «Calcular»")

    def _texto(self, nombre: str) -> str:
        widget = self._campos.get(nombre)
        if widget is None:
            return ""
        if isinstance(widget, QSpinBox):
            return str(widget.value())
        return widget.text().strip()

    def _numero(self, nombre: str, defecto: float = 0.0) -> float:
        texto = self._texto(nombre).replace(",", ".")
        try:
            return float(texto)
        except ValueError:
            raise numerico.ErrorNumerico(
                f"«{texto}» no es un número válido en el campo {nombre}"
            ) from None

    def _leer_puntos(self) -> list[tuple[float, float]]:
        puntos: list[tuple[float, float]] = []
        for numero, linea in enumerate(self.puntos.toPlainText().splitlines(), 1):
            limpia = linea.strip().replace(";", ",")
            if not limpia:
                continue
            partes = [p for p in limpia.replace(",", " ").split() if p]
            if len(partes) != 2:
                raise numerico.ErrorNumerico(
                    f"La línea {numero} debe tener dos números: «x, y»"
                )
            try:
                puntos.append((float(partes[0]), float(partes[1])))
            except ValueError:
                raise numerico.ErrorNumerico(
                    f"La línea {numero} no contiene dos números válidos"
                ) from None
        return puntos

    # -------------------------------------------------------------- cálculo -- #

    def calcular(self) -> None:
        try:
            self._ejecutar(self._clave)
        except (numerico.ErrorNumerico, sim.ErrorSimbolico) as e:
            self.resultado.clear()
            self.detalle.clear()
            self.tabla.setRowCount(0)
            self.grafica.lienzo.limpiar("Sin gráfica")
            aviso(self, str(e), "Métodos numéricos")
        except Exception as e:
            aviso(self, f"No se pudo calcular ({type(e).__name__}: {e})", "Error")

    def _ejecutar(self, clave: str) -> None:
        decimales = max(8, int(config["decimales"]))

        if clave in ("biseccion", "newton", "secante"):
            expresion = self._texto("expresion")
            tolerancia = self._numero("tolerancia", 1e-10)
            if clave == "biseccion":
                raiz, iteraciones, nota = numerico.biseccion(
                    expresion, self._numero("a"), self._numero("b"), tolerancia)
            elif clave == "newton":
                raiz, iteraciones, nota = numerico.newton_raphson(
                    expresion, self._numero("x0"), tolerancia)
            else:
                raiz, iteraciones, nota = numerico.secante(
                    expresion, self._numero("x0"), self._numero("x1"), tolerancia)

            self.resultado.setText(f"Raíz ≈ {formatear(raiz, decimales)}")
            self.detalle.setText(nota)
            self._mostrar_tabla(iteraciones, decimales)
            self._dibujar_raiz(expresion, iteraciones, raiz)
            self._guardar(f"{self.combo.currentText()}: {expresion} → x ≈ "
                          f"{formatear(raiz, 8)}")
            return

        if clave in ("trapecio", "simpson"):
            expresion = self._texto("expresion")
            a, b = self._numero("a"), self._numero("b")
            n = int(self._numero("n", 100))
            funcion = numerico.trapecio if clave == "trapecio" else numerico.simpson
            valor, puntos, nota = funcion(expresion, a, b, n)

            self.resultado.setText(f"∫ ≈ {formatear(valor, decimales)}")
            self.detalle.setText(nota)
            self._mostrar_tabla(puntos, decimales)
            self._dibujar_integral(expresion, a, b, n, clave)
            self._guardar(f"{self.combo.currentText()}: ∫{expresion} de {a:g} a "
                          f"{b:g} ≈ {formatear(valor, 8)}")
            return

        if clave in ("lagrange", "newton_interp"):
            puntos = self._leer_puntos()
            metodo = "lagrange" if clave == "lagrange" else "newton"
            polinomio, detalles, nota = numerico.interpolar(puntos, metodo)

            self.resultado.setText(f"P(x) = {sim.texto(polinomio)}")
            self.detalle.setText(nota)
            self._mostrar_tabla(detalles, decimales)
            self._dibujar_interpolacion(polinomio, puntos)
            self._guardar(f"{self.combo.currentText()}: P(x) = {sim.texto(polinomio)}",
                          {"puntos": self.puntos.toPlainText()})
            return

        # EDOs aproximadas
        expresion = self._texto("fxy")
        x0, y0 = self._numero("x0"), self._numero("y0")
        h = self._numero("h", 0.1)
        pasos = int(self._numero("pasos", 20))
        funcion = numerico.euler if clave == "euler" else numerico.runge_kutta_4
        iteraciones, nota = funcion(expresion, x0, y0, h, pasos)

        final = iteraciones[-1].valores
        self.resultado.setText(
            f"y({formatear(final['xₙ'], 6)}) ≈ {formatear(final['yₙ'], decimales)}"
        )
        self.detalle.setText(nota)
        self._mostrar_tabla(iteraciones, decimales)
        self._dibujar_edo(iteraciones, expresion)
        self._guardar(f"{self.combo.currentText()}: y′ = {expresion}, "
                      f"y({x0:g}) = {y0:g} → {formatear(final['yₙ'], 8)}")

    # --------------------------------------------------------------- tabla -- #

    def _mostrar_tabla(self, iteraciones: list, decimales: int) -> None:
        if not iteraciones:
            self.tabla.setRowCount(0)
            self.tabla.setColumnCount(0)
            return

        columnas = ["n"] + list(iteraciones[0].valores.keys())
        con_error = any(it.error is not None for it in iteraciones)
        if con_error:
            columnas.append("error")

        self.tabla.setColumnCount(len(columnas))
        self.tabla.setHorizontalHeaderLabels(columnas)
        self.tabla.setRowCount(len(iteraciones))

        for fila, it in enumerate(iteraciones):
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(it.n)))
            for columna, clave in enumerate(list(it.valores.keys()), start=1):
                valor = it.valores[clave]
                texto = (formatear(valor, decimales)
                         if isinstance(valor, (int, float)) else str(valor))
                celda = QTableWidgetItem(texto)
                celda.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla.setItem(fila, columna, celda)
            if con_error:
                texto = "" if it.error is None else f"{it.error:.3e}"
                celda = QTableWidgetItem(texto)
                celda.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.tabla.setItem(fila, len(columnas) - 1, celda)

        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.resizeRowsToContents()

    # -------------------------------------------------------------- gráficas -- #

    def _dibujar_raiz(self, expresion: str, iteraciones: list, raiz: float) -> None:
        try:
            expr = sim.analizar(expresion)
            var = sim.variable_principal(expr, "x")
            funcion = sim.a_funcion(expr, var)
        except sim.ErrorSimbolico:
            self.grafica.lienzo.limpiar("Sin gráfica")
            return

        radio = max(2.0, abs(raiz) * 1.5)
        xs = np.linspace(raiz - radio, raiz + radio, 800)
        ys = cortar_saltos(muestrear(funcion, xs))

        eje = self.grafica.lienzo.nuevo_eje()
        eje.plot(xs, ys, color=CICLO[0], linewidth=1.7, label=f"f({var})")
        eje.plot([raiz], [0], "o", color=self.paleta.aviso, markersize=9,
                 markeredgecolor=self.paleta.grafico_fondo, label="raíz", zorder=5)

        # Las aproximaciones sucesivas, para ver cómo se acercan.
        aproximaciones = [it.valores.get("c") or it.valores.get("xₙ")
                          for it in iteraciones if
                          it.valores.get("c") is not None or it.valores.get("xₙ") is not None]
        if aproximaciones:
            eje.plot(aproximaciones, [0] * len(aproximaciones), "|",
                     color=self.paleta.texto_suave, markersize=12, alpha=0.55,
                     label="aproximaciones")

        self.grafica.lienzo.acotar_vertical(eje, ys)
        self.grafica.lienzo.estilizar(eje, etiqueta_x=str(var), leyenda=True)

    def _dibujar_integral(self, expresion: str, a: float, b: float, n: int,
                          metodo: str) -> None:
        try:
            expr = sim.analizar(expresion)
            var = sim.variable_principal(expr, "x")
            funcion = sim.a_funcion(expr, var)
        except sim.ErrorSimbolico:
            self.grafica.lienzo.limpiar("Sin gráfica")
            return

        margen = (b - a) * 0.15
        xs = np.linspace(a - margen, b + margen, 800)
        ys = cortar_saltos(muestrear(funcion, xs))

        eje = self.grafica.lienzo.nuevo_eje()
        eje.plot(xs, ys, color=CICLO[0], linewidth=1.7, label=f"f({var})")

        # Se dibujan los trapecios reales, pero sin saturar la vista.
        divisiones = min(n, 40)
        bordes = np.linspace(a, b, divisiones + 1)
        alturas = muestrear(funcion, bordes)
        eje.fill_between(bordes, 0, alturas, step=None, alpha=0.28,
                         color=self.paleta.grafico_relleno, label="área aproximada")
        for x in bordes:
            altura = float(muestrear(funcion, np.array([x]))[0])
            if np.isfinite(altura):
                eje.plot([x, x], [0, altura], color=self.paleta.grafico_rejilla,
                         linewidth=0.7, alpha=0.8)

        if divisiones < n:
            eje.set_title(f"se muestran {divisiones} de los {n} subintervalos",
                          color=self.paleta.texto_suave, fontsize=8)

        self.grafica.lienzo.acotar_vertical(eje, ys)
        self.grafica.lienzo.estilizar(eje, etiqueta_x=str(var), leyenda=True)

    def _dibujar_interpolacion(self, polinomio, puntos: list) -> None:
        import sympy as sp

        x = sp.Symbol("x")
        funcion = sp.lambdify(x, polinomio, "numpy")
        xs_datos = [p[0] for p in puntos]
        margen = (max(xs_datos) - min(xs_datos)) * 0.15 or 1.0
        xs = np.linspace(min(xs_datos) - margen, max(xs_datos) + margen, 600)
        ys = muestrear(funcion, xs)

        eje = self.grafica.lienzo.nuevo_eje()
        eje.plot(xs, ys, color=CICLO[0], linewidth=1.7, label="P(x)")
        eje.plot(xs_datos, [p[1] for p in puntos], "o", color=self.paleta.aviso,
                 markersize=8, markeredgecolor=self.paleta.grafico_fondo,
                 label="puntos dados", zorder=5)
        self.grafica.lienzo.acotar_vertical(eje, ys)
        self.grafica.lienzo.estilizar(eje, etiqueta_x="x", leyenda=True)

    def _dibujar_edo(self, iteraciones: list, expresion: str) -> None:
        xs = [it.valores["xₙ"] for it in iteraciones]
        ys = [it.valores["yₙ"] for it in iteraciones]

        eje = self.grafica.lienzo.nuevo_eje()
        eje.plot(xs, ys, "o-", color=CICLO[0], markersize=3.5, linewidth=1.6,
                 label="solución aproximada")
        self.grafica.lienzo.estilizar(eje, titulo=f"y′ = {expresion}",
                                      etiqueta_x="x", etiqueta_y="y", leyenda=True)

    # ---------------------------------------------------------------- varios -- #

    def _guardar(self, operacion: str, extra: dict | None = None) -> None:
        datos = {"metodo": self._clave}
        datos.update({k: self._texto(k) for k in self._campos})
        datos.update(extra or {})
        try:
            entrada = hist.guardar("numerico", operacion, datos)
            self.historial.anadir(entrada)
        except hist.ErrorHistorial:
            pass

    def _cargar_ejemplo(self) -> None:
        clave = self._clave
        if clave in ("lagrange", "newton_interp"):
            self.puntos.setPlainText("0, 1\n1, 3\n2, 7\n3, 13")
        self.calcular()

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is None:
            return
        lineas = [self.resultado.text(), self.detalle.text(), ""]
        cabeceras = [self.tabla.horizontalHeaderItem(c).text()
                     for c in range(self.tabla.columnCount())
                     if self.tabla.horizontalHeaderItem(c)]
        lineas.append("\t".join(cabeceras))
        for fila in range(self.tabla.rowCount()):
            celdas = [self.tabla.item(fila, c).text() if self.tabla.item(fila, c) else ""
                      for c in range(self.tabla.columnCount())]
            lineas.append("\t".join(celdas))
        portapapeles.setText("\n".join(lineas))

    def _restaurar(self, datos: dict) -> None:
        claves = [c for c, _, _ in self._catalogo()]
        metodo = datos.get("metodo")
        if metodo in claves:
            self.combo.setCurrentIndex(claves.index(metodo))
        for nombre, widget in self._campos.items():
            valor = datos.get(nombre)
            if valor is None:
                continue
            if isinstance(widget, QSpinBox):
                try:
                    widget.setValue(int(float(valor)))
                except (TypeError, ValueError):
                    pass
            else:
                widget.setText(str(valor))
        if datos.get("puntos"):
            self.puntos.setPlainText(str(datos["puntos"]))
        self.calcular()

    def aplicar_paleta(self, paleta) -> None:
        self.paleta = paleta
        self.grafica.aplicar_paleta(paleta)


_NOTAS = {
    "biseccion": "Necesita un intervalo [a, b] donde f cambie de signo. Siempre "
                 "converge, pero despacio: gana un bit de precisión por iteración.",
    "newton": "Converge muy rápido cerca de la raíz, pero puede divergir si la "
              "derivada se anula o el punto de partida está lejos.",
    "secante": "Como Newton pero sin calcular la derivada: usa dos puntos "
               "anteriores para estimar la pendiente.",
    "trapecio": "Sustituye la curva por segmentos rectos. El error baja con n².",
    "simpson": "Usa parábolas en vez de rectas: mucho más preciso. Necesita n par "
               "(se ajusta solo si pone impar).",
    "lagrange": "Polinomio que pasa exactamente por todos los puntos. Con muchos "
                "puntos oscila mucho (fenómeno de Runge).",
    "newton_interp": "Mismo polinomio que Lagrange, pero calculado de forma que "
                     "añadir un punto no obliga a rehacerlo todo.",
    "euler": "El método más simple: avanza en línea recta con la pendiente del "
             "punto actual. Error del orden de h.",
    "rk4": "Promedia cuatro pendientes por paso. Error del orden de h⁴: con el "
           "mismo h es muchísimo más preciso que Euler.",
}
