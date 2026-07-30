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
from PyQt5.QtWidgets import QApplication, QMessageBox

from src import __autor__, __nombre__
from src.core.rutas import archivo_datos


def _configurar_registro() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-7s  %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(archivo_datos("axioma.log"), encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


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

    _instalar_gestor_de_errores()

    from src.ui.ventana_principal import VentanaPrincipal

    ventana = VentanaPrincipal()
    ventana.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
