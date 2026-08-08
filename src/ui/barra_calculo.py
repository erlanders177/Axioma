"""Barra de cálculo, presente en todos los módulos.

Resuelve la fricción de tener que salir del módulo en el que se está trabajando
para hacer una cuenta suelta. Si está resolviendo una ecuación trigonométrica y
necesita saber cuánto vale ``5*sin(30)``, lo escribe aquí sin moverse.

Dos decisiones de diseño importantes:

* **Lo que se calcula aquí va al historial del módulo activo**, no al de la
  calculadora. Si está trabajando en una figura geométrica, esa cuenta pertenece
  a ese problema, no a un cajón común.
* **Las variables son compartidas.** Al escribir ``h = 5*sin(30)`` puede usar
  ``h`` en los campos del módulo, que es lo que evita tener que copiar números a
  mano de un sitio a otro.
"""

from __future__ import annotations

from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLineEdit, QVBoxLayout, QWidget

from ..core import magnitudes, variables
from ..core.config import config
from ..core.evaluador import ErrorExpresion, evaluar, parentesis_pendientes
from ..core.formato import formatear
from .comunes import boton, etiqueta

#: Cuántas expresiones recuerda para las flechas ↑/↓.
MAX_RECORDADAS = 100


class BarraCalculo(QFrame):
    """Línea de cálculo rápida, compartida por todos los módulos."""

    #: (operación, datos) — la ventana la guarda en el historial del módulo activo.
    calculado = pyqtSignal(str, dict)
    #: Se emite cuando cambian las variables, para que los paneles se refresquen.
    variables_cambiadas = pyqtSignal()

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.setProperty("clase", "tarjeta")
        self.ultimo_resultado = 0.0
        self._recordadas: list[str] = []
        self._posicion = 0
        self._borrador = ""
        self._construir()

    def _construir(self) -> None:
        columna = QVBoxLayout(self)
        columna.setContentsMargins(12, 8, 12, 8)
        columna.setSpacing(4)

        fila = QHBoxLayout()
        fila.setSpacing(8)

        indicador = etiqueta("ƒ")
        indicador.setStyleSheet("font-size: 16px; font-weight: 600;")
        indicador.setFixedWidth(14)
        fila.addWidget(indicador)

        self.entrada = QLineEdit()
        self.entrada.setPlaceholderText(
            "Cuenta rápida sin salir del módulo:  5*sin(30)   ·   h = 2*pi*r   "
            "·   3 km + 200 m"
        )
        self.entrada.setToolTip(
            "Mismas funciones que la calculadora, y también unidades.\n"
            "Escriba «nombre = expresión» para guardar una variable y usarla "
            "en los campos del módulo.\n"
            "↑ y ↓ recorren lo ya calculado."
        )
        self.entrada.returnPressed.connect(self.calcular)
        self.entrada.textChanged.connect(self._vista_previa)
        self.entrada.installEventFilter(self)
        fila.addWidget(self.entrada, 1)

        self.resultado = etiqueta("", "resultado")
        self.resultado.setMinimumWidth(150)
        self.resultado.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.resultado.setTextInteractionFlags(Qt.TextSelectableByMouse)
        fila.addWidget(self.resultado)

        fila.addWidget(boton("Borrar variables", "", self._borrar_variables,
                             tooltip="Olvidar todas las variables definidas"))
        columna.addLayout(fila)

        self.etiqueta_variables = etiqueta("", "nota", ajustar=True)
        self.etiqueta_variables.setVisible(False)
        columna.addWidget(self.etiqueta_variables)

    # ------------------------------------------------------------- historial -- #

    def eventFilter(self, objeto, evento):  # noqa: N802 (nombre impuesto por Qt)
        if objeto is self.entrada and evento.type() == QEvent.KeyPress:
            if evento.key() == Qt.Key_Up:
                self._recorrer(-1)
                return True
            if evento.key() == Qt.Key_Down:
                self._recorrer(1)
                return True
        return super().eventFilter(objeto, evento)

    def _recorrer(self, salto: int) -> None:
        if not self._recordadas:
            return
        if self._posicion == len(self._recordadas):
            self._borrador = self.entrada.text()

        destino = max(0, min(len(self._recordadas), self._posicion + salto))
        if destino == self._posicion:
            return
        self._posicion = destino
        texto = (self._borrador if destino == len(self._recordadas)
                 else self._recordadas[destino])
        self.entrada.setText(texto)
        self.entrada.setCursorPosition(len(texto))

    # --------------------------------------------------------------- cálculo -- #

    def _entorno(self) -> dict:
        entorno = {"ans": self.ultimo_resultado}
        entorno.update(variables.valores())
        return entorno

    @staticmethod
    def _asignacion(expresion: str) -> tuple[str, str] | None:
        """Detecta «nombre = expresión», sin confundirla con ==, <= o >=."""
        if expresion.count("=") != 1:
            return None
        izquierda, _, derecha = expresion.partition("=")
        if derecha.startswith("=") or izquierda.rstrip()[-1:] in "<>!":
            return None
        nombre = izquierda.strip()
        if not nombre.isidentifier() or not derecha.strip():
            return None
        return nombre, derecha.strip()

    def _vista_previa(self) -> None:
        texto = self.entrada.text().strip()
        if not texto:
            self.resultado.clear()
            return

        asignacion = self._asignacion(texto)
        cuerpo = asignacion[1] if asignacion else texto
        tentativa = cuerpo + ")" * parentesis_pendientes(cuerpo)

        valor = self._evaluar_silencioso(tentativa)
        if valor is None:
            self.resultado.clear()
            return
        prefijo = f"{asignacion[0]} = " if asignacion else "= "
        self.resultado.setText(prefijo + valor)

    def _evaluar_silencioso(self, expresion: str) -> str | None:
        """Texto del resultado, o ``None`` si aún no es evaluable."""
        decimales = config["decimales"]
        if magnitudes.contiene_unidades(expresion):
            try:
                return magnitudes.evaluar(expresion).texto(decimales)
            except magnitudes.ErrorMagnitud:
                return None
        try:
            return formatear(evaluar(expresion, config["modo_angulo"], self._entorno()),
                             decimales)
        except ErrorExpresion:
            return None

    def calcular(self) -> None:
        expresion = self.entrada.text().strip()
        if not expresion:
            return

        asignacion = self._asignacion(expresion)
        cuerpo = asignacion[1] if asignacion else expresion
        decimales = config["decimales"]

        # Las expresiones con unidades las resuelve el motor de magnitudes.
        if magnitudes.contiene_unidades(cuerpo):
            try:
                cantidad = magnitudes.evaluar(cuerpo)
            except magnitudes.ErrorMagnitud as e:
                self._error(str(e))
                return

            # Una variable guarda un número, no una magnitud. Permitir
            # «alto = 50 mm» haría que al usar «alto» en un campo en centímetros
            # valiera 50 cm sin avisar: un resultado erróneo en silencio.
            if asignacion and cantidad.unidad is not None:
                self._error(
                    f"Las variables guardan números sin unidad. Convierta antes: "
                    f"«{asignacion[0]} = {cuerpo} a {cantidad.unidad.simbolo}» y "
                    f"use ese número."
                )
                return

            valor, texto_resultado = cantidad.valor, cantidad.texto(decimales)
        else:
            try:
                valor = evaluar(cuerpo, config["modo_angulo"], self._entorno())
            except ErrorExpresion as e:
                self._error(str(e))
                return
            texto_resultado = formatear(valor, decimales)

        if asignacion:
            try:
                variables.definir(asignacion[0], valor)
            except variables.ErrorVariable as e:
                self._error(str(e))
                return
            self._refrescar_variables()
            self.variables_cambiadas.emit()
            operacion = f"{asignacion[0]} = {cuerpo} = {texto_resultado}"
            resumen = f"{asignacion[0]} = {texto_resultado}"
        else:
            operacion = f"{expresion} = {texto_resultado}"
            resumen = f"= {texto_resultado}"

        self.ultimo_resultado = valor
        self._recordar(expresion)

        # Vaciar el campo dispara la vista previa, que borraría el resultado:
        # por eso se escribe después, no antes.
        self.entrada.clear()
        self.resultado.setText(resumen)
        self.entrada.setFocus()

        # El cálculo pertenece al módulo en el que se está trabajando.
        self.calculado.emit(operacion, {
            "expresion": expresion,
            "resultado": texto_resultado,
            "origen": "barra",
        })

    def _error(self, mensaje: str) -> None:
        self.resultado.setProperty("clase", "error")
        self.resultado.style().unpolish(self.resultado)
        self.resultado.style().polish(self.resultado)
        self.resultado.setText(mensaje[:60])
        self.resultado.setToolTip(mensaje)

    def _recordar(self, expresion: str) -> None:
        if not self._recordadas or self._recordadas[-1] != expresion:
            self._recordadas.append(expresion)
            del self._recordadas[:-MAX_RECORDADAS]
        self._posicion = len(self._recordadas)
        self._borrador = ""
        self.resultado.setProperty("clase", "resultado")
        self.resultado.style().unpolish(self.resultado)
        self.resultado.style().polish(self.resultado)

    # -------------------------------------------------------------- variables -- #

    def _refrescar_variables(self) -> None:
        texto = variables.resumen(config["decimales"])
        self.etiqueta_variables.setText(f"Variables:   {texto}" if texto else "")
        self.etiqueta_variables.setVisible(bool(texto))

    def _borrar_variables(self) -> None:
        variables.borrar_todas()
        self._refrescar_variables()
        self.variables_cambiadas.emit()
        self.entrada.setFocus()

    def enfocar(self) -> None:
        """Lleva el cursor a la barra (atajo de teclado de la ventana)."""
        self.entrada.setFocus()
        self.entrada.selectAll()
