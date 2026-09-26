"""El botón «Paso a paso» y la caja donde se ve el desarrollo.

Lo comparten la calculadora, Geometría y Conversiones. Recuerda si se dejó
encendido en cada apartado, y cuando lo está, cada cálculo nuevo trae su
desarrollo sin tener que volver a pedirlo.
"""

from __future__ import annotations

import html
from typing import Callable

from PyQt5.QtWidgets import QTextBrowser

from ..core.config import config
from .comunes import boton

__all__ = ["PasoAPaso", "pasos_en_html"]


def pasos_en_html(pasos: list, paleta=None) -> str:
    """Los pasos numerados: el título, la explicación y la cuenta."""
    suave = paleta.texto_suave if paleta else "#8b98ac"
    acento = paleta.acento if paleta else "#4a9eff"
    if not pasos:
        return f"<p style='color:{suave}'>Aquí no hay pasos que enseñar.</p>"
    partes = ["<ol style='margin-left:-18px'>"]
    for paso in pasos:
        sangria = 14 * paso.nivel
        partes.append(f"<li style='margin-bottom:6px; margin-left:{sangria}px'>")
        partes.append(f"<b>{html.escape(paso.titulo)}</b>")
        if paso.detalle:
            detalle = html.escape(paso.detalle.replace("**", "^").replace("*", "·"))
            partes.append(f"<br><span style='color:{suave}'>{detalle}</span>")
        if paso.expresion:
            expresion = html.escape(paso.expresion.replace("**", "^").replace("*", "·"))
            partes.append(f"<br><span style='color:{acento}; font-family:Consolas,monospace'>"
                          f"{expresion}</span>")
        partes.append("</li>")
    partes.append("</ol>")
    return "".join(partes)


class PasoAPaso:
    """Un botón que se queda encendido y la caja del desarrollo, por separado.

    Van separados porque cada panel los coloca donde le cabe: el botón junto a
    los demás botones, la caja debajo del resultado.

    `obtener` devuelve la lista de pasos del último cálculo, o ``None`` si no
    hay ninguno.
    """

    def __init__(self, clave: str, obtener: Callable[[], list | None],
                 alto_maximo: int = 260) -> None:
        self.clave = clave
        self._obtener = obtener
        self._paleta = None
        self.boton = boton("Paso a paso", "", self._alternar,
                           tooltip="Ver cómo se llega al resultado, paso a paso")
        self.boton.setCheckable(True)
        self.boton.setChecked(bool((config["paso_a_paso"] or {}).get(clave)))
        self.caja = QTextBrowser()
        self.caja.setOpenLinks(False)
        self.caja.setMaximumHeight(alto_maximo)
        self.caja.setVisible(False)

    @property
    def activo(self) -> bool:
        return self.boton.isChecked()

    def _alternar(self) -> None:
        config["paso_a_paso"] = {**(config["paso_a_paso"] or {}), self.clave: self.activo}
        if self.activo:
            self.refrescar()
        else:
            self.caja.setVisible(False)

    def refrescar(self) -> None:
        """Si está encendido, trae el desarrollo del último cálculo."""
        if not self.activo:
            return
        try:
            pasos = self._obtener()
        except Exception as e:  # noqa: BLE001 (sympy lanza tipos muy variados)
            self.caja.setHtml(f"<p>No se pudo desarrollar: {html.escape(str(e))}</p>")
        else:
            if pasos is None:
                self.caja.setHtml("<p>Calcule algo primero.</p>")
            else:
                self.caja.setHtml(pasos_en_html(pasos, self._paleta))
        self.caja.setVisible(True)

    def aplicar_paleta(self, paleta) -> None:
        self._paleta = paleta
        if self.caja.isVisible():
            self.refrescar()
