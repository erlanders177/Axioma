"""Punto de entrada de Axioma.

Ejecutar con:  python main.py
"""

from __future__ import annotations

import logging
import sys
import traceback
from pathlib import Path

# Permite ejecutar el archivo directamente y también desde el ejecutable
# empaquetado, donde el directorio de trabajo puede ser cualquiera.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QMessageBox

from src import __autor__, __nombre__
from src.core.rutas import archivo_datos, icono


def _configurar_registro() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(archivo_datos("axioma.log"), encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def _agrupar_en_barra_de_tareas() -> None:
    """Hace que Windows use el icono de la aplicación en la barra de tareas.

    Sin declarar un identificador propio, Windows agrupa la ventana bajo el
    proceso que la lanza (``python.exe``) y muestra el icono de Python en lugar
    del nuestro. Sólo aplica a Windows; en el resto de sistemas no hace nada.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"Erlanders.{__nombre__}.{__nombre__}"
        )
    except (AttributeError, OSError):  # pragma: no cover - depende del sistema
        pass


def _instalar_gestor_de_errores() -> None:
    """Muestra un diálogo en vez de cerrarse en silencio ante un error no previsto."""
    def gestor(tipo, valor, rastro):
        if issubclass(tipo, KeyboardInterrupt):
            sys.__excepthook__(tipo, valor, rastro)
            return
        detalle = "".join(traceback.format_exception(tipo, valor, rastro))
        logging.getLogger("axioma").critical("Error no controlado:\n%s", detalle)

        cuadro = QMessageBox()
        cuadro.setIcon(QMessageBox.Critical)
        cuadro.setWindowTitle("Error inesperado")
        cuadro.setText(
            "Se ha producido un error inesperado.\n"
            "La aplicación intentará seguir funcionando."
        )
        cuadro.setInformativeText(f"{tipo.__name__}: {valor}")
        cuadro.setDetailedText(detalle)
        cuadro.exec_()

    sys.excepthook = gestor


def main() -> int:
    _configurar_registro()

    # Escalado correcto en pantallas de alta densidad; debe hacerse antes de crear
    # la QApplication.
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName(__nombre__)
    app.setOrganizationName(__autor__)

    ruta_icono = icono()
    if ruta_icono is not None:
        app.setWindowIcon(QIcon(str(ruta_icono)))
    _agrupar_en_barra_de_tareas()

    _instalar_gestor_de_errores()

    from src.ui.ventana_principal import VentanaPrincipal

    ventana = VentanaPrincipal()
    ventana.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
