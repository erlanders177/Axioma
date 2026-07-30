"""Resolución de ecuaciones e inecuaciones de una variable, con su gráfica.

Arreglos respecto a la versión 1:

* Si la ecuación no tenía soluciones, ``soluciones_str`` no existía y el ``datos``
  del historial lanzaba ``UnboundLocalError``, que se mostraba como un error
  incomprensible.
* Sólo admitía la variable ``x``; ahora se detecta la variable automáticamente.
* Sólo aceptaba sintaxis de Python (``x**2``); ahora también ``x^2`` y ``2x``.
* Las raíces complejas hacían fallar ``sol.evalf(4)``; ahora se muestran aparte.
"""

from __future__ import annotations

import numpy as np
import sympy as sp
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QHBoxLayout, QLineEdit, QPlainTextEdit, QSplitter, QVBoxLayout,
    QWidget,
)

from ..core import historial as hist
from ..core import simbolico as sim
from ..core.config import config
from . import tema
from .comunes import PanelHistorial, aviso, boton, etiqueta, separador, tarjeta
from .grafica import CICLO, PanelGrafica, cortar_saltos, muestrear

EJEMPLOS = [
    "x^2 - 4 = 0",
    "2x + 5 = 13",
    "x^3 - 6x^2 + 11x - 6 = 0",
    "sin(x) = 0.5",
    "exp(x) = 10",
    "1/x + 1/(x+1) = 1",
    "sqrt(x + 2) = x",
    "x^2 - 4 > 0",
    "2x + 1 <= 7",
]

#: Símbolos de desigualdad admitidos, del más largo al más corto para que
#: «<=» se detecte antes que «<».
_DESIGUALDADES = ["<=", ">=", "≤", "≥", "<", ">"]


class ErrorEcuacion(sim.ErrorSimbolico):
    """La ecuación no se pudo interpretar o resolver."""


class PanelEcuaciones(QWidget):
    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.paleta = tema.paleta(config["tema"])
        self._construir()

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna())

        marco_hist, col_hist = tarjeta()
        self.historial = PanelHistorial("ecuaciones", "Historial de ecuaciones")
        self.historial.restaurar.connect(self._restaurar)
        col_hist.addWidget(self.historial)
        division.addWidget(marco_hist)

        division.setStretchFactor(0, 3)
        division.setStretchFactor(1, 2)
        division.setSizes([700, 360])
        raiz.addWidget(division)

    def _crear_columna(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Ecuación", "seccion"))

        self.entrada = QLineEdit()
        self.entrada.setPlaceholderText("Por ejemplo:  x^2 - 5x + 6 = 0    ·    x^2 - 4 > 0")
        self.entrada.setToolTip(
            "Puede usar ^ para potencias y omitir el signo de multiplicar (2x).\n"
            "Funciones: sin, cos, tan, exp, log, sqrt, abs…\n"
            "Si no escribe «=», se supone «= 0».\n"
            "También resuelve inecuaciones con <, >, <= y >=."
        )
        self.entrada.returnPressed.connect(self.resolver)
        col.addWidget(self.entrada)

        opciones = QHBoxLayout()
        opciones.setSpacing(10)
        self.chk_complejas = QCheckBox("Mostrar soluciones complejas")
        self.chk_complejas.setChecked(True)
        self.chk_complejas.stateChanged.connect(self._recalcular_silencioso)
        opciones.addWidget(self.chk_complejas)

        self.chk_exactas = QCheckBox("Mostrar valores exactos")
        self.chk_exactas.setChecked(True)
        self.chk_exactas.stateChanged.connect(self._recalcular_silencioso)
        opciones.addWidget(self.chk_exactas)
        opciones.addStretch()
        col.addLayout(opciones)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Resolver", "primario", self.resolver))
        acciones.addWidget(boton("Limpiar", "", self.limpiar))
        acciones.addWidget(boton("Ejemplo", "", self._ejemplo,
                                 tooltip="Cargar una ecuación de ejemplo"))
        acciones.addStretch()
        col.addLayout(acciones)
        col.addWidget(separador())

        self.salida = QPlainTextEdit()
        self.salida.setProperty("clase", "mono")
        self.salida.setReadOnly(True)
        self.salida.setMinimumHeight(120)
        self.salida.setPlaceholderText("Aquí aparecerán las soluciones…")
        col.addWidget(self.salida, 1)
        columna.addWidget(marco)

        marco_grafica, col_grafica = tarjeta()
        col_grafica.addWidget(etiqueta("Gráfica", "seccion"))
        self.grafica = PanelGrafica(self.paleta, 5.0, 3.0, con_barra=False)
        self.grafica.setMinimumHeight(220)
        col_grafica.addWidget(self.grafica, 1)
        columna.addWidget(marco_grafica, 1)

        self._limpiar_grafica("Resuelva una ecuación para ver su gráfica")
        return contenedor

    # ------------------------------------------------------------ resolución -- #

    @staticmethod
    def _detectar_desigualdad(texto: str) -> str | None:
        for simbolo in _DESIGUALDADES:
            if simbolo in texto:
                return simbolo
        return None

    @staticmethod
    def _interpretar(texto: str, separador_relacion: str = "=") -> tuple[sp.Expr, sp.Symbol]:
        """Convierte el texto en una expresión comparada con cero y su variable."""
        limpio = texto.strip()
        if not limpio:
            raise ErrorEcuacion("Introduzca una ecuación")
        if limpio.count(separador_relacion) > 1:
            raise ErrorEcuacion(
                f"La expresión sólo puede tener un signo «{separador_relacion}»"
            )

        izquierda, _, derecha = limpio.partition(separador_relacion)
        if not derecha.strip():
            derecha = "0"

        expr_izq = sim.analizar(izquierda)
        expr_der = sim.analizar(derecha)

        # Las incógnitas se toman de los dos lados **antes** de simplificar: en
        # «x + 1 = x + 2» la diferencia es la constante −1, pero la ecuación sí
        # tiene incógnita (simplemente no tiene solución).
        libres = sim.incognitas(expr_izq, expr_der)

        if not libres:
            raise ErrorEcuacion(
                "La expresión no contiene ninguna incógnita. "
                "Use una letra como variable, por ejemplo «x»."
            )
        if len(libres) > 1:
            nombres = ", ".join(s.name for s in libres)
            raise ErrorEcuacion(
                f"Hay varias incógnitas ({nombres}). Este módulo resuelve una sola; "
                f"use «Sistemas» para varias variables."
            )
        return sp.simplify(expr_izq - expr_der), libres[0]

    def resolver(self, *, silencioso: bool = False) -> None:
        texto = self.entrada.text().strip()
        if not texto:
            if not silencioso:
                aviso(self, "Introduzca una ecuación.", "Ecuaciones")
            return

        desigualdad = self._detectar_desigualdad(texto)
        if desigualdad:
            self._resolver_inecuacion(texto, desigualdad, silencioso)
            return

        try:
            expresion, variable = self._interpretar(texto)
            soluciones = self._buscar_soluciones(expresion, variable)
        except sim.ErrorSimbolico as e:
            self.salida.setPlainText(str(e))
            self._limpiar_grafica("Sin gráfica")
            if not silencioso:
                aviso(self, str(e), "Ecuaciones")
            return
        except Exception as e:  # sympy puede lanzar de casi todo
            mensaje = f"No se pudo resolver la ecuación ({type(e).__name__}: {e})"
            self.salida.setPlainText(mensaje)
            self._limpiar_grafica("Sin gráfica")
            if not silencioso:
                aviso(self, mensaje, "Ecuaciones")
            return

        informe, resumen = self._formatear(expresion, variable, soluciones)
        self.salida.setPlainText(informe)
        self._dibujar(expresion, variable, soluciones["reales"])

        if not silencioso:
            try:
                entrada = hist.guardar("ecuaciones", f"{texto}   →   {resumen}", {
                    "ecuacion": texto,
                    "variable": variable.name,
                    "soluciones": [str(s) for s in soluciones["reales"]],
                })
                self.historial.anadir(entrada)
            except hist.ErrorHistorial as e:
                aviso(self, str(e), "Historial")

    def _resolver_inecuacion(self, texto: str, simbolo: str, silencioso: bool) -> None:
        """Resuelve una desigualdad y sombrea en la gráfica el conjunto solución."""
        normalizado = simbolo.replace("≤", "<=").replace("≥", ">=")
        try:
            expresion, variable = self._interpretar(texto, simbolo)
        except sim.ErrorSimbolico as e:
            self.salida.setPlainText(str(e))
            self._limpiar_grafica("Sin gráfica")
            if not silencioso:
                aviso(self, str(e), "Inecuaciones")
            return

        relaciones = {
            "<": sp.StrictLessThan, ">": sp.StrictGreaterThan,
            "<=": sp.LessThan, ">=": sp.GreaterThan,
        }
        try:
            conjunto = sp.solveset(
                relaciones[normalizado](expresion, 0), variable, sp.S.Reals
            )
        except (ValueError, TypeError, NotImplementedError) as e:
            mensaje = f"No se pudo resolver la inecuación ({e})"
            self.salida.setPlainText(mensaje)
            self._limpiar_grafica("Sin gráfica")
            if not silencioso:
                aviso(self, mensaje, "Inecuaciones")
            return

        lineas = [
            f"Inecuación normalizada:  {sim.texto(expresion)} {normalizado} 0",
            f"Incógnita:  {variable.name}",
            "",
        ]
        if conjunto == sp.S.EmptySet:
            lineas.append("No hay ningún valor que la cumpla.")
            resumen = "sin solución"
        elif conjunto == sp.S.Reals:
            lineas.append(f"Se cumple para cualquier valor real de {variable.name}.")
            resumen = "todos los reales"
        else:
            lineas.append(f"Solución:  {variable.name} ∈ {sim.texto(conjunto)}")
            resumen = sim.texto(conjunto)
            frontera = sp.solve(sp.Eq(expresion, 0), variable)
            reales = [sp.N(r, 8) for r in frontera if not r.free_symbols and sim.es_real(r)]
            if reales:
                lineas.append("")
                lineas.append("Puntos frontera (donde la expresión vale 0): "
                              + ", ".join(sim.texto(r) for r in reales))

        self.salida.setPlainText("\n".join(lineas))
        self._dibujar(expresion, variable, [], conjunto=conjunto, relacion=normalizado)

        if not silencioso:
            try:
                entrada = hist.guardar("ecuaciones", f"{texto}   →   {resumen}", {
                    "ecuacion": texto,
                    "variable": variable.name,
                })
                self.historial.anadir(entrada)
            except hist.ErrorHistorial:
                pass

    @staticmethod
    def _buscar_soluciones(expresion: sp.Expr, variable: sp.Symbol) -> dict:
        """Separa las soluciones en reales y complejas, comprobándolas.

        ``solve`` puede devolver raíces espurias (por ejemplo al elevar al
        cuadrado ambos lados), así que cada candidata se sustituye en la
        ecuación original.
        """
        # Si al simplificar desaparece la incógnita, la ecuación es una identidad
        # (siempre cierta) o una contradicción (nunca cierta).
        if variable not in expresion.free_symbols:
            constante = sp.simplify(expresion)
            return {"reales": [], "complejas": [], "crudas": [],
                    "identidad": constante == 0}

        crudas = sp.solve(sp.Eq(expresion, 0), variable, dict=False)
        if not isinstance(crudas, (list, tuple)):
            crudas = [crudas]

        reales: list[sp.Expr] = []
        complejas: list[sp.Expr] = []
        for candidata in crudas:
            if not isinstance(candidata, sp.Expr) or candidata.free_symbols:
                continue  # solución paramétrica: no se puede evaluar

            try:
                residuo = complex(expresion.subs(variable, candidata).evalf())
                numerica = complex(candidata.evalf())
            except (TypeError, ValueError, ZeroDivisionError):
                # No se puede evaluar numéricamente: se acepta tal cual, sin
                # decidir si es real o compleja más allá de lo que diga sympy.
                (reales if candidata.is_real else complejas).append(candidata)
                continue

            # Se descartan las raíces espurias (aparecen, por ejemplo, al elevar
            # al cuadrado los dos lados de la ecuación).
            escala = max(1.0, abs(numerica))
            if abs(residuo) > 1e-8 * escala:
                continue

            if abs(numerica.imag) < 1e-12:
                reales.append(candidata if candidata.is_real else sp.re(candidata))
            else:
                complejas.append(candidata)

        return {"reales": reales, "complejas": complejas, "crudas": crudas,
                "identidad": False}

    def _formatear(self, expresion: sp.Expr, variable: sp.Symbol,
                   soluciones: dict) -> tuple[str, str]:
        decimales = max(4, int(config["decimales"]))
        lineas = [
            f"Ecuación normalizada:  {sp.sstr(sp.simplify(expresion))} = 0",
            f"Incógnita:  {variable.name}",
        ]

        if variable not in expresion.free_symbols:
            lineas.append("")
            if soluciones.get("identidad"):
                lineas.append(
                    f"Los dos lados son iguales: la ecuación es una IDENTIDAD.\n"
                    f"Se cumple para cualquier valor de {variable.name}."
                )
                return "\n".join(lineas), "identidad (infinitas soluciones)"
            lineas.append(
                f"Al simplificar, «{variable.name}» desaparece y queda una "
                f"igualdad falsa.\nLa ecuación no tiene solución."
            )
            return "\n".join(lineas), "sin solución"

        grado = None
        try:
            polinomio = sp.Poly(expresion, variable)
            grado = polinomio.degree()
            lineas.append(f"Tipo:  polinómica de grado {grado}")
        except (sp.PolynomialError, sp.GeneratorsNeeded, TypeError):
            lineas.append("Tipo:  no polinómica")

        factorizada = sp.factor(expresion)
        if factorizada != expresion:
            lineas.append(f"Factorizada:  {sp.sstr(factorizada)} = 0")

        lineas.append("")
        reales = soluciones["reales"]
        complejas = soluciones["complejas"]

        if not reales and not complejas:
            if soluciones["crudas"]:
                lineas.append("La ecuación no tiene soluciones concretas "
                              "(la solución depende de otros parámetros).")
            else:
                lineas.append("La ecuación no tiene solución.")
            return "\n".join(lineas), "sin solución"

        partes_resumen: list[str] = []

        if reales:
            lineas.append(f"Soluciones reales ({len(reales)}):")
            for i, solucion in enumerate(reales, 1):
                aproximada = sp.N(solucion, decimales)
                exacta = sp.sstr(sp.nsimplify(solucion, rational=False))
                if self.chk_exactas.isChecked() and exacta != sp.sstr(aproximada):
                    lineas.append(f"   {variable.name}{_subindice(i)} = {aproximada}"
                                  f"        (exacto: {exacta})")
                else:
                    lineas.append(f"   {variable.name}{_subindice(i)} = {aproximada}")
                partes_resumen.append(f"{variable.name}={sp.N(solucion, 6)}")

        if complejas and self.chk_complejas.isChecked():
            lineas.append("")
            lineas.append(f"Soluciones complejas ({len(complejas)}):")
            for i, solucion in enumerate(complejas, 1):
                lineas.append(f"   {variable.name}{_subindice(i)} = {sp.N(solucion, decimales)}")
            if not reales:
                partes_resumen.append(f"{len(complejas)} raíces complejas")

        if grado is not None and len(reales) + len(complejas) < grado:
            lineas.append("")
            lineas.append(f"Nota: una ecuación de grado {grado} tiene {grado} raíces "
                          "contando multiplicidades; algunas pueden estar repetidas.")

        return "\n".join(lineas), ", ".join(partes_resumen) or "sin solución real"

    # -------------------------------------------------------------- gráfica -- #

    def _limpiar_grafica(self, mensaje: str = "") -> None:
        self.grafica.lienzo.limpiar(mensaje)

    def _dibujar(self, expresion: sp.Expr, variable: sp.Symbol, raices: list,
                 *, conjunto=None, relacion: str = "") -> None:
        try:
            funcion = sim.a_funcion(expresion, variable)
        except sim.ErrorSimbolico:
            self._limpiar_grafica("Esta función no se puede representar")
            return

        # Ventana centrada en las raíces, o [-10, 10] si no hay ninguna.
        if raices:
            valores = [float(sp.re(sp.N(r))) for r in raices]
            centro = (min(valores) + max(valores)) / 2
            radio = max(max(valores) - min(valores), 2.0) * 1.5
        else:
            centro, radio = 0.0, 10.0

        xs = np.linspace(centro - radio, centro + radio, 1400)
        ys = cortar_saltos(muestrear(funcion, xs))
        if np.all(np.isnan(ys)):
            self._limpiar_grafica("La función no toma valores reales en ese intervalo")
            return

        eje = self.grafica.lienzo.nuevo_eje()
        eje.plot(xs, ys, color=CICLO[0], linewidth=1.8, label=f"f({variable.name})")

        if raices:
            xr = [float(sp.re(sp.N(r))) for r in raices]
            eje.plot(xr, [0] * len(xr), "o", color=self.paleta.aviso, markersize=7,
                     markeredgecolor=self.paleta.grafico_fondo,
                     label="soluciones", zorder=5)

        # En una inecuación se sombrea la zona donde se cumple la condición.
        if conjunto is not None and relacion:
            self._sombrear_solucion(eje, xs, ys, relacion)

        self.grafica.lienzo.acotar_vertical(eje, ys)
        self.grafica.lienzo.estilizar(eje, etiqueta_x=variable.name, leyenda=True)

    def _sombrear_solucion(self, eje, xs: np.ndarray, ys: np.ndarray, relacion: str) -> None:
        comparaciones = {
            "<": ys < 0, ">": ys > 0, "<=": ys <= 0, ">=": ys >= 0,
        }
        dentro = comparaciones.get(relacion)
        if dentro is None:
            return
        dentro = np.where(np.isnan(ys), False, dentro)
        eje.fill_between(xs, eje.get_ylim()[0], eje.get_ylim()[1], where=dentro,
                         color=self.paleta.exito, alpha=0.16,
                         label="se cumple aquí", transform=eje.get_xaxis_transform())

    # ---------------------------------------------------------------- varios -- #

    def limpiar(self) -> None:
        self.entrada.clear()
        self.salida.clear()
        self._limpiar_grafica("Resuelva una ecuación para ver su gráfica")
        self.entrada.setFocus()

    def _ejemplo(self) -> None:
        actual = self.entrada.text().strip()
        siguiente = 0
        if actual in EJEMPLOS:
            siguiente = (EJEMPLOS.index(actual) + 1) % len(EJEMPLOS)
        self.entrada.setText(EJEMPLOS[siguiente])
        self.resolver(silencioso=True)

    def _recalcular_silencioso(self) -> None:
        if self.entrada.text().strip():
            self.resolver(silencioso=True)

    def _restaurar(self, datos: dict) -> None:
        ecuacion = datos.get("ecuacion")
        if ecuacion:
            self.entrada.setText(str(ecuacion))
            self.entrada.setFocus()
            self.resolver(silencioso=True)

    def aplicar_paleta(self, paleta) -> None:
        self.paleta = paleta
        self.grafica.aplicar_paleta(paleta)
        self._recalcular_silencioso()
        if not self.entrada.text().strip():
            self._limpiar_grafica("Resuelva una ecuación para ver su gráfica")


_SUBINDICES = "₀₁₂₃₄₅₆₇₈₉"


def _subindice(numero: int) -> str:
    return "".join(_SUBINDICES[int(d)] for d in str(numero))
