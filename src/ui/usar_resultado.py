"""Llevar el resultado de un apartado a los demás.

Con varios apartados abiertos a la vez, lo natural es querer usar en uno lo que
ha salido en otro: el volumen que ha dado Geometría, dentro de una ecuación; la
raíz que ha dado Ecuaciones, en la calculadora. Copiar el número a mano invita a
equivocarse en un dígito, y redondea sin querer.

Aquí se guarda ese resultado como **variable compartida**, con su valor completo,
y a partir de ese momento vale en cualquier campo de cualquier apartado.
"""

from __future__ import annotations

import re
import unicodedata

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QInputDialog, QMessageBox, QWidget

from ..core import variables

#: Un número al principio del texto: «392.699 cm³» → 392.699. Se admite el signo,
#: la notación científica y la coma decimal.
_NUMERO = re.compile(r"[-+]?\d+(?:[.,]\d+)?(?:[eE][-+]?\d+)?")


class _Senales(QObject):
    """Avisos que cruzan la aplicación sin encadenar reenvíos panel a panel."""

    #: Alguien ha definido o borrado una variable.
    variables_cambiadas = pyqtSignal()


senales = _Senales()


def numero_de(texto: str) -> float | None:
    """Extrae el valor de un resultado ya formateado, o ``None`` si no lo hay."""
    if not texto:
        return None
    encontrado = _NUMERO.search(texto.replace("−", "-"))
    if encontrado is None:
        return None
    try:
        return float(encontrado.group().replace(",", "."))
    except ValueError:
        return None


def nombre_sugerido(etiqueta: str) -> str:
    """«Área lateral» → ``area_lateral``, que sí se puede escribir en un campo."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", etiqueta)
        if unicodedata.category(c) != "Mn"
    )
    limpio = re.sub(r"[^0-9A-Za-z]+", "_", sin_tildes).strip("_").lower()
    if not limpio or limpio[0].isdigit():
        limpio = f"r_{limpio}" if limpio else "resultado"
    return limpio


def permitir_usar_valores(editor, etiqueta: str = "resultado") -> None:
    """Añade «Usar como variable» al menú contextual de una salida de texto.

    Las salidas en texto (ecuaciones, matrices, pasos…) no son tablas, así que
    lo que se guarda es el número que el usuario haya seleccionado.
    """
    from PyQt5.QtCore import Qt as _Qt

    def menu(punto) -> None:
        propio = editor.createStandardContextMenu()
        seleccion = editor.textCursor().selectedText()
        numero = numero_de(seleccion)
        propio.addSeparator()
        accion = propio.addAction("Usar el número seleccionado como variable…")
        accion.setEnabled(numero is not None)
        if numero is None:
            accion.setToolTip("Seleccione antes un número de la salida")
        elegida = propio.exec_(editor.viewport().mapToGlobal(punto))
        if elegida is accion and numero is not None:
            guardar_como_variable(editor, etiqueta, numero)

    editor.setContextMenuPolicy(_Qt.CustomContextMenu)
    editor.customContextMenuRequested.connect(menu)


def guardar_como_variable(padre: QWidget, etiqueta: str, valor) -> str | None:
    """Pide un nombre y guarda el valor. Devuelve el nombre, o ``None``.

    Se guarda el número **completo**, no el que se ve: el resultado mostrado va
    redondeado a los decimales configurados, y arrastrar ese redondeo a los
    cálculos siguientes es justo lo que se quiere evitar.
    """
    numero = valor if isinstance(valor, (int, float)) else numero_de(str(valor))
    if numero is None:
        QMessageBox.information(
            padre, "Usar el resultado",
            "Ahí no hay un número que guardar. Seleccione un valor numérico.",
        )
        return None

    sugerencia = nombre_sugerido(etiqueta)
    while True:
        nombre, aceptado = QInputDialog.getText(
            padre, "Usar el resultado en otros apartados",
            f"Guardar {numero:g} como variable.\n"
            f"Podrá escribir ese nombre en cualquier campo de cualquier apartado.",
            text=sugerencia,
        )
        if not aceptado:
            return None
        nombre = nombre.strip()
        try:
            variables.definir(nombre, float(numero))
        except variables.ErrorVariable as e:
            QMessageBox.warning(padre, "Nombre no válido", str(e))
            sugerencia = nombre
            continue
        senales.variables_cambiadas.emit()
        return nombre
