"""Sistemas de ecuaciones lineales.

El parser de la versión anterior se escribía a mano carácter a carácter y fallaba
en muchos casos reales:

* ``variables.update([c for c in eq if c.isalpha()])`` recogía cualquier letra,
  incluidas las de funciones o del lado derecho.
* La extracción del coeficiente aceptaba ``+`` y ``-`` dentro del número, y la
  línea ``coef = float(num_part) * (1.0 if coef == 1.0 else -1.0)`` daba signos
  incorrectos en varios casos.
* El lado derecho tenía que ser un número suelto: ``= 7/2`` o ``= 2+3`` fallaban.
* Sólo admitía variables a la izquierda; ``2x = 3y + 1`` no funcionaba.
* ``np.linalg.solve`` exige una matriz cuadrada, así que un sistema de 2
  ecuaciones con 3 incógnitas (o al revés) sólo producía un error genérico.

Aquí se usa sympy: acepta cualquier forma algebraica lineal y distingue entre
solución única, sistema incompatible y sistema con infinitas soluciones.
"""

from __future__ import annotations

import sympy as sp
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox, QFormLayout, QHBoxLayout, QLineEdit, QPlainTextEdit, QScrollArea,
    QSpinBox, QSplitter, QVBoxLayout, QWidget,
)
from sympy.parsing.sympy_parser import (
    convert_xor, implicit_multiplication_application, parse_expr,
    standard_transformations,
)

from ..core import pasos as pasos_core
from ..core.config import config
from .comunes import (
    PanelModulo,
    aviso, boton, etiqueta, formatear_pasos, tarjeta,
)
from .usar_resultado import permitir_usar_valores

TRANSFORMACIONES = standard_transformations + (
    implicit_multiplication_application,
    convert_xor,
)

MIN_ECUACIONES = 2
MAX_ECUACIONES = 10

EJEMPLO = [
    "2x + 3y = 7",
    "x - y = 1",
]


class ErrorSistema(ValueError):
    """El sistema no se pudo interpretar."""


class PanelSistemas(PanelModulo):
    MODULO = "sistemas"
    TITULO_HISTORIAL = "Historial de sistemas"

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.campos: list[QLineEdit] = []
        self._construir()
        self._actualizar_campos()

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna())


        division.setStretchFactor(0, 3)
        division.setSizes([680])
        raiz.addWidget(division)

    def _crear_columna(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()

        cabecera = QHBoxLayout()
        cabecera.addWidget(etiqueta("Número de ecuaciones", "seccion"))
        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setRange(MIN_ECUACIONES, MAX_ECUACIONES)
        self.spin_cantidad.setValue(2)
        self.spin_cantidad.valueChanged.connect(self._actualizar_campos)
        cabecera.addWidget(self.spin_cantidad)
        cabecera.addStretch()
        cabecera.addWidget(etiqueta(
            "Las incógnitas se detectan solas (x, y, z, a, b…)", "subtitulo"))
        col.addLayout(cabecera)

        area = QScrollArea()
        area.setWidgetResizable(True)
        self.contenedor_campos = QWidget()
        self.formulario = QFormLayout(self.contenedor_campos)
        self.formulario.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.formulario.setHorizontalSpacing(10)
        self.formulario.setVerticalSpacing(7)
        area.setWidget(self.contenedor_campos)
        area.setMinimumHeight(150)
        col.addWidget(area)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Resolver", "primario", self.resolver))
        acciones.addWidget(boton("Limpiar", "", self.limpiar))
        acciones.addWidget(boton("Ejemplo", "", self._ejemplo))
        self.chk_pasos = QCheckBox("Método de Gauss paso a paso")
        self.chk_pasos.setChecked(True)
        self.chk_pasos.setToolTip(
            "Muestra cada operación sobre las filas de la matriz ampliada"
        )
        self.chk_pasos.stateChanged.connect(lambda: self.resolver(silencioso=True))
        acciones.addWidget(self.chk_pasos)
        acciones.addStretch()
        col.addLayout(acciones)
        columna.addWidget(marco)

        marco_salida, col_salida = tarjeta()
        col_salida.addWidget(etiqueta("Resultado", "seccion"))
        self.salida = QPlainTextEdit()
        permitir_usar_valores(self.salida, "solución")
        self.salida.setProperty("clase", "mono")
        self.salida.setReadOnly(True)
        self.salida.setPlaceholderText(
            "Escriba las ecuaciones (por ejemplo «2x + 3y = 7») y pulse «Resolver»."
        )
        col_salida.addWidget(self.salida, 1)

        fila = QHBoxLayout()
        fila.addWidget(boton("Copiar", "", self._copiar))
        fila.addStretch()
        col_salida.addLayout(fila)
        columna.addWidget(marco_salida, 1)

        return contenedor

    def _actualizar_campos(self) -> None:
        """Ajusta el número de campos conservando lo que el usuario ya escribió."""
        textos = [campo.text() for campo in self.campos]
        objetivo = self.spin_cantidad.value()

        while self.formulario.count():
            elemento = self.formulario.takeAt(0)
            widget = elemento.widget()
            if widget is not None:
                widget.setParent(None)
        self.campos.clear()

        for i in range(objetivo):
            campo = QLineEdit()
            campo.setPlaceholderText("Ej.: 2x + 3y - z = 7")
            campo.returnPressed.connect(self.resolver)
            if i < len(textos):
                campo.setText(textos[i])
            self.campos.append(campo)
            self.formulario.addRow(f"Ecuación {i + 1}:", campo)

    # ------------------------------------------------------------ resolución -- #

    @staticmethod
    def _interpretar(lineas: list[str]) -> tuple[list[sp.Eq], list[sp.Symbol]]:
        ecuaciones: list[sp.Eq] = []
        incognitas: set[sp.Symbol] = set()

        for numero, linea in enumerate(lineas, 1):
            if linea.count("=") != 1:
                raise ErrorSistema(
                    f"La ecuación {numero} debe tener exactamente un signo «=»"
                )
            izquierda, _, derecha = linea.partition("=")
            try:
                expr_izq = parse_expr(izquierda, transformations=TRANSFORMACIONES)
                expr_der = parse_expr(derecha, transformations=TRANSFORMACIONES)
            except (SyntaxError, TypeError, ValueError, AttributeError) as e:
                raise ErrorSistema(f"No se entiende la ecuación {numero}: {e}") from e

            expresion = sp.expand(expr_izq - expr_der)
            simbolos = expresion.free_symbols
            if not simbolos:
                raise ErrorSistema(
                    f"La ecuación {numero} no contiene incógnitas"
                )

            culpable = _termino_no_lineal(expresion, sorted(simbolos, key=str))
            if culpable:
                raise ErrorSistema(
                    f"La ecuación {numero} no es lineal ({culpable}). Este módulo "
                    f"resuelve sistemas lineales; use «Ecuaciones» para una sola "
                    f"incógnita no lineal."
                )

            ecuaciones.append(sp.Eq(expresion, 0))
            incognitas |= simbolos

        return ecuaciones, sorted(incognitas, key=lambda s: s.name)

    def resolver(self, *, silencioso: bool = False) -> None:
        lineas = [campo.text().strip() for campo in self.campos]
        lineas = [linea for linea in lineas if linea]

        if len(lineas) < MIN_ECUACIONES:
            mensaje = f"Escriba al menos {MIN_ECUACIONES} ecuaciones."
            self.salida.setPlainText(mensaje)
            if not silencioso:
                aviso(self, mensaje, "Sistemas")
            return

        try:
            ecuaciones, incognitas = self._interpretar(lineas)
            informe, resumen = self._resolver_sistema(lineas, ecuaciones, incognitas)
        except ErrorSistema as e:
            self.salida.setPlainText(str(e))
            if not silencioso:
                aviso(self, str(e), "Sistemas")
            return
        except Exception as e:
            mensaje = f"No se pudo resolver el sistema ({type(e).__name__}: {e})"
            self.salida.setPlainText(mensaje)
            if not silencioso:
                aviso(self, mensaje, "Sistemas")
            return

        self.salida.setPlainText(informe)
        if not silencioso:
            self.guardar_en_historial(f"Sistema {len(lineas)}×{len(incognitas)}  →  {resumen}",
                {"ecuaciones": lineas,
                 "incognitas": [s.name for s in incognitas]},)

    def _resolver_sistema(self, lineas: list[str], ecuaciones: list[sp.Eq],
                          incognitas: list[sp.Symbol]) -> tuple[str, str]:
        decimales = max(4, int(config["decimales"]))
        nombres = [s.name for s in incognitas]

        salida = [
            f"Sistema de {len(ecuaciones)} ecuaciones con {len(incognitas)} "
            f"incógnitas ({', '.join(nombres)})",
            "",
        ]
        for i, linea in enumerate(lineas, 1):
            salida.append(f"  ({i})  {linea}")
        salida.append("")

        matriz, vector = sp.linear_eq_to_matrix(ecuaciones, incognitas)
        ampliada = matriz.row_join(vector)
        rango = matriz.rank()
        rango_ampliada = ampliada.rank()

        salida.append("Matriz de coeficientes:")
        salida.extend(_matriz_a_texto(matriz, vector))
        salida.append("")
        salida.append(f"Rango de la matriz de coeficientes:  {rango}")
        salida.append(f"Rango de la matriz ampliada:         {rango_ampliada}")

        if matriz.rows == matriz.cols:
            determinante = sp.simplify(matriz.det())
            salida.append(f"Determinante:  {determinante}")

        salida.append("")

        # Teorema de Rouché-Frobenius.
        if rango < rango_ampliada:
            salida.append("El sistema es INCOMPATIBLE: no tiene ninguna solución.")
            salida.append("(el rango de la matriz ampliada es mayor que el de la "
                          "matriz de coeficientes)")
            return "\n".join(salida), "incompatible"

        solucion = sp.linsolve(ecuaciones, incognitas)
        if not solucion:
            salida.append("El sistema no tiene solución.")
            return "\n".join(salida), "sin solución"

        tupla = next(iter(solucion))
        libres = sorted({str(s) for expresion in tupla for s in expresion.free_symbols})

        if rango == len(incognitas) and not libres:
            salida.append("Sistema COMPATIBLE DETERMINADO: solución única.")
            salida.append("")
            partes = []
            for nombre, valor in zip(nombres, tupla):
                exacto = sp.sstr(sp.nsimplify(valor, rational=True))
                aproximado = sp.sstr(sp.N(valor, decimales))
                if exacto != aproximado:
                    salida.append(f"   {nombre} = {aproximado}        (exacto: {exacto})")
                else:
                    salida.append(f"   {nombre} = {aproximado}")
                partes.append(f"{nombre}={sp.N(valor, 6)}")
            salida.append(self._desarrollo(ecuaciones, incognitas))
            return "\n".join(salida), ", ".join(partes)

        grados = len(incognitas) - rango
        salida.append(f"Sistema COMPATIBLE INDETERMINADO: infinitas soluciones "
                      f"({grados} grado{'s' if grados != 1 else ''} de libertad).")
        salida.append("")
        salida.append("Solución general:")
        for nombre, valor in zip(nombres, tupla):
            salida.append(f"   {nombre} = {sp.sstr(sp.simplify(valor))}")
        if libres:
            salida.append("")
            salida.append(f"donde {', '.join(libres)} puede tomar cualquier valor.")
        salida.append(self._desarrollo(ecuaciones, incognitas))
        return "\n".join(salida), f"infinitas soluciones ({grados} g. de libertad)"

    def _desarrollo(self, ecuaciones: list, incognitas: list) -> str:
        """Bloque con la eliminación de Gauss, o vacío si está desactivado."""
        if not self.chk_pasos.isChecked():
            return ""
        try:
            lista = pasos_core.pasos_sistema(ecuaciones, incognitas)
        except Exception:
            # El desarrollo es un extra: si falla, el resultado ya está arriba.
            return ""
        if not lista:
            return ""
        return "\n" + "─" * 58 + "\nPASO A PASO (método de Gauss)\n\n" + formatear_pasos(lista)

    # ---------------------------------------------------------------- varios -- #

    def limpiar(self) -> None:
        for campo in self.campos:
            campo.clear()
        self.salida.clear()
        if self.campos:
            self.campos[0].setFocus()

    def _ejemplo(self) -> None:
        self.spin_cantidad.setValue(len(EJEMPLO))
        for campo, texto in zip(self.campos, EJEMPLO):
            campo.setText(texto)
        self.resolver(silencioso=True)

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.salida.toPlainText())

    def restaurar_datos(self, datos: dict) -> None:
        ecuaciones = datos.get("ecuaciones") or []
        if not ecuaciones:
            return
        cantidad = max(MIN_ECUACIONES, min(MAX_ECUACIONES, len(ecuaciones)))
        self.spin_cantidad.setValue(cantidad)
        self._actualizar_campos()
        for campo, texto in zip(self.campos, ecuaciones):
            campo.setText(str(texto))
        self.resolver(silencioso=True)

    def aplicar_paleta(self, paleta) -> None:
        return


def _termino_no_lineal(expresion: sp.Expr, simbolos: list[sp.Symbol]) -> str:
    """Describe el primer término no lineal encontrado, o ``""`` si es lineal.

    Una expresión es afín en sus incógnitas si **todas** sus derivadas segundas
    (incluidas las cruzadas) son cero. Así se detectan a la vez ``x²``, ``x·y``,
    ``1/x`` y ``sen(x)``, que un análisis de grado por separado dejaría pasar.
    """
    for i, a in enumerate(simbolos):
        for b in simbolos[i:]:
            try:
                segunda = sp.simplify(sp.diff(expresion, a, b))
            except (TypeError, ValueError, sp.SympifyError):
                return f"«{a}» aparece de forma no lineal"
            if segunda != 0:
                if a == b:
                    return f"«{a}» no aparece elevada a la primera potencia"
                return f"aparece el producto «{a}·{b}»"
    return ""


def _matriz_a_texto(matriz: sp.Matrix, vector: sp.Matrix) -> list[str]:
    """Formatea la matriz ampliada alineando las columnas."""
    filas: list[list[str]] = []
    for i in range(matriz.rows):
        fila = [sp.sstr(matriz[i, j]) for j in range(matriz.cols)]
        fila.append(sp.sstr(vector[i, 0]))
        filas.append(fila)

    if not filas:
        return []

    anchos = [max(len(fila[c]) for fila in filas) for c in range(len(filas[0]))]
    lineas = []
    for fila in filas:
        coeficientes = "  ".join(v.rjust(anchos[i]) for i, v in enumerate(fila[:-1]))
        lineas.append(f"  [ {coeficientes}  |  {fila[-1].rjust(anchos[-1])} ]")
    return lineas
