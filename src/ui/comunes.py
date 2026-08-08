"""Widgets y utilidades compartidas por todos los paneles."""

from __future__ import annotations

from typing import Callable

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QAbstractItemView, QFileDialog, QFrame, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from ..core import historial as hist
from ..core.formato import formatear, normalizar

ROL_ID = int(Qt.UserRole)
ROL_DATOS = int(Qt.UserRole) + 1


# --------------------------------------------------------------------------- #
# Fábricas sencillas
# --------------------------------------------------------------------------- #


def etiqueta(texto: str, clase: str = "", *, ajustar: bool = False) -> QLabel:
    widget = QLabel(texto)
    if clase:
        widget.setProperty("clase", clase)
    if ajustar:
        widget.setWordWrap(True)
    return widget


def boton(texto: str, clase: str = "", al_pulsar: Callable | None = None,
          *, tooltip: str = "") -> QPushButton:
    widget = QPushButton(texto)
    if clase:
        widget.setProperty("clase", clase)
    if al_pulsar is not None:
        widget.clicked.connect(al_pulsar)
    if tooltip:
        widget.setToolTip(tooltip)
    return widget


def tarjeta(*, margen: int = 14, espaciado: int = 10) -> tuple[QFrame, QVBoxLayout]:
    """Contenedor con fondo y borde redondeado, más su layout vertical."""
    marco = QFrame()
    marco.setProperty("clase", "tarjeta")
    disposicion = QVBoxLayout(marco)
    disposicion.setContentsMargins(margen, margen, margen, margen)
    disposicion.setSpacing(espaciado)
    return marco, disposicion


def separador() -> QFrame:
    linea = QFrame()
    linea.setProperty("clase", "separador")
    linea.setFrameShape(QFrame.HLine)
    linea.setFixedHeight(1)
    return linea


def aviso(padre: QWidget, mensaje: str, titulo: str = "Aviso") -> None:
    QMessageBox.warning(padre, titulo, mensaje)


def informar(padre: QWidget, mensaje: str, titulo: str = "Listo") -> None:
    QMessageBox.information(padre, titulo, mensaje)


def confirmar(padre: QWidget, mensaje: str, titulo: str = "Confirmar") -> bool:
    respuesta = QMessageBox.question(
        padre, titulo, mensaje,
        QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
    )
    return respuesta == QMessageBox.Yes


# --------------------------------------------------------------------------- #
# Campo numérico
# --------------------------------------------------------------------------- #


class CampoNumerico(QLineEdit):
    """Campo de texto para números, expresiones, variables y unidades.

    Además de un número suelto acepta:

    * expresiones (``2*pi``, ``sqrt(2)``, ``5*sin(30)``);
    * las variables definidas en la barra de cálculo (``r``, ``h``…);
    * unidades, si el campo se crea con ``unidades=True`` (``5 cm``, ``50 mm``).

    Así no hay que salir del módulo a calcular un dato para volver a teclearlo.
    """

    aceptado = pyqtSignal()

    def __init__(self, marcador: str = "0", padre: QWidget | None = None, *,
                 unidades: bool = False) -> None:
        super().__init__(padre)
        self.admite_unidades = unidades
        self.setPlaceholderText(marcador)
        self.setAlignment(Qt.AlignRight)
        self.returnPressed.connect(self.aceptado.emit)

    def valor(self, *, obligatorio: bool = True) -> float | None:
        """Número que representa el campo, ignorando la unidad si la lleva.

        Raises:
            ValueError: con un mensaje explicando por qué no se entiende.
        """
        cantidad = self.cantidad(obligatorio=obligatorio)
        return None if cantidad is None else cantidad.valor

    def cantidad(self, *, obligatorio: bool = True):
        """Devuelve una ``magnitudes.Cantidad`` (valor y unidad), o ``None``."""
        from ..core import magnitudes
        from ..core import variables as vars_compartidas
        from ..core.config import config
        from ..core.evaluador import ErrorExpresion, evaluar

        crudo = self.text().strip()
        if not crudo:
            if obligatorio:
                raise ValueError("Falta un valor")
            return None

        # 1. Un número suelto es lo más frecuente: se prueba primero.
        try:
            return magnitudes.Cantidad(float(crudo.replace(",", ".")))
        except ValueError:
            pass

        # 2. Con unidades, si el campo las admite.
        if self.admite_unidades and magnitudes.contiene_unidades(crudo):
            try:
                return magnitudes.evaluar(crudo)
            except magnitudes.ErrorMagnitud as e:
                raise ValueError(str(e)) from None

        # 3. Expresión o variable.
        try:
            valor = evaluar(crudo, config["modo_angulo"], vars_compartidas.valores())
        except ErrorExpresion as e:
            raise ValueError(f"«{crudo}»: {e}") from None
        return magnitudes.Cantidad(float(valor))

    def poner(self, valor: float | str) -> None:
        self.setText(valor if isinstance(valor, str) else formatear(valor, 10))


# --------------------------------------------------------------------------- #
# Tabla de resultados
# --------------------------------------------------------------------------- #


class TablaResultados(QTableWidget):
    """Tabla de dos columnas (magnitud, valor) para mostrar resultados."""

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(0, 2, padre)
        self.setHorizontalHeaderLabels(["Magnitud", "Valor"])
        self.verticalHeader().setVisible(False)
        self.setAlternatingRowColors(True)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setShowGrid(False)
        # La primera columna toma lo justo para su texto y la segunda se queda con
        # el resto: al revés, los valores largos (fórmulas exactas, matrices) se
        # cortaban aunque sobrara espacio a la izquierda.
        cabecera = self.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(1, QHeaderView.Stretch)
        cabecera.setMaximumSectionSize(340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def mostrar(self, filas: list[tuple[str, str]]) -> None:
        self.setRowCount(len(filas))
        for i, (magnitud, valor) in enumerate(filas):
            self.setItem(i, 0, QTableWidgetItem(magnitud))
            celda = QTableWidgetItem(valor)
            celda.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            fuente = QFont("Consolas")
            fuente.setStyleHint(QFont.Monospace)
            celda.setFont(fuente)
            self.setItem(i, 1, celda)
        self.resizeRowsToContents()

    def limpiar(self) -> None:
        self.setRowCount(0)

    def texto_plano(self) -> str:
        lineas = []
        for fila in range(self.rowCount()):
            magnitud = self.item(fila, 0)
            valor = self.item(fila, 1)
            if magnitud and valor:
                lineas.append(f"{magnitud.text()}: {valor.text()}")
        return "\n".join(lineas)


def formatear_pasos(pasos: list, ancho_sangria: int = 4) -> str:
    """Convierte una lista de ``core.pasos.Paso`` en texto para mostrar.

    Se numeran sólo los pasos de primer nivel: los anidados son detalles de la
    regla que los contiene, no pasos independientes del desarrollo.
    """
    if not pasos:
        return ""

    lineas: list[str] = []
    numero = 0
    for paso in pasos:
        sangria = " " * (ancho_sangria * paso.nivel)
        if paso.nivel == 0:
            numero += 1
            cabecera = f"{numero}. {paso.titulo}" if paso.titulo else ""
        else:
            cabecera = f"· {paso.titulo}" if paso.titulo else ""

        if cabecera:
            lineas.append(f"{sangria}{cabecera}")
        if paso.detalle:
            lineas.append(f"{sangria}   {paso.detalle}")
        if paso.expresion:
            for linea in str(paso.expresion).splitlines():
                lineas.append(f"{sangria}      {linea}")
        lineas.append("")

    return "\n".join(lineas).rstrip()


# --------------------------------------------------------------------------- #
# Panel de historial reutilizable
# --------------------------------------------------------------------------- #


class PanelHistorial(QWidget):
    """Lista de operaciones guardadas, con búsqueda, borrado y exportación.

    Hay **uno solo** para toda la aplicación, en la ventana principal, y va
    mostrando el historial del módulo activo. Antes cada panel llevaba el suyo:
    dieciséis copias de unos 350 px de ancho cada una, repitiendo el mismo
    espacio en pantalla y el mismo código.

    Cada elemento recuerda el **id** de su entrada, así el borrado nunca afecta a
    la fila equivocada aunque la lista se haya filtrado o reordenado (el bug de
    la versión 1, que borraba por posición).
    """

    restaurar = pyqtSignal(dict)

    def __init__(self, modulo: str, titulo: str = "Historial",
                 padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.modulo = modulo
        self._construir(titulo)
        self.recargar()

    def cambiar_modulo(self, modulo: str, titulo: str = "") -> None:
        """Pasa a mostrar el historial de otro módulo."""
        if modulo == self.modulo:
            return
        self.modulo = modulo
        if titulo:
            self.titulo.setText(titulo)
        self.buscador.clear()
        self.recargar()

    def _construir(self, titulo: str) -> None:
        disposicion = QVBoxLayout(self)
        disposicion.setContentsMargins(0, 0, 0, 0)
        disposicion.setSpacing(8)

        cabecera = QHBoxLayout()
        self.titulo = etiqueta(titulo, "seccion")
        cabecera.addWidget(self.titulo)
        cabecera.addStretch()
        self.contador = etiqueta("", "subtitulo")
        cabecera.addWidget(self.contador)
        disposicion.addLayout(cabecera)

        self.buscador = QLineEdit()
        self.buscador.setPlaceholderText("Buscar en el historial…")
        self.buscador.setClearButtonEnabled(True)
        self.buscador.textChanged.connect(self._filtrar)
        disposicion.addWidget(self.buscador)

        self.lista = QListWidget()
        self.lista.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.lista.itemSelectionChanged.connect(self._actualizar_botones)
        self.lista.itemDoubleClicked.connect(self._restaurar_elemento)
        self.lista.setToolTip("Haga doble clic en una operación para volver a cargarla")
        disposicion.addWidget(self.lista, 1)

        acciones = QHBoxLayout()
        acciones.setSpacing(6)
        self.btn_borrar = boton("Borrar selección", "peligro", self._borrar_seleccion)
        self.btn_borrar.setEnabled(False)
        self.btn_limpiar = boton("Vaciar todo", "peligro", self._limpiar_todo)
        self.btn_exportar = boton("Exportar…", "", self._exportar)
        acciones.addWidget(self.btn_borrar)
        acciones.addWidget(self.btn_limpiar)
        acciones.addWidget(self.btn_exportar)
        disposicion.addLayout(acciones)

    # -- carga y actualización -------------------------------------------- #

    def recargar(self) -> None:
        self.lista.clear()
        try:
            entradas = hist.cargar(self.modulo)
        except hist.ErrorHistorial as e:
            aviso(self, str(e), "Historial")
            entradas = []
        for entrada in entradas:
            self.lista.addItem(self._crear_elemento(entrada))
        self._filtrar(self.buscador.text())
        self._actualizar_botones()

    def anadir(self, entrada: dict) -> None:
        """Inserta al principio la entrada recién guardada."""
        self.lista.insertItem(0, self._crear_elemento(entrada))
        self._filtrar(self.buscador.text())
        self._actualizar_botones()

    @staticmethod
    def _crear_elemento(entrada: dict) -> QListWidgetItem:
        fecha = hist.fecha_legible(entrada)
        texto = entrada.get("operacion", "")
        elemento = QListWidgetItem(f"{texto}    ·  {fecha}" if fecha else texto)
        elemento.setData(ROL_ID, entrada.get("id", ""))
        elemento.setData(ROL_DATOS, entrada.get("datos", {}))
        elemento.setToolTip(texto)
        return elemento

    def _filtrar(self, texto: str) -> None:
        consulta = normalizar(texto.strip())
        visibles = 0
        for fila in range(self.lista.count()):
            elemento = self.lista.item(fila)
            coincide = consulta in normalizar(elemento.text())
            elemento.setHidden(not coincide)
            visibles += coincide
        total = self.lista.count()
        self.contador.setText(
            f"{visibles} de {total}" if consulta else (f"{total} operaciones" if total else "vacío")
        )

    def _actualizar_botones(self) -> None:
        seleccion = bool(self.lista.selectedItems())
        self.btn_borrar.setEnabled(seleccion)
        self.btn_limpiar.setEnabled(self.lista.count() > 0)
        self.btn_exportar.setEnabled(self.lista.count() > 0)

    # -- acciones ---------------------------------------------------------- #

    def _restaurar_elemento(self, elemento: QListWidgetItem) -> None:
        datos = elemento.data(ROL_DATOS)
        if isinstance(datos, dict) and datos:
            self.restaurar.emit(datos)

    def _borrar_seleccion(self) -> None:
        seleccionados = self.lista.selectedItems()
        if not seleccionados:
            return
        ids = [e.data(ROL_ID) for e in seleccionados if e.data(ROL_ID)]
        try:
            borradas = hist.borrar(self.modulo, ids)
        except hist.ErrorHistorial as e:
            aviso(self, str(e), "Historial")
            return
        for elemento in seleccionados:
            self.lista.takeItem(self.lista.row(elemento))
        self._filtrar(self.buscador.text())
        self._actualizar_botones()
        if borradas == 0:
            aviso(self, "No se encontraron esas entradas en el archivo.", "Historial")

    def _limpiar_todo(self) -> None:
        if self.lista.count() == 0:
            return
        if not confirmar(
            self,
            f"¿Vaciar por completo el historial de este módulo "
            f"({self.lista.count()} operaciones)?\nEsta acción no se puede deshacer.",
            "Vaciar historial",
        ):
            return
        try:
            hist.limpiar(self.modulo)
        except hist.ErrorHistorial as e:
            aviso(self, str(e), "Historial")
            return
        self.lista.clear()
        self._filtrar("")
        self._actualizar_botones()

    def _exportar(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(
            self, "Exportar historial", f"historial_{self.modulo}.csv",
            "CSV (*.csv);;Texto (*.txt)",
        )
        if not ruta:
            return
        try:
            lineas = hist.exportar(self.modulo, ruta)
        except hist.ErrorHistorial as e:
            aviso(self, str(e), "Exportar")
            return
        informar(self, f"Se exportaron {lineas} operaciones a:\n{ruta}", "Exportado")


# --------------------------------------------------------------------------- #
# Base de todos los paneles
# --------------------------------------------------------------------------- #


class PanelModulo(QWidget):
    """Base común de los dieciséis módulos.

    Se encarga del historial, que ya no vive dentro de cada panel sino en la
    ventana principal: el panel sólo declara a qué módulo pertenece y avisa
    cuando guarda algo. Así el historial ocupa espacio en pantalla una vez en
    lugar de dieciséis, y sigue estando separado por apartados.
    """

    #: Clave del módulo en ``core.historial.MODULOS``.
    MODULO: str = ""
    #: Título que muestra el historial cuando este panel está activo.
    TITULO_HISTORIAL: str = "Historial"

    #: Se emite con la entrada recién guardada, para que la ventana la muestre.
    guardado = pyqtSignal(dict)

    def guardar_en_historial(self, operacion: str,
                             datos: dict | None = None) -> dict | None:
        """Guarda una operación y avisa a la ventana. Devuelve la entrada."""
        if not self.MODULO:
            return None
        try:
            entrada = hist.guardar(self.MODULO, operacion, datos or {})
        except hist.ErrorHistorial as e:
            aviso(self, str(e), "Historial")
            return None
        self.guardado.emit(entrada)
        return entrada

    # -- métodos que cada panel concreta ----------------------------------- #

    def restaurar_datos(self, datos: dict) -> None:
        """Vuelve a cargar una operación del historial. Lo redefine cada panel."""

    def aplicar_paleta(self, paleta) -> None:
        """Reacciona al cambio de tema. Sólo hace falta si el panel dibuja."""
