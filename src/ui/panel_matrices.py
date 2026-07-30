"""Matrices y álgebra lineal."""

from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QComboBox, QHBoxLayout, QPlainTextEdit, QSpinBox, QSplitter,
    QVBoxLayout, QWidget,
)

from ..core import historial as hist
from ..core import matrices as mat
from .comunes import PanelHistorial, aviso, boton, etiqueta, separador, tarjeta

EJEMPLOS = {
    "A": "1  2  3\n4  5  6\n7  8 10",
    "B": "1  0  0\n0  1  0\n0  0  1",
}


class EditorMatriz(QWidget):
    """Cuadro de texto para escribir una matriz, con su indicador de tamaño."""

    def __init__(self, titulo: str, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        columna = QVBoxLayout(self)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(4)

        cabecera = QHBoxLayout()
        cabecera.addWidget(etiqueta(titulo, "seccion"))
        cabecera.addStretch()
        self.dimension = etiqueta("—", "subtitulo")
        cabecera.addWidget(self.dimension)
        columna.addLayout(cabecera)

        self.editor = QPlainTextEdit()
        self.editor.setProperty("clase", "mono")
        fuente = QFont("Consolas")
        fuente.setStyleHint(QFont.Monospace)
        self.editor.setFont(fuente)
        self.editor.setPlaceholderText("1  2\n3  4")
        self.editor.setToolTip(
            "Una fila por línea, elementos separados por espacios o comas.\n"
            "Admite fracciones y expresiones: 1/2, sqrt(2), pi"
        )
        self.editor.textChanged.connect(self._actualizar_dimension)
        columna.addWidget(self.editor, 1)

    def _actualizar_dimension(self) -> None:
        try:
            matriz = mat.analizar_matriz(self.editor.toPlainText())
        except mat.ErrorMatriz:
            self.dimension.setText("—")
            return
        self.dimension.setText(f"{matriz.rows} × {matriz.cols}")

    def texto(self) -> str:
        return self.editor.toPlainText()

    def poner(self, texto: str) -> None:
        self.editor.setPlainText(texto)

    def matriz(self, nombre: str):
        return mat.analizar_matriz(self.editor.toPlainText(), nombre)


class PanelMatrices(QWidget):
    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self._construir()
        self._cambiar_operacion(0)

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna_entrada())
        division.addWidget(self._crear_columna_salida())

        marco_hist, col_hist = tarjeta()
        self.historial = PanelHistorial("matrices", "Historial")
        self.historial.restaurar.connect(self._restaurar)
        col_hist.addWidget(self.historial)
        division.addWidget(marco_hist)

        division.setSizes([390, 460, 290])
        raiz.addWidget(division)

    def _crear_columna_entrada(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Operación", "seccion"))
        self.combo = QComboBox()
        for _, titulo, _ in mat.OPERACIONES_UNARIAS:
            self.combo.addItem("A  ·  " + titulo)
        for _, titulo in mat.OPERACIONES_BINARIAS:
            self.combo.addItem("A y B  ·  " + titulo)
        self.combo.currentIndexChanged.connect(self._cambiar_operacion)
        col.addWidget(self.combo)

        fila_extra = QHBoxLayout()
        self.etiqueta_extra = etiqueta("Exponente:", "subtitulo")
        self.spin_extra = QSpinBox()
        self.spin_extra.setRange(-20, 20)
        self.spin_extra.setValue(2)
        fila_extra.addWidget(self.etiqueta_extra)
        fila_extra.addWidget(self.spin_extra)
        fila_extra.addStretch()
        col.addLayout(fila_extra)

        col.addWidget(separador())

        self.editor_a = EditorMatriz("Matriz A")
        col.addWidget(self.editor_a, 1)

        self.editor_b = EditorMatriz("Matriz B")
        col.addWidget(self.editor_b, 1)

        self.nota = etiqueta("", "nota", ajustar=True)
        col.addWidget(self.nota)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Calcular", "primario", self.calcular))
        acciones.addWidget(boton("Ejemplo", "", self._cargar_ejemplo))
        acciones.addWidget(boton("Limpiar", "", self.limpiar))
        col.addLayout(acciones)

        columna.addWidget(marco, 1)
        return contenedor

    def _crear_columna_salida(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Resultado", "seccion"))
        self.salida = QPlainTextEdit()
        self.salida.setProperty("clase", "mono")
        fuente = QFont("Consolas")
        fuente.setStyleHint(QFont.Monospace)
        self.salida.setFont(fuente)
        self.salida.setReadOnly(True)
        self.salida.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.salida.setPlaceholderText(
            "Escriba una matriz (una fila por línea) y pulse «Calcular»."
        )
        col.addWidget(self.salida, 1)

        fila = QHBoxLayout()
        fila.addWidget(boton("Copiar", "", self._copiar))
        fila.addStretch()
        col.addLayout(fila)
        columna.addWidget(marco, 1)

        return contenedor

    # ---------------------------------------------------------- operaciones -- #

    def _operacion_actual(self) -> tuple[str, str, bool, str | None]:
        """(clave, título, ¿necesita B?, parámetro extra)."""
        indice = self.combo.currentIndex()
        unarias = len(mat.OPERACIONES_UNARIAS)
        if indice < unarias:
            clave, titulo, extra = mat.OPERACIONES_UNARIAS[indice]
            return clave, titulo, False, extra
        clave, titulo = mat.OPERACIONES_BINARIAS[indice - unarias]
        return clave, titulo, True, None

    def _cambiar_operacion(self, _indice: int) -> None:
        clave, _, necesita_b, extra = self._operacion_actual()

        self.editor_b.setVisible(necesita_b)
        self.etiqueta_extra.setVisible(bool(extra))
        self.spin_extra.setVisible(bool(extra))
        if extra:
            self.etiqueta_extra.setText(f"{extra.capitalize()}:")

        if clave == "sistema":
            self.editor_b.dimension.setText("")
            self.nota.setText(
                "Para resolver A·x = b escriba en B la columna de términos "
                "independientes (una fila por línea)."
            )
        else:
            self.nota.setText(_NOTAS.get(clave, ""))
        self.nota.setVisible(bool(self.nota.text()))
        self.salida.clear()

    def calcular(self) -> None:
        clave, titulo, necesita_b, extra = self._operacion_actual()

        try:
            a = self.editor_a.matriz("la matriz A")
            b = self.editor_b.matriz("la matriz B") if necesita_b else None
            parametros = {"exponente": self.spin_extra.value()} if extra else {}
            filas = mat.operar(clave, a, b, parametros)
        except mat.ErrorMatriz as e:
            self.salida.setPlainText(str(e))
            aviso(self, str(e), "Matrices")
            return
        except Exception as e:  # sympy puede lanzar de casi todo
            mensaje = f"No se pudo calcular ({type(e).__name__}: {e})"
            self.salida.setPlainText(mensaje)
            aviso(self, mensaje, "Error")
            return

        self.salida.setPlainText(_formatear(titulo, a, b, filas))

        resumen = next((v.replace("\n", " ") for _, v in filas if v), "")
        operacion = f"{titulo}  ({a.rows}×{a.cols})  →  {resumen[:70]}"
        try:
            entrada = hist.guardar("matrices", operacion, {
                "operacion": clave,
                "a": self.editor_a.texto(),
                "b": self.editor_b.texto() if necesita_b else "",
                "extra": self.spin_extra.value(),
            })
            self.historial.anadir(entrada)
        except hist.ErrorHistorial:
            pass

    # ---------------------------------------------------------------- varios -- #

    def limpiar(self) -> None:
        self.editor_a.poner("")
        self.editor_b.poner("")
        self.salida.clear()

    def _cargar_ejemplo(self) -> None:
        clave, _, necesita_b, _ = self._operacion_actual()
        self.editor_a.poner(EJEMPLOS["A"])
        if clave == "sistema":
            self.editor_a.poner("2  3\n1 -1")
            self.editor_b.poner("7\n1")
        elif necesita_b:
            self.editor_b.poner(EJEMPLOS["B"])
        self.calcular()

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.salida.toPlainText())

    def _restaurar(self, datos: dict) -> None:
        claves_unarias = [c for c, _, _ in mat.OPERACIONES_UNARIAS]
        claves_binarias = [c for c, _ in mat.OPERACIONES_BINARIAS]
        clave = datos.get("operacion")
        if clave in claves_unarias:
            self.combo.setCurrentIndex(claves_unarias.index(clave))
        elif clave in claves_binarias:
            self.combo.setCurrentIndex(len(claves_unarias) + claves_binarias.index(clave))
        if datos.get("a"):
            self.editor_a.poner(str(datos["a"]))
        if datos.get("b"):
            self.editor_b.poner(str(datos["b"]))
        if "extra" in datos:
            try:
                self.spin_extra.setValue(int(datos["extra"]))
            except (TypeError, ValueError):
                pass
        self.calcular()

    def aplicar_paleta(self, paleta) -> None:
        return


def _formatear(titulo: str, a, b, filas: list[tuple[str, str]]) -> str:
    """Compone el informe con las matrices de entrada y los resultados."""
    lineas = [titulo, "=" * len(titulo), ""]

    lineas.append(f"A  ({a.rows} × {a.cols})")
    lineas.append(mat.matriz_a_texto(a))
    if b is not None:
        lineas.append("")
        lineas.append(f"B  ({b.rows} × {b.cols})")
        lineas.append(mat.matriz_a_texto(b))
    lineas.append("")
    lineas.append("-" * 46)
    lineas.append("")

    for etiqueta_fila, valor in filas:
        if not etiqueta_fila and not valor:
            lineas.append("")
        elif "\n" in str(valor):
            lineas.append(f"{etiqueta_fila}:")
            lineas.append(str(valor))
            lineas.append("")
        else:
            lineas.append(f"{etiqueta_fila}:  {valor}")

    return "\n".join(lineas)


_NOTAS = {
    "propiedades": "Rango, determinante, traza e invertibilidad de A.",
    "inversa": "Sólo existe si la matriz es cuadrada y su determinante no es nulo.",
    "pseudoinversa": "Generaliza la inversa a matrices no cuadradas o singulares.",
    "rref": "Eliminación de Gauss-Jordan: la forma escalonada reducida por filas.",
    "autovalores": "Resuelve det(A − λI) = 0 y da los autovectores asociados.",
    "nucleo": "Vectores x que cumplen A·x = 0.",
    "imagen": "Base del espacio generado por las columnas de A.",
    "lu": "Descompone A = L·U (con posibles permutaciones de filas).",
}
