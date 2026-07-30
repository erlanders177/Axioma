"""Tema visual de la aplicación (hoja de estilos Qt)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Paleta:
    nombre: str
    fondo: str
    fondo_panel: str
    fondo_control: str
    fondo_control_hover: str
    borde: str
    texto: str
    texto_suave: str
    acento: str
    acento_hover: str
    acento_texto: str
    exito: str
    aviso: str
    peligro: str
    operador: str
    funcion: str
    # Colores para los gráficos de matplotlib.
    grafico_fondo: str
    grafico_relleno: str
    grafico_linea: str
    grafico_rejilla: str


OSCURO = Paleta(
    nombre="oscuro",
    fondo="#12161f",
    fondo_panel="#1a2030",
    fondo_control="#242c40",
    fondo_control_hover="#2f3950",
    borde="#333d54",
    texto="#e8ecf4",
    texto_suave="#95a1bb",
    acento="#4c8dff",
    acento_hover="#6ba1ff",
    acento_texto="#ffffff",
    exito="#2ecc71",
    aviso="#f0a020",
    peligro="#e5484d",
    operador="#31405e",
    funcion="#2a3348",
    grafico_fondo="#1a2030",
    grafico_relleno="#4c8dff",
    grafico_linea="#8fb8ff",
    grafico_rejilla="#333d54",
)

CLARO = Paleta(
    nombre="claro",
    fondo="#f2f4f8",
    fondo_panel="#ffffff",
    fondo_control="#e7ebf2",
    fondo_control_hover="#dae0ea",
    borde="#ccd4e0",
    texto="#1c2333",
    texto_suave="#5d6880",
    acento="#2f6fed",
    acento_hover="#1d5bd6",
    acento_texto="#ffffff",
    exito="#1e9e58",
    aviso="#c47a06",
    peligro="#cf3339",
    operador="#dbe4f5",
    funcion="#e9edf5",
    grafico_fondo="#ffffff",
    grafico_relleno="#2f6fed",
    grafico_linea="#1d4ea8",
    grafico_rejilla="#ccd4e0",
)

PALETAS = {"oscuro": OSCURO, "claro": CLARO}


def paleta(nombre: str) -> Paleta:
    return PALETAS.get(nombre, OSCURO)


def hoja_de_estilos(p: Paleta) -> str:
    """Genera el QSS completo a partir de una paleta."""
    return f"""
    QWidget {{
        background-color: {p.fondo};
        color: {p.texto};
        font-family: "Segoe UI", "Noto Sans", Arial, sans-serif;
        font-size: 14px;
    }}

    QLabel {{
        background: transparent;
    }}
    QLabel[clase="titulo"] {{
        font-size: 22px;
        font-weight: 600;
        color: {p.texto};
    }}
    QLabel[clase="subtitulo"] {{
        font-size: 13px;
        color: {p.texto_suave};
    }}
    QLabel[clase="seccion"] {{
        font-size: 12px;
        font-weight: 600;
        color: {p.texto_suave};
        text-transform: uppercase;
    }}
    QLabel[clase="resultado"] {{
        font-size: 17px;
        font-weight: 600;
        color: {p.acento};
    }}
    QLabel[clase="error"] {{
        color: {p.peligro};
        font-weight: 600;
    }}
    QLabel[clase="nota"] {{
        color: {p.texto_suave};
        font-size: 12px;
        font-style: italic;
    }}

    /* -------------------------------- Marcos ------------------------------ */
    QFrame[clase="tarjeta"] {{
        background-color: {p.fondo_panel};
        border: 1px solid {p.borde};
        border-radius: 10px;
    }}
    QFrame[clase="separador"] {{
        background-color: {p.borde};
        max-height: 1px;
        border: none;
    }}

    /* ------------------------------- Botones ------------------------------ */
    QPushButton {{
        background-color: {p.fondo_control};
        color: {p.texto};
        border: 1px solid {p.borde};
        border-radius: 8px;
        padding: 8px 14px;
        font-size: 14px;
    }}
    QPushButton:hover {{
        background-color: {p.fondo_control_hover};
    }}
    QPushButton:pressed {{
        background-color: {p.acento};
        color: {p.acento_texto};
    }}
    QPushButton:disabled {{
        color: {p.texto_suave};
        background-color: {p.fondo_panel};
        border-color: {p.borde};
    }}
    QPushButton[clase="primario"] {{
        background-color: {p.acento};
        color: {p.acento_texto};
        border: none;
        font-weight: 600;
    }}
    QPushButton[clase="primario"]:hover {{
        background-color: {p.acento_hover};
    }}
    QPushButton[clase="peligro"] {{
        background-color: transparent;
        color: {p.peligro};
        border: 1px solid {p.peligro};
    }}
    QPushButton[clase="peligro"]:hover {{
        background-color: {p.peligro};
        color: #ffffff;
    }}
    QPushButton[clase="peligro"]:disabled {{
        color: {p.texto_suave};
        border-color: {p.borde};
        background: transparent;
    }}
    QPushButton[clase="tecla"] {{
        font-size: 18px;
        font-weight: 500;
        padding: 0px;
        border-radius: 8px;
    }}
    QPushButton[clase="tecla-operador"] {{
        background-color: {p.operador};
        font-size: 18px;
        font-weight: 600;
        padding: 0px;
        border-radius: 8px;
    }}
    QPushButton[clase="tecla-funcion"] {{
        background-color: {p.funcion};
        color: {p.texto_suave};
        font-size: 13px;
        padding: 0px;
        border-radius: 8px;
    }}
    QPushButton[clase="tecla-funcion"]:hover {{
        color: {p.texto};
    }}
    QPushButton[clase="tecla-igual"] {{
        background-color: {p.acento};
        color: {p.acento_texto};
        font-size: 20px;
        font-weight: 700;
        border: none;
        padding: 0px;
        border-radius: 8px;
    }}
    QPushButton[clase="tecla-igual"]:hover {{
        background-color: {p.acento_hover};
    }}
    QPushButton[clase="tecla-borrar"] {{
        background-color: {p.operador};
        color: {p.aviso};
        font-size: 17px;
        font-weight: 600;
        padding: 0px;
        border-radius: 8px;
    }}
    QPushButton[clase="enlace"] {{
        background: transparent;
        border: none;
        color: {p.acento};
        text-decoration: underline;
        padding: 2px;
    }}

    /* -------------------------- Navegación lateral ------------------------ */
    QListWidget[clase="navegacion"] {{
        background-color: {p.fondo_panel};
        border: none;
        border-right: 1px solid {p.borde};
        outline: none;
        padding: 8px 6px;
        font-size: 14px;
    }}
    QListWidget[clase="navegacion"]::item {{
        padding: 9px 12px;
        border-radius: 8px;
        margin-bottom: 2px;
        color: {p.texto_suave};
    }}
    QListWidget[clase="navegacion"]::item:hover {{
        background-color: {p.fondo_control};
        color: {p.texto};
    }}
    QListWidget[clase="navegacion"]::item:selected {{
        background-color: {p.acento};
        color: {p.acento_texto};
        font-weight: 600;
    }}

    /* ------------------------------- Entradas ----------------------------- */
    QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
        background-color: {p.fondo_control};
        color: {p.texto};
        border: 1px solid {p.borde};
        border-radius: 8px;
        padding: 7px 10px;
        selection-background-color: {p.acento};
        selection-color: {p.acento_texto};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {p.acento};
    }}
    QLineEdit:disabled, QPlainTextEdit:disabled {{
        color: {p.texto_suave};
    }}
    QLineEdit[clase="pantalla"] {{
        background-color: {p.fondo_panel};
        border: 1px solid {p.borde};
        border-radius: 10px;
        font-family: "Consolas", "DejaVu Sans Mono", monospace;
        font-size: 30px;
        font-weight: 500;
        padding: 12px 14px;
    }}
    QLabel[clase="pantalla-previa"] {{
        color: {p.texto_suave};
        font-family: "Consolas", "DejaVu Sans Mono", monospace;
        font-size: 14px;
        padding: 0px 16px;
    }}
    QPlainTextEdit[clase="mono"], QTextEdit[clase="mono"] {{
        font-family: "Consolas", "DejaVu Sans Mono", monospace;
        font-size: 13px;
    }}

    QSpinBox::up-button, QDoubleSpinBox::up-button,
    QSpinBox::down-button, QDoubleSpinBox::down-button {{
        background-color: {p.fondo_control_hover};
        border: none;
        width: 18px;
    }}
    QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid {p.texto_suave};
        width: 0px; height: 0px;
    }}
    QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
        image: none;
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {p.texto_suave};
        width: 0px; height: 0px;
    }}

    /* ----------------------------- Desplegables --------------------------- */
    QComboBox {{
        background-color: {p.fondo_control};
        color: {p.texto};
        border: 1px solid {p.borde};
        border-radius: 8px;
        padding: 7px 10px;
        min-height: 20px;
    }}
    QComboBox:hover {{
        border-color: {p.acento};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QComboBox::down-arrow {{
        image: none;
        border-left: 5px solid transparent;
        border-right: 5px solid transparent;
        border-top: 6px solid {p.texto_suave};
        width: 0px;
        height: 0px;
        margin-right: 8px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {p.fondo_panel};
        color: {p.texto};
        border: 1px solid {p.borde};
        border-radius: 8px;
        selection-background-color: {p.acento};
        selection-color: {p.acento_texto};
        outline: none;
        padding: 4px;
    }}

    /* ------------------------------- Listas ------------------------------- */
    QListWidget, QTableWidget, QTreeWidget {{
        background-color: {p.fondo_panel};
        color: {p.texto};
        border: 1px solid {p.borde};
        border-radius: 8px;
        outline: none;
        alternate-background-color: {p.fondo_control};
    }}
    QListWidget::item {{
        padding: 6px 8px;
        border-radius: 6px;
    }}
    QListWidget::item:hover {{
        background-color: {p.fondo_control};
    }}
    QListWidget::item:selected {{
        background-color: {p.acento};
        color: {p.acento_texto};
    }}
    QHeaderView::section {{
        background-color: {p.fondo_control};
        color: {p.texto_suave};
        border: none;
        border-bottom: 1px solid {p.borde};
        padding: 7px 8px;
        font-weight: 600;
    }}
    QTableWidget {{
        gridline-color: {p.borde};
    }}
    QTableWidget::item {{
        padding: 4px 6px;
    }}
    QTableWidget::item:selected {{
        background-color: {p.acento};
        color: {p.acento_texto};
    }}
    QTableCornerButton::section {{
        background-color: {p.fondo_control};
        border: none;
    }}

    /* ------------------------------ Pestañas ------------------------------ */
    QTabWidget::pane {{
        border: 1px solid {p.borde};
        border-radius: 8px;
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {p.texto_suave};
        padding: 8px 16px;
        margin-right: 2px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
    }}
    QTabBar::tab:hover {{
        color: {p.texto};
    }}
    QTabBar::tab:selected {{
        background-color: {p.fondo_panel};
        color: {p.acento};
        border: 1px solid {p.borde};
        border-bottom-color: {p.fondo_panel};
        font-weight: 600;
    }}

    /* ------------------------- Barras de desplazamiento ------------------- */
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 11px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {p.borde};
        border-radius: 5px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {p.texto_suave};
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 11px;
        margin: 0px;
    }}
    QScrollBar::handle:horizontal {{
        background: {p.borde};
        border-radius: 5px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {p.texto_suave};
    }}
    QScrollBar::add-line, QScrollBar::sub-line {{
        height: 0px;
        width: 0px;
    }}
    QScrollBar::add-page, QScrollBar::sub-page {{
        background: none;
    }}

    /* --------------------------- Otros controles -------------------------- */
    QCheckBox, QRadioButton {{
        spacing: 8px;
        background: transparent;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {p.borde};
        background-color: {p.fondo_control};
    }}
    QCheckBox::indicator {{
        border-radius: 4px;
    }}
    QRadioButton::indicator {{
        border-radius: 9px;
    }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background-color: {p.acento};
        border-color: {p.acento};
    }}
    QGroupBox {{
        border: 1px solid {p.borde};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 10px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0px 6px;
        color: {p.texto_suave};
    }}
    QToolTip {{
        background-color: {p.fondo_panel};
        color: {p.texto};
        border: 1px solid {p.acento};
        border-radius: 6px;
        padding: 6px;
    }}
    QSplitter::handle {{
        background-color: {p.borde};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
    }}
    QMessageBox {{
        background-color: {p.fondo_panel};
    }}
    QStatusBar {{
        background-color: {p.fondo_panel};
        color: {p.texto_suave};
        border-top: 1px solid {p.borde};
    }}
    """
