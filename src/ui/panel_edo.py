"""Ecuaciones diferenciales ordinarias, con campo de direcciones."""

from __future__ import annotations

import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QSpinBox,
    QSplitter, QVBoxLayout, QWidget,
)

from ..core import edo
from ..core import numerico
from ..core.config import config
from . import tema
from .comunes import (
    PanelModulo,
    TablaResultados, aviso, boton, etiqueta, separador, tarjeta,
)
from .grafica import CICLO, PanelGrafica

EJEMPLOS = [
    ("y' + 2y = 0", ""),
    ("y' = x*y", "y(0) = 1"),
    ("y'' - 3y' + 2y = 0", "y(0) = 1, y'(0) = 0"),
    ("y'' + y = sin(x)", "y(0) = 0, y'(0) = 1"),
    ("y' = x - y", "y(0) = 2"),
    ("dy/dx = y/x", ""),
]


class PanelEDO(PanelModulo):
    MODULO = "edo"
    TITULO_HISTORIAL = "Historial"

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.paleta = tema.paleta(config["tema"])
        self._ejemplo_actual = -1
        self._construir()
        # `currentIndexChanged` no se dispara al construir con el índice ya en 0,
        # así que hay que ocultar a mano lo que no corresponde al modo inicial.
        self._cambiar_modo(0)

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_entrada())
        division.addWidget(self._crear_columna_salida())


        division.setSizes([380, 500])
        raiz.addWidget(division)

    def _crear_columna_entrada(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Modo", "seccion"))
        self.combo_modo = QComboBox()
        self.combo_modo.addItems([
            "Resolver (solución exacta)",
            "Resolver con Laplace",
            "Sistema de ecuaciones",
            "Resolver por aproximación (Runge-Kutta)",
        ])
        self.combo_modo.currentIndexChanged.connect(self._cambiar_modo)
        col.addWidget(self.combo_modo)

        col.addWidget(separador())

        formulario = QFormLayout()
        formulario.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        formulario.setRowWrapPolicy(QFormLayout.WrapLongRows)
        formulario.setHorizontalSpacing(10)
        formulario.setVerticalSpacing(7)

        self.entrada = QLineEdit()
        self.entrada.setPlaceholderText("y' + 2y = 0     ·     y'' + y = sin(x)")
        self.entrada.setToolTip(
            "Escriba la derivada como y', y'' … o como dy/dx.\n"
            "Se admite la notación de clase: 2y en vez de 2*y."
        )
        self.entrada.returnPressed.connect(self.resolver)
        formulario.addRow("Ecuación:", self.entrada)

        self.condiciones = QLineEdit()
        self.condiciones.setPlaceholderText("y(0) = 1, y'(0) = 0     (opcional)")
        self.condiciones.returnPressed.connect(self.resolver)
        self.etiqueta_condiciones = etiqueta("Condiciones:")
        formulario.addRow(self.etiqueta_condiciones, self.condiciones)

        fila_variables = QHBoxLayout()
        self.var_dependiente = QLineEdit("y")
        self.var_dependiente.setFixedWidth(44)
        self.var_dependiente.setAlignment(Qt.AlignCenter)
        self.var_independiente = QLineEdit("x")
        self.var_independiente.setFixedWidth(44)
        self.var_independiente.setAlignment(Qt.AlignCenter)
        fila_variables.addWidget(self.var_dependiente)
        fila_variables.addWidget(etiqueta("en función de", "subtitulo"))
        fila_variables.addWidget(self.var_independiente)
        fila_variables.addStretch()
        formulario.addRow("Función:", fila_variables)
        col.addLayout(formulario)

        # -- sistema de ecuaciones ------------------------------------------ #
        self.contenedor_sistema = QWidget()
        col_sistema = QVBoxLayout(self.contenedor_sistema)
        col_sistema.setContentsMargins(0, 0, 0, 0)
        col_sistema.addWidget(etiqueta("Ecuaciones del sistema", "seccion"))
        self.sistema = QPlainTextEdit()
        self.sistema.setProperty("clase", "mono")
        self.sistema.setPlaceholderText("x' = y\ny' = -x")
        self.sistema.setMaximumHeight(110)
        col_sistema.addWidget(self.sistema)
        col.addWidget(self.contenedor_sistema)

        # -- aproximación numérica ------------------------------------------ #
        self.contenedor_numerico = QWidget()
        rejilla = QFormLayout(self.contenedor_numerico)
        rejilla.setContentsMargins(0, 0, 0, 0)
        rejilla.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.campo_fxy = QLineEdit("x - y")
        self.campo_fxy.setToolTip("Lado derecho de y′ = f(x, y)")
        rejilla.addRow("y′ = f(x,y) =", self.campo_fxy)
        self.campo_x0 = QLineEdit("0")
        rejilla.addRow("x₀ =", self.campo_x0)
        self.campo_y0 = QLineEdit("1")
        rejilla.addRow("y₀ =", self.campo_y0)
        self.campo_h = QLineEdit("0.1")
        rejilla.addRow("paso h =", self.campo_h)
        self.spin_pasos = QSpinBox()
        self.spin_pasos.setRange(1, 5000)
        self.spin_pasos.setValue(20)
        rejilla.addRow("pasos =", self.spin_pasos)
        col.addWidget(self.contenedor_numerico)

        self.nota = etiqueta("", "nota", ajustar=True)
        col.addWidget(self.nota)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Resolver", "primario", self.resolver))
        acciones.addWidget(boton("Ejemplo", "", self._cargar_ejemplo))
        acciones.addWidget(boton("Limpiar", "", self.limpiar))
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
        self.titulo_grafica = etiqueta("Campo de direcciones", "seccion")
        col_graf.addWidget(self.titulo_grafica)
        self.grafica = PanelGrafica(self.paleta, 5.0, 3.2, con_barra=False)
        self.grafica.setMinimumHeight(230)
        col_graf.addWidget(self.grafica, 1)
        columna.addWidget(marco_graf, 2)

        return contenedor

    # ---------------------------------------------------------------- modos -- #

    @property
    def _modo(self) -> str:
        return ["exacta", "laplace", "sistema", "numerico"][self.combo_modo.currentIndex()]

    def _cambiar_modo(self, _indice: int) -> None:
        modo = self._modo
        es_sistema = modo == "sistema"
        es_numerico = modo == "numerico"
        directa = modo in ("exacta", "laplace")

        self.entrada.setVisible(directa)
        self.condiciones.setVisible(directa)
        self.etiqueta_condiciones.setVisible(directa)
        self.contenedor_sistema.setVisible(es_sistema)
        self.contenedor_numerico.setVisible(es_numerico)

        if modo == "laplace":
            self.var_independiente.setText("t")
            self.nota.setText(
                "El método de Laplace necesita condiciones iniciales en 0. "
                "Se transforma la ecuación, se despeja Y(s) y se antitransforma."
            )
        elif es_sistema:
            self.nota.setText(
                "Una ecuación por línea, todas de primer orden: «x' = y» y «y' = -x». "
                "Máximo cuatro."
            )
        elif es_numerico:
            self.nota.setText(
                "Para las ecuaciones que no tienen solución exacta. Runge-Kutta de "
                "orden 4 aproxima la curva paso a paso."
            )
        else:
            self.var_independiente.setText("x")
            self.nota.setText(
                "Si no pone condiciones iniciales se obtiene la solución general, "
                "con sus constantes C1, C2…"
            )

        self.tabla.limpiar()
        self.grafica.lienzo.limpiar("Pulse «Resolver»")

    # ------------------------------------------------------------ resolución -- #

    def resolver(self) -> None:
        modo = self._modo
        try:
            if modo == "sistema":
                self._resolver_sistema()
            elif modo == "numerico":
                self._resolver_numerico()
            else:
                self._resolver_exacta(modo)
        except (edo.ErrorEDO, numerico.ErrorNumerico) as e:
            self.tabla.limpiar()
            self.grafica.lienzo.limpiar("Sin gráfica")
            aviso(self, str(e), "Ecuaciones diferenciales")
        except Exception as e:  # sympy lanza tipos muy variados
            self.tabla.limpiar()
            self.grafica.lienzo.limpiar("Sin gráfica")
            aviso(self, f"No se pudo resolver ({type(e).__name__}: {e})", "Error")

    def _resolver_exacta(self, modo: str) -> None:
        texto_edo = self.entrada.text().strip()
        condiciones = self.condiciones.text().strip()
        dependiente = self.var_dependiente.text().strip() or "y"
        independiente = self.var_independiente.text().strip() or "x"

        if modo == "laplace":
            filas = edo.resolver_por_laplace(texto_edo, condiciones,
                                             dependiente, independiente)
        else:
            filas = edo.resolver(texto_edo, condiciones, dependiente, independiente)

        self.tabla.mostrar(filas)
        self._dibujar_campo(texto_edo, dependiente, independiente)
        self._guardar(f"{texto_edo}" + (f"   con {condiciones}" if condiciones else ""),
                      {"modo": modo, "ecuacion": texto_edo, "condiciones": condiciones,
                       "dependiente": dependiente, "independiente": independiente})

    def _resolver_sistema(self) -> None:
        lineas = self.sistema.toPlainText().splitlines()
        independiente = self.var_independiente.text().strip() or "t"
        filas = edo.resolver_sistema(lineas, independiente)
        self.tabla.mostrar(filas)
        self.grafica.lienzo.limpiar(
            "El campo de direcciones sólo se dibuja para una ecuación"
        )
        activas = [l.strip() for l in lineas if l.strip()]
        self._guardar(f"Sistema: {'  |  '.join(activas)}",
                      {"modo": "sistema", "sistema": self.sistema.toPlainText()})

    def _resolver_numerico(self) -> None:
        try:
            x0 = float(self.campo_x0.text().replace(",", "."))
            y0 = float(self.campo_y0.text().replace(",", "."))
            h = float(self.campo_h.text().replace(",", "."))
        except ValueError:
            raise numerico.ErrorNumerico(
                "x₀, y₀ y h deben ser números"
            ) from None

        expresion = self.campo_fxy.text().strip()
        pasos = self.spin_pasos.value()
        iteraciones, nota = numerico.runge_kutta_4(
            expresion, x0, y0, h, pasos,
            self.var_independiente.text().strip() or "x",
            self.var_dependiente.text().strip() or "y",
        )

        decimales = config["decimales"]
        filas = [
            ("Ecuación", f"y′ = {expresion}"),
            ("Condición inicial", f"y({x0:g}) = {y0:g}"),
            ("Método", "Runge-Kutta de orden 4"),
            ("", nota),
            ("", ""),
        ]
        from ..core.formato import formatear
        for it in iteraciones:
            x = it.valores.get("xₙ")
            y = it.valores.get("yₙ")
            filas.append((f"n = {it.n}",
                          f"x = {formatear(x, decimales)}    y = {formatear(y, decimales)}"))
        self.tabla.mostrar(filas)

        self._dibujar_solucion_numerica(iteraciones, expresion)
        self._guardar(
            f"RK4: y′ = {expresion},  y({x0:g}) = {y0:g},  h = {h:g}",
            {"modo": "numerico", "fxy": expresion, "x0": x0, "y0": y0,
             "h": h, "pasos": pasos},
        )

    # -------------------------------------------------------------- gráficas -- #

    def _dibujar_campo(self, texto_edo: str, dependiente: str,
                       independiente: str) -> None:
        """Campo de direcciones: cada segmento tiene la pendiente que marca la EDO."""
        try:
            pendiente, expresion = edo.campo_direcciones(
                texto_edo, dependiente, independiente
            )
        except edo.ErrorEDO as e:
            self.grafica.lienzo.limpiar(str(e))
            return

        eje = self.grafica.lienzo.nuevo_eje()
        rejilla = np.linspace(-4, 4, 19)
        X, Y = np.meshgrid(rejilla, rejilla)

        with np.errstate(all="ignore"):
            try:
                M = np.asarray(pendiente(X, Y), dtype=float)
            except Exception:
                self.grafica.lienzo.limpiar("El campo no se puede representar")
                return

        if M.shape != X.shape:
            M = np.full(X.shape, float(M))
        M = np.where(np.isfinite(M), M, np.nan)

        # Se normaliza cada vector para que todos midan igual: interesa la
        # dirección, no el módulo.
        U = np.ones_like(M)
        norma = np.sqrt(1 + M ** 2)
        eje.quiver(X, Y, U / norma, M / norma,
                   color=self.paleta.grafico_linea, alpha=0.65,
                   angles="xy", pivot="middle", headwidth=3, headlength=4)

        eje.set_xlim(-4.4, 4.4)
        eje.set_ylim(-4.4, 4.4)
        self.grafica.lienzo.estilizar(
            eje, titulo=f"y′ = {expresion}",
            etiqueta_x=independiente, etiqueta_y=dependiente,
        )
        self.titulo_grafica.setText("Campo de direcciones")

    def _dibujar_solucion_numerica(self, iteraciones: list, expresion: str) -> None:
        xs = [it.valores["xₙ"] for it in iteraciones]
        ys = [it.valores["yₙ"] for it in iteraciones]

        eje = self.grafica.lienzo.nuevo_eje()
        eje.plot(xs, ys, "o-", color=CICLO[0], markersize=3.5, linewidth=1.6,
                 label="Runge-Kutta 4")
        self.grafica.lienzo.estilizar(
            eje, titulo=f"y′ = {expresion}", etiqueta_x="x", etiqueta_y="y",
            leyenda=True,
        )
        self.titulo_grafica.setText("Solución aproximada")

    # ---------------------------------------------------------------- varios -- #

    def _guardar(self, operacion: str, datos: dict) -> None:
        self.guardar_en_historial(operacion, datos)

    def limpiar(self) -> None:
        self.entrada.clear()
        self.condiciones.clear()
        self.sistema.clear()
        self.tabla.limpiar()
        self.grafica.lienzo.limpiar("Pulse «Resolver»")

    def _cargar_ejemplo(self) -> None:
        if self._modo == "sistema":
            self.sistema.setPlainText("x' = y\ny' = -x")
            self.var_independiente.setText("t")
        elif self._modo == "numerico":
            self.campo_fxy.setText("x - y")
        else:
            self._ejemplo_actual = (self._ejemplo_actual + 1) % len(EJEMPLOS)
            ecuacion, condiciones = EJEMPLOS[self._ejemplo_actual]
            self.entrada.setText(ecuacion)
            self.condiciones.setText(condiciones)
        self.resolver()

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.tabla.texto_plano())

    def restaurar_datos(self, datos: dict) -> None:
        modos = ["exacta", "laplace", "sistema", "numerico"]
        modo = datos.get("modo", "exacta")
        if modo in modos:
            self.combo_modo.setCurrentIndex(modos.index(modo))
        if datos.get("ecuacion"):
            self.entrada.setText(str(datos["ecuacion"]))
        if datos.get("condiciones"):
            self.condiciones.setText(str(datos["condiciones"]))
        if datos.get("sistema"):
            self.sistema.setPlainText(str(datos["sistema"]))
        if datos.get("fxy"):
            self.campo_fxy.setText(str(datos["fxy"]))
        for clave, campo in (("x0", self.campo_x0), ("y0", self.campo_y0),
                             ("h", self.campo_h)):
            if clave in datos:
                campo.setText(str(datos[clave]))
        if "pasos" in datos:
            try:
                self.spin_pasos.setValue(int(datos["pasos"]))
            except (TypeError, ValueError):
                pass
        if datos.get("dependiente"):
            self.var_dependiente.setText(str(datos["dependiente"]))
        if datos.get("independiente"):
            self.var_independiente.setText(str(datos["independiente"]))
        self.resolver()

    def aplicar_paleta(self, paleta) -> None:
        self.paleta = paleta
        self.grafica.aplicar_paleta(paleta)
