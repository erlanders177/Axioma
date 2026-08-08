"""Ventana principal: una sola pantalla con apartados encajables.

La calculadora ocupa el centro y no se cierra; los demás apartados se enganchan
a su alrededor desde el lateral, los que se quieran a la vez, y se colocan
arrastrándolos: al lado, encima, debajo, apilados en pestañas o sueltos fuera de
la ventana. No se cambia de página, porque trabajar con una figura geométrica y
la ecuación que la describe exige verlas juntas, no una detrás de otra.

Los paneles se construyen la primera vez que se abren, así el arranque es
inmediato, y no se destruyen al cerrarlos: lo escrito sigue ahí al volver.
"""

from __future__ import annotations

import webbrowser
from typing import Callable

from PyQt5.QtCore import QByteArray, QSize, Qt
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView, QApplication, QComboBox, QDockWidget, QHBoxLayout,
    QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QShortcut,
    QStatusBar, QVBoxLayout, QWidget,
)

from .. import __autor__, __contacto__, __nombre__, __url__, __version__
from ..core import figuras, unidades
from ..core import historial as hist
from ..core.config import config
from ..core.rutas import dir_datos, recurso
from . import tema
from .apartado import Apartado
from .barra_calculo import BarraCalculo
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

#: Anchos de referencia al repartir la pantalla entre los bloques abiertos.
LATERAL = 216              # el menú de la izquierda, que es fijo
CENTRO_MINIMO = 620        # lo que necesita el teclado de la calculadora
ANCHO_MINIMO_BLOQUE = 330  # por debajo de esto un apartado no se puede usar
ANCHO_COMODO_BLOQUE = 560  # si sobra sitio, tampoco hace falta más

#: Encabezados de la navegación: (índice donde empieza, título del grupo).
#: Con dieciséis módulos una lista plana se lee mal y no cabe sin desplazar.
GRUPOS_NAVEGACION: list[tuple[int, str]] = [
    (0, "Cálculo diario"),
    (4, "Álgebra"),
    (8, "Análisis"),
    (12, "Datos y geometría"),
]




class VentanaPrincipal(QMainWindow):
    """Una sola pantalla: la calculadora, y los apartados que se enganchen.

    No hay páginas. La calculadora ocupa el centro y no se cierra nunca; los
    demás apartados son bloques que se abren desde el lateral y se colocan donde
    el usuario quiera —al lado, encima, debajo, apilados en pestañas o sueltos
    fuera de la ventana—, tantos a la vez como quepan. La disposición se guarda,
    así que la aplicación vuelve a abrirse tal y como se dejó.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"{__nombre__} {__version__}")
        self.setMinimumSize(1100, 700)
        self._paneles: dict[str, QWidget] = {}
        self._apartados: dict[str, Apartado] = {}
        self._bloques: dict[str, QDockWidget] = {}
        self._orden: list[str] = []          # orden de apertura, para el tope
        self._constructores: dict[str, Callable[[], QWidget]] = {}
        self.paleta = tema.paleta(config["tema"])

        # La rejilla libre: los bloques se pueden anidar en filas y columnas en
        # vez de limitarse a las cuatro bandas del borde.
        self.setDockNestingEnabled(True)
        self.setDockOptions(
            QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks
            | QMainWindow.AllowTabbedDocks
        )

        self._construir()
        self._aplicar_tema()
        self._restaurar_geometria()
        self._atajos()
        self._restaurar_disposicion()

        app = QApplication.instance()
        if app is not None:
            app.focusChanged.connect(self._seguir_el_foco)

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        for clave, _, _, _, clase in MODULOS:
            self._constructores[clave] = clase

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

        # La calculadora está siempre: es el sitio desde el que se trabaja.
        self.apartado_calculadora = self._crear_apartado("calculadora")
        columna.addWidget(self.apartado_calculadora, 1)

        # La barra de cálculo sirve a todos los apartados abiertos.
        self.barra = BarraCalculo()
        self.barra.calculado.connect(self._guardar_calculo_de_la_barra)
        self.barra.variables_cambiadas.connect(self._avisar_de_las_variables)
        columna.addWidget(self.barra)

        raiz.addWidget(contenedor, 1)
        self._activo = self.apartado_calculadora

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(f"{unidades.resumen()}  ·  {figuras.resumen()}")

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
        self.navegacion.setSelectionMode(QAbstractItemView.NoSelection)
        self.navegacion.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.navegacion.setIconSize(QSize(1, 1))
        self.navegacion.setToolTip(
            "Pulse para enganchar un apartado a la pantalla; vuelva a pulsar "
            "para quitarlo.\nLuego se arrastran por su título para colocarlos."
        )

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

        self.navegacion.itemClicked.connect(self._pulsar_en_el_menu)
        columna.addWidget(self.navegacion, 1)

        pie = QWidget()
        pie_col = QVBoxLayout(pie)
        pie_col.setContentsMargins(10, 8, 10, 12)
        pie_col.setSpacing(4)

        fila_tope = QHBoxLayout()
        fila_tope.setSpacing(6)
        fila_tope.addWidget(etiqueta("A la vez:", "subtitulo"))
        self.combo_tope = QComboBox()
        self.combo_tope.setToolTip(
            "Cuántos apartados puede haber enganchados a la vez, sin contar la "
            "calculadora.\nAl pasarse se cierra el más antiguo, para que nada "
            "quede aplastado."
        )
        for texto, valor in (("sin tope", 0), ("2", 2), ("3", 3), ("4", 4)):
            self.combo_tope.addItem(texto, valor)
        tope = int(config["max_paneles"] or 0)
        self.combo_tope.setCurrentIndex(max(0, self.combo_tope.findData(tope)))
        self.combo_tope.currentIndexChanged.connect(self._cambiar_tope)
        fila_tope.addWidget(self.combo_tope, 1)
        pie_col.addLayout(fila_tope)

        pie_col.addWidget(boton("Cerrar apartados", "", self.cerrar_todos,
                                tooltip="Dejar sólo la calculadora"))
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

    def _atajos(self) -> None:
        QShortcut(QKeySequence("Ctrl+T"), self, self._alternar_tema)
        QShortcut(QKeySequence("F1"), self, self._abrir_manual)
        QShortcut(QKeySequence("Ctrl+Space"), self, self.barra.enfocar)
        QShortcut(QKeySequence("Ctrl+W"), self, self._cerrar_el_activo)
        QShortcut(QKeySequence("Ctrl+Q"), self, self.close)
        # Sólo hay teclas del 1 al 9; el resto de apartados se abren con el ratón.
        for indice in range(min(9, len(MODULOS))):
            QShortcut(
                QKeySequence(f"Ctrl+{indice + 1}"), self,
                lambda i=indice: self.ir_a_modulo(i),
            )

    # ------------------------------------------------------ abrir y cerrar -- #

    def _crear_apartado(self, clave: str) -> Apartado:
        """Construye el panel del módulo (una sola vez) y lo envuelve."""
        titulo = next(m[2] for m in MODULOS if m[0] == clave)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            panel = self._constructores[clave]()
        except Exception as e:  # un módulo roto no debe tumbar la aplicación
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self, "Error al abrir el apartado",
                f"No se pudo cargar «{titulo}»:\n\n{type(e).__name__}: {e}",
            )
            raise
        finally:
            QApplication.restoreOverrideCursor()

        apartado = Apartado(panel, clave)
        apartado.restaurar.connect(panel.restaurar_datos)
        if hasattr(panel, "aplicar_paleta"):
            panel.aplicar_paleta(self.paleta)
        self._paneles[clave] = panel
        self._apartados[clave] = apartado
        return apartado

    def abrir(self, clave: str, *, area=Qt.RightDockWidgetArea) -> None:
        """Engancha un apartado a la pantalla, o lo trae al frente si ya está."""
        if clave == "calculadora":
            self.apartado_calculadora.panel.setFocus()
            self._activo = self.apartado_calculadora
            return

        bloque = self._bloques.get(clave)
        if bloque is not None:
            bloque.show()
            bloque.raise_()
            self._activo = self._apartados[clave]
            self._anotar_uso(clave)
            self._marcar_menu()
            return

        try:
            apartado = self._apartados.get(clave) or self._crear_apartado(clave)
        except Exception:
            return

        icono, titulo = next((m[1], m[2]) for m in MODULOS if m[0] == clave)
        bloque = QDockWidget(f"{icono}   {titulo}", self)
        bloque.setObjectName(f"bloque_{clave}")   # lo necesita saveState()
        bloque.setWidget(apartado)
        bloque.setAllowedAreas(Qt.AllDockWidgetAreas)
        bloque.setFeatures(
            QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable
            | QDockWidget.DockWidgetClosable
        )
        bloque.visibilityChanged.connect(lambda _=False: self._marcar_menu())
        self._bloques[clave] = bloque

        # Un bloque nuevo se apoya en el último abierto en vez de partir la
        # pantalla otra vez. Si ya no queda ancho para otra columna se coloca
        # debajo: es preferible a estrujar la calculadora hasta que el teclado
        # deje de verse. El usuario puede recolocarlo arrastrándolo.
        self.addDockWidget(area, bloque)
        anteriores = [c for c in self._orden if c in self._bloques and c != clave]
        if anteriores:
            vecino = self._bloques[anteriores[-1]]
            if not vecino.isFloating():
                self.splitDockWidget(vecino, bloque, self._orientacion_para_el_nuevo())

        bloque.show()   # addDockWidget no lo muestra si la ventana aún no lo está
        self._activo = apartado
        self._anotar_uso(clave)
        self._repartir_el_ancho()
        self._marcar_menu()

    def _orientacion_para_el_nuevo(self) -> int:
        """¿El bloque nuevo cabe en otra columna, o va debajo del anterior?"""
        columnas = len({b.x() for b in self._bloques.values() if not b.isFloating()})
        sitio = self.width() - LATERAL - CENTRO_MINIMO
        return Qt.Horizontal if sitio >= ANCHO_MINIMO_BLOQUE * (columnas + 1) else Qt.Vertical

    def _repartir_el_ancho(self) -> None:
        """Da a cada bloque un ancho de trabajo sin ahogar a la calculadora.

        Sin esto, Qt reparte según lo que pida cada panel, y los paneles piden
        mucho: dos bloques abiertos dejaban el teclado de la calculadora con
        media tecla asomando.
        """
        laterales = [b for b in self._bloques.values() if not b.isFloating()]
        if not laterales:
            return
        # Los bloques apilados en la misma columna comparten ancho, así que lo
        # que cuenta para el reparto son las columnas, no los bloques.
        columnas = max(1, len({b.x() for b in laterales}))
        disponible = max(0, self.width() - LATERAL - CENTRO_MINIMO)
        ancho = max(ANCHO_MINIMO_BLOQUE, min(ANCHO_COMODO_BLOQUE, disponible // columnas))
        self.resizeDocks(laterales, [ancho] * len(laterales), Qt.Horizontal)

    def cerrar(self, clave: str) -> None:
        """Quita un apartado de la pantalla. El panel se conserva en memoria."""
        bloque = self._bloques.pop(clave, None)
        if bloque is None:
            return
        if clave in self._orden:
            self._orden.remove(clave)
        bloque.setWidget(None)
        apartado = self._apartados.get(clave)
        if apartado is not None:
            apartado.setParent(None)
        self.removeDockWidget(bloque)
        bloque.deleteLater()
        if self._activo is apartado:
            self._activo = self.apartado_calculadora
        self._marcar_menu()

    def alternar(self, clave: str) -> None:
        """Abre el apartado si está cerrado, y lo cierra si está abierto."""
        if clave in self._bloques:
            self.cerrar(clave)
        else:
            self.abrir(clave)

    def cerrar_todos(self) -> None:
        for clave in list(self._bloques):
            self.cerrar(clave)

    def _cerrar_el_activo(self) -> None:
        clave = getattr(self._activo, "clave", "")
        if clave and clave != "calculadora":
            self.cerrar(clave)

    def _anotar_uso(self, clave: str) -> None:
        """Registra el orden de apertura y aplica el tope si lo hay."""
        if clave in self._orden:
            self._orden.remove(clave)
        self._orden.append(clave)

        tope = int(config["max_paneles"] or 0)
        if tope > 0:
            # Se cierra el más antiguo, que es el que lleva más tiempo sin usarse.
            while len(self._orden) > tope:
                self.cerrar(self._orden[0])

    def _cambiar_tope(self) -> None:
        config["max_paneles"] = self.combo_tope.currentData()
        if self._orden:
            self._anotar_uso(self._orden[-1])

    # ------------------------------------------------------------- lateral -- #

    def _pulsar_en_el_menu(self, elemento: QListWidgetItem) -> None:
        indice = self._modulo_de_fila.get(self.navegacion.row(elemento))
        if indice is not None:
            self.alternar(MODULOS[indice][0])

    def _marcar_menu(self) -> None:
        """Marca en el lateral qué apartados están enganchados ahora mismo."""
        for indice, (clave, icono, titulo_mod, _, _) in enumerate(MODULOS):
            fila = self._fila_de_modulo.get(indice)
            elemento = self.navegacion.item(fila) if fila is not None else None
            if elemento is None:
                continue
            abierto = clave == "calculadora" or clave in self._bloques
            elemento.setText(f"{'●' if abierto else '　'} {icono.ljust(2)}  {titulo_mod}")
            fuente = elemento.font()
            fuente.setBold(abierto)
            elemento.setFont(fuente)

    def ir_a_modulo(self, indice: int) -> None:
        """Abre el apartado que ocupa esa posición en ``MODULOS`` y lo enfoca."""
        if 0 <= indice < len(MODULOS):
            self.abrir(MODULOS[indice][0])

    # -------------------------------------------------------- foco y barra -- #

    def _seguir_el_foco(self, _viejo, nuevo) -> None:
        """El apartado activo es aquel donde está el cursor del usuario."""
        widget = nuevo
        while widget is not None:
            if isinstance(widget, Apartado):
                self._activo = widget
                return
            widget = widget.parentWidget()

    @property
    def historial(self):
        """Historial del apartado activo (el de la calculadora por defecto)."""
        return self._activo.historial

    def _guardar_calculo_de_la_barra(self, operacion: str, datos: dict) -> None:
        """Lo calculado en la barra pertenece al apartado en el que se está."""
        apartado = self._activo
        modulo = getattr(apartado.panel, "MODULO", "") or apartado.clave
        try:
            entrada = hist.guardar(modulo, operacion, datos)
        except hist.ErrorHistorial:
            return
        apartado.historial.anadir(entrada)

    def _avisar_de_las_variables(self) -> None:
        """Permite a los paneles reaccionar si dependen de las variables."""
        for panel in self._paneles.values():
            if hasattr(panel, "variables_actualizadas"):
                panel.variables_actualizadas()

    # -------------------------------------------------------- disposición -- #

    def _restaurar_disposicion(self) -> None:
        """Vuelve a dejar la pantalla como estaba al cerrar."""
        guardada = config["disposicion"] or {}
        for clave in guardada.get("abiertos", []):
            if clave in self._constructores and clave != "calculadora":
                self.abrir(clave)
        estado = guardada.get("estado")
        if estado:
            try:
                self.restoreState(QByteArray.fromBase64(estado.encode("ascii")))
            except (ValueError, UnicodeEncodeError):
                pass       # una disposición ilegible no debe impedir arrancar
        self._marcar_menu()

    def _guardar_disposicion(self) -> None:
        config["disposicion"] = {
            "abiertos": list(self._orden),
            "estado": bytes(self.saveState().toBase64()).decode("ascii"),
        }
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
            <p><b>Atajos:</b> Ctrl+1…9 abre un apartado · Ctrl+W cierra el
               activo · Ctrl+Espacio va a la barra de cálculo ·
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
        self._guardar_disposicion()
        config.guardar()
        super().closeEvent(evento)
