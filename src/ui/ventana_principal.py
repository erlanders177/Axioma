"""Ventana principal: navegación lateral con todos los módulos.

En la versión anterior cada módulo abría su propia ventana suelta y la ventana
principal las guardaba en un diccionario que se inicializaba **después** de
conectar los botones. Aquí hay una sola ventana con un panel por módulo, creado
de forma diferida la primera vez que se abre (así el arranque es inmediato).
"""

from __future__ import annotations

import webbrowser
from typing import Callable

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QHBoxLayout, QListWidget,
    QListWidgetItem, QMainWindow, QMessageBox, QShortcut, QStackedWidget,
    QStatusBar, QVBoxLayout, QWidget,
)

from .. import __autor__, __contacto__, __nombre__, __url__, __version__
from ..core import figuras, unidades
from ..core.config import config
from ..core.rutas import dir_datos, recurso
from . import tema
from .comunes import boton, etiqueta
from .panel_ajuste import PanelAjuste
from .panel_bases import PanelBases
from .panel_calculadora import PanelCalculadora
from .panel_calculo import PanelCalculo
from .panel_combinatoria import PanelCombinatoria
from .panel_complejos import PanelComplejos
from .panel_conversiones import PanelConversiones
from .panel_ecuaciones import PanelEcuaciones
from .panel_edo import PanelEDO
from .panel_estadistica import PanelEstadistica
from .panel_geometria import PanelGeometria
from .panel_graficador import PanelGraficador
from .panel_matrices import PanelMatrices
from .panel_numerico import PanelNumerico
from .panel_sistemas import PanelSistemas
from .panel_transformadas import PanelTransformadas

#: (clave, icono, título, descripción corta, clase del panel)
#: Los iconos son símbolos de texto, no emoji: los emoji se dibujan en blanco y
#: negro en la fuente de sistema de Windows y quedan irreconocibles.
MODULOS: list[tuple[str, str, str, str, type]] = [
    ("calculadora", "π", "Calculadora", "Científica, con variables y unidades", PanelCalculadora),
    ("graficador", "∿", "Gráficas", "Representar funciones de x", PanelGraficador),
    ("conversiones", "⇄", "Conversiones", "51 magnitudes, 555 unidades", PanelConversiones),
    ("bases", "01", "Bases numéricas", "Binario, hexadecimal y bits", PanelBases),

    ("ecuaciones", "ƒ", "Ecuaciones", "Ecuaciones e inecuaciones", PanelEcuaciones),
    ("sistemas", "≡", "Sistemas", "Ecuaciones lineales", PanelSistemas),
    ("matrices", "⊞", "Matrices", "Álgebra lineal", PanelMatrices),
    ("complejos", "ι", "Complejos", "Aritmética y plano de Argand", PanelComplejos),

    ("calculo", "∫", "Cálculo", "Derivadas, integrales y límites", PanelCalculo),
    ("edo", "∂", "Ec. diferenciales", "EDOs y campo de direcciones", PanelEDO),
    ("transformadas", "ℒ", "Transformadas", "Laplace y Fourier", PanelTransformadas),
    ("numerico", "≈", "Numérico", "Métodos aproximados", PanelNumerico),

    ("estadistica", "μ", "Estadística", "Descriptiva y probabilidad", PanelEstadistica),
    ("ajuste", "⌒", "Ajuste de curvas", "Qué modelo describe los datos", PanelAjuste),
    ("geometria", "△", "Geometría", "61 figuras, planas y cuerpos", PanelGeometria),
    ("combinatoria", "n!", "Combinatoria", "Factorial, C(n,r), P(n,r)", PanelCombinatoria),
]

#: Encabezados de la navegación: (índice donde empieza, título del grupo).
#: Con dieciséis módulos una lista plana se lee mal y no cabe sin desplazar.
GRUPOS_NAVEGACION: list[tuple[int, str]] = [
    (0, "Cálculo diario"),
    (4, "Álgebra"),
    (8, "Análisis"),
    (12, "Datos y geometría"),
]


class VentanaPrincipal(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{__nombre__} {__version__}")
        self.setMinimumSize(1100, 700)
        self._paneles: dict[str, QWidget] = {}
        self._constructores: dict[str, Callable[[], QWidget]] = {}
        self.paleta = tema.paleta(config["tema"])

        self._construir()
        self._aplicar_tema()
        self._restaurar_geometria()
        self._atajos()

        inicial = config["modulo_inicial"]
        claves = [m[0] for m in MODULOS]
        self.ir_a_modulo(claves.index(inicial) if inicial in claves else 0)

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        raiz = QHBoxLayout(central)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        raiz.addWidget(self._crear_lateral())

        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(18, 14, 18, 14)
        columna.setSpacing(12)
        columna.addLayout(self._crear_encabezado())

        self.pila = QStackedWidget()
        columna.addWidget(self.pila, 1)
        raiz.addWidget(contenedor, 1)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            f"{unidades.resumen()}  ·  {figuras.resumen()}"
        )

        # Marcador de posición para cada módulo; el panel real se crea al abrirlo.
        for clave, _, _, _, clase in MODULOS:
            self._constructores[clave] = clase
            hueco = QWidget()
            QVBoxLayout(hueco).addWidget(
                etiqueta("Cargando…", "subtitulo"), alignment=Qt.AlignCenter
            )
            self.pila.addWidget(hueco)

    def _crear_lateral(self) -> QWidget:
        lateral = QWidget()
        lateral.setFixedWidth(216)
        columna = QVBoxLayout(lateral)
        columna.setContentsMargins(0, 0, 0, 0)
        columna.setSpacing(0)

        marca = QWidget()
        marca_col = QVBoxLayout(marca)
        marca_col.setContentsMargins(16, 18, 16, 10)
        marca_col.setSpacing(2)
        titulo = etiqueta(__nombre__, "titulo")
        titulo.setStyleSheet("font-size: 21px; letter-spacing: 1px;")
        marca_col.addWidget(titulo)
        marca_col.addWidget(etiqueta(f"calculadora científica · v{__version__}", "subtitulo"))
        columna.addWidget(marca)

        self.navegacion = QListWidget()
        self.navegacion.setProperty("clase", "navegacion")
        self.navegacion.setSelectionMode(QAbstractItemView.SingleSelection)
        self.navegacion.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.navegacion.setIconSize(QSize(1, 1))

        # Los encabezados de grupo son elementos no seleccionables intercalados,
        # así que la fila de la lista deja de coincidir con el índice del módulo.
        self._fila_de_modulo: dict[int, int] = {}
        self._modulo_de_fila: dict[int, int] = {}
        encabezados = dict(GRUPOS_NAVEGACION)

        for indice, (_, icono, titulo_mod, descripcion, _) in enumerate(MODULOS):
            if indice in encabezados:
                cabecera = QListWidgetItem(encabezados[indice].upper())
                cabecera.setFlags(Qt.NoItemFlags)
                fuente = cabecera.font()
                fuente.setPointSizeF(max(7.5, fuente.pointSizeF() - 2))
                fuente.setBold(True)
                cabecera.setFont(fuente)
                self.navegacion.addItem(cabecera)

            elemento = QListWidgetItem(f"{icono.ljust(2)}   {titulo_mod}")
            elemento.setToolTip(descripcion)
            self._fila_de_modulo[indice] = self.navegacion.count()
            self._modulo_de_fila[self.navegacion.count()] = indice
            self.navegacion.addItem(elemento)

        self.navegacion.currentRowChanged.connect(self._fila_seleccionada)
        columna.addWidget(self.navegacion, 1)

        pie = QWidget()
        pie_col = QVBoxLayout(pie)
        pie_col.setContentsMargins(10, 8, 10, 12)
        pie_col.setSpacing(4)
        self.btn_tema = boton("", "", self._alternar_tema,
                              tooltip="Cambiar entre tema claro y oscuro (Ctrl+T)")
        pie_col.addWidget(self.btn_tema)
        pie_col.addWidget(boton("📖  Manual", "", self._abrir_manual,
                                tooltip="Abrir el manual de usuario (F1)"))
        pie_col.addWidget(boton("ℹ️  Acerca de", "", self._acerca_de))
        columna.addWidget(pie)

        # El lateral necesita su propio fondo para que el borde derecho se vea.
        lateral.setObjectName("lateral")
        return lateral

    def _crear_encabezado(self) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.setSpacing(10)
        columna = QVBoxLayout()
        columna.setSpacing(1)
        self.titulo_modulo = etiqueta("", "titulo")
        self.subtitulo_modulo = etiqueta("", "subtitulo")
        columna.addWidget(self.titulo_modulo)
        columna.addWidget(self.subtitulo_modulo)
        fila.addLayout(columna)
        fila.addStretch()
        return fila

    def _atajos(self) -> None:
        QShortcut(QKeySequence("Ctrl+T"), self, self._alternar_tema)
        QShortcut(QKeySequence("F1"), self, self._abrir_manual)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        # Sólo hay teclas del 1 al 9; el resto de módulos se abren con el ratón.
        for indice in range(min(9, len(MODULOS))):
            QShortcut(
                QKeySequence(f"Ctrl+{indice + 1}"), self,
                lambda i=indice: self.ir_a_modulo(i),
            )

    # -------------------------------------------------------------- lógica -- #

    def _fila_seleccionada(self, fila: int) -> None:
        """Traduce la fila de la lista (que incluye encabezados) al módulo."""
        indice = self._modulo_de_fila.get(fila)
        if indice is not None:
            self._cambiar_modulo(indice)

    def ir_a_modulo(self, indice: int) -> None:
        """Selecciona un módulo por su posición en ``MODULOS``."""
        fila = self._fila_de_modulo.get(indice)
        if fila is not None:
            self.navegacion.setCurrentRow(fila)

    def _cambiar_modulo(self, indice: int) -> None:
        if not 0 <= indice < len(MODULOS):
            return
        clave, icono, titulo_mod, descripcion, _ = MODULOS[indice]

        if clave not in self._paneles:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            try:
                panel = self._constructores[clave]()
            except Exception as e:  # el módulo no debe tumbar la aplicación
                QApplication.restoreOverrideCursor()
                QMessageBox.critical(
                    self, "Error al abrir el módulo",
                    f"No se pudo cargar «{titulo_mod}»:\n\n{type(e).__name__}: {e}",
                )
                return
            QApplication.restoreOverrideCursor()

            antiguo = self.pila.widget(indice)
            self.pila.removeWidget(antiguo)
            antiguo.deleteLater()
            self.pila.insertWidget(indice, panel)
            self._paneles[clave] = panel
            if hasattr(panel, "aplicar_paleta"):
                panel.aplicar_paleta(self.paleta)

        self.pila.setCurrentIndex(indice)
        self.titulo_modulo.setText(f"{icono}  {titulo_mod}")
        self.subtitulo_modulo.setText(descripcion)
        config["modulo_inicial"] = clave

    def _alternar_tema(self) -> None:
        nuevo = "claro" if self.paleta.nombre == "oscuro" else "oscuro"
        config["tema"] = nuevo
        self.paleta = tema.paleta(nuevo)
        self._aplicar_tema()
        for panel in self._paneles.values():
            if hasattr(panel, "aplicar_paleta"):
                panel.aplicar_paleta(self.paleta)

    def _aplicar_tema(self) -> None:
        hoja = tema.hoja_de_estilos(self.paleta)
        hoja += f"""
        QWidget#lateral {{
            background-color: {self.paleta.fondo_panel};
            border-right: 1px solid {self.paleta.borde};
        }}
        """
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(hoja)
        etiqueta_btn = "☀️  Tema claro" if self.paleta.nombre == "oscuro" else "🌙  Tema oscuro"
        self.btn_tema.setText(etiqueta_btn)

    # ---------------------------------------------------------------- menús -- #

    def _abrir_manual(self) -> None:
        ruta = recurso("docs", "manual_usuario.html")
        if not ruta.exists():
            ruta = recurso("manual_usuario.html")
        if not ruta.exists():
            QMessageBox.information(
                self, "Manual",
                "No se encontró el archivo del manual junto a la aplicación.",
            )
            return
        webbrowser.open(ruta.as_uri())

    def _acerca_de(self) -> None:
        cuadro = QMessageBox(self)
        cuadro.setWindowTitle(f"Acerca de {__nombre__}")
        cuadro.setTextFormat(Qt.RichText)
        cuadro.setText(
            f"""
            <h2>{__nombre__} {__version__}</h2>
            <p>Calculadora científica multifunción · {len(MODULOS)} módulos</p>
            <p><b>Desarrollador:</b> {__autor__}<br>
               <b>Contacto:</b> <a href="mailto:{__contacto__}">{__contacto__}</a><br>
               <b>Proyecto:</b> <a href="{__url__}">{__url__}</a></p>
            <hr>
            <p><b>Contenido:</b><br>
               {unidades.resumen()}<br>
               {figuras.resumen()}</p>
            <p><b>Atajos:</b> Ctrl+1…9 cambia de módulo ·
               Ctrl+T cambia el tema · F1 abre el manual</p>
            <p><b>Datos del usuario:</b><br>
               <code>{dir_datos()}</code></p>
            <p style="color:#888;font-size:11px;">
               Copyright 2026 Aarón Aranda Torrijos<br>
               Licencia PolyForm Noncommercial 1.0.0 — libre salvo uso comercial.<br>
               Para uso comercial, escriba a
               <a href="mailto:{__contacto__}">{__contacto__}</a>.</p>
            """
        )
        cuadro.setStandardButtons(QMessageBox.Ok)
        cuadro.exec_()

    # ------------------------------------------------------------ geometría -- #

    def _restaurar_geometria(self) -> None:
        guardada = config["ventana"] or {}
        ancho = int(guardada.get("ancho", 1240))
        alto = int(guardada.get("alto", 800))
        self.resize(ancho, alto)
        if "x" in guardada and "y" in guardada:
            self.move(int(guardada["x"]), int(guardada["y"]))
        if guardada.get("maximizada"):
            self.showMaximized()

    def closeEvent(self, evento) -> None:  # noqa: N802 (nombre impuesto por Qt)
        config["ventana"] = {
            "ancho": self.width(),
            "alto": self.height(),
            "x": self.x(),
            "y": self.y(),
            "maximizada": self.isMaximized(),
        }
        config.guardar()
        super().closeEvent(evento)
