"""Factorial y combinatoria.

El módulo original sólo calculaba factoriales, con un tope arbitrario de 1000 y
volcando el número entero en un ``QLabel``, lo que estiraba la ventana sin límite
cuando el resultado tenía miles de dígitos. Aquí:

* el tope es mucho más alto y el resultado se muestra en un cuadro con
  desplazamiento, recortando el centro de los números enormes;
* se añaden combinaciones, permutaciones, variaciones, números de Catalan,
  coeficientes multinomiales, la función gamma para valores no enteros y la
  aproximación de Stirling.
"""

from __future__ import annotations

import math

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QComboBox, QFormLayout, QHBoxLayout, QPlainTextEdit, QSplitter,
    QVBoxLayout, QWidget,
)

from ..core.formato import formatear, formatear_entero_grande
from .comunes import (
    PanelModulo,
    CampoNumerico, aviso, boton, etiqueta, separador, tarjeta,
)

#: Por encima de este valor no se calcula el factorial exacto (tardaría demasiado
#: y el resultado tendría cientos de miles de dígitos).
MAX_EXACTO = 20_000
MAX_ENTRADA = 1_000_000


class ErrorCombinatoria(ValueError):
    """Los datos no son válidos para esta operación."""


class PanelCombinatoria(PanelModulo):
    MODULO = "combinatoria"
    TITULO_HISTORIAL = "Historial de cálculos"

    #: (clave, título, etiquetas de los parámetros necesarios)
    OPERACIONES = [
        ("factorial", "Factorial  n!", ["n"]),
        ("combinaciones", "Combinaciones  C(n, r)", ["n", "r"]),
        ("permutaciones", "Permutaciones (variaciones)  P(n, r)", ["n", "r"]),
        ("variaciones_rep", "Variaciones con repetición  nʳ", ["n", "r"]),
        ("combinaciones_rep", "Combinaciones con repetición  C(n+r−1, r)", ["n", "r"]),
        ("permutaciones_total", "Permutaciones de n elementos  n!", ["n"]),
        ("doble_factorial", "Doble factorial  n!!", ["n"]),
        ("subfactorial", "Subfactorial (desórdenes)  ¡n", ["n"]),
        ("catalan", "Número de Catalan  Cₙ", ["n"]),
        ("gamma", "Función gamma  Γ(x)", ["x"]),
        ("stirling", "Aproximación de Stirling de n!", ["n"]),
    ]

    def __init__(self, padre: QWidget | None = None) -> None:
        super().__init__(padre)
        self.campos: dict[str, CampoNumerico] = {}
        self._construir()
        self._cambiar_operacion(0)

    # ------------------------------------------------------------------ UI -- #

    def _construir(self) -> None:
        raiz = QHBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)

        division = QSplitter(Qt.Horizontal)
        division.addWidget(self._crear_columna())


        division.setStretchFactor(0, 3)
        division.setSizes([680])
        raiz.addWidget(division)

    def _crear_columna(self) -> QWidget:
        contenedor = QWidget()
        columna = QVBoxLayout(contenedor)
        columna.setContentsMargins(0, 0, 8, 0)
        columna.setSpacing(10)

        marco, col = tarjeta()
        col.addWidget(etiqueta("Operación", "seccion"))
        self.combo = QComboBox()
        self.combo.addItems([titulo for _, titulo, _ in self.OPERACIONES])
        self.combo.currentIndexChanged.connect(self._cambiar_operacion)
        col.addWidget(self.combo)

        col.addWidget(separador())
        col.addWidget(etiqueta("Datos", "seccion"))
        self.formulario = QFormLayout()
        self.formulario.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.formulario.setHorizontalSpacing(10)
        self.formulario.setVerticalSpacing(7)
        col.addLayout(self.formulario)

        self.explicacion = etiqueta("", "nota", ajustar=True)
        col.addWidget(self.explicacion)

        acciones = QHBoxLayout()
        acciones.addWidget(boton("Calcular", "primario", self.calcular))
        acciones.addWidget(boton("Copiar", "", self._copiar))
        acciones.addStretch()
        col.addLayout(acciones)
        columna.addWidget(marco)

        marco_salida, col_salida = tarjeta()
        col_salida.addWidget(etiqueta("Resultado", "seccion"))
        self.salida = QPlainTextEdit()
        self.salida.setProperty("clase", "mono")
        self.salida.setReadOnly(True)
        self.salida.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        self.salida.setPlaceholderText("Introduzca los datos y pulse «Calcular».")
        col_salida.addWidget(self.salida, 1)
        columna.addWidget(marco_salida, 1)

        return contenedor

    def _cambiar_operacion(self, indice: int) -> None:
        clave, _, parametros = self.OPERACIONES[indice]

        while self.formulario.count():
            elemento = self.formulario.takeAt(0)
            widget = elemento.widget()
            if widget is not None:
                # setParent(None) lo quita de la pantalla ya; deleteLater solo
                # actúa al volver al bucle de eventos, y hasta entonces el widget
                # se sigue dibujando encima del que ocupa ahora su sitio.
                widget.setParent(None)
                widget.deleteLater()
        self.campos.clear()

        for nombre in parametros:
            campo = CampoNumerico("entero ≥ 0" if nombre != "x" else "número real")
            campo.aceptado.connect(self.calcular)
            self.campos[nombre] = campo
            self.formulario.addRow(f"{nombre} =", campo)

        self.explicacion.setText(_EXPLICACIONES.get(clave, ""))
        self.salida.clear()

    # -------------------------------------------------------------- cálculo -- #

    def _leer(self, nombre: str, *, entero: bool = True) -> float:
        campo = self.campos[nombre]
        try:
            valor = campo.valor()
        except ValueError as e:
            raise ErrorCombinatoria(str(e)) from None
        if valor is None:
            raise ErrorCombinatoria(f"Falta el valor de «{nombre}»")

        if entero:
            if abs(valor - round(valor)) > 1e-9:
                raise ErrorCombinatoria(f"«{nombre}» debe ser un número entero")
            valor = int(round(valor))
            if valor < 0:
                raise ErrorCombinatoria(f"«{nombre}» no puede ser negativo")
            if valor > MAX_ENTRADA:
                raise ErrorCombinatoria(
                    f"«{nombre}» es demasiado grande (máximo {MAX_ENTRADA:,})".replace(",", ".")
                )
        return valor

    def calcular(self) -> None:
        clave, titulo, _ = self.OPERACIONES[self.combo.currentIndex()]
        try:
            texto, operacion = getattr(self, f"_op_{clave}")()
        except ErrorCombinatoria as e:
            self.salida.setPlainText(str(e))
            aviso(self, str(e), "Datos incorrectos")
            return
        except (OverflowError, ValueError) as e:
            mensaje = f"No se pudo calcular: {e}"
            self.salida.setPlainText(mensaje)
            aviso(self, mensaje, "Error")
            return

        self.salida.setPlainText(texto)
        datos = {"operacion": clave,
                 "valores": {n: c.text() for n, c in self.campos.items()}}
        self.guardar_en_historial(operacion, datos)

    # -- operaciones ------------------------------------------------------- #

    def _op_factorial(self) -> tuple[str, str]:
        n = int(self._leer("n"))
        if n > MAX_EXACTO:
            digitos, aproximado = _estimar_factorial(n)
            texto = (
                f"{n}! es demasiado grande para calcularlo de forma exacta "
                f"(máximo {MAX_EXACTO:,}).\n\n"
                f"Estimación:\n"
                f"  dígitos    ≈ {digitos:,}\n"
                f"  valor      ≈ {aproximado}\n"
            ).replace(",", ".")
            return texto, f"{n}! ≈ {aproximado} ({digitos} dígitos)"

        resultado = math.factorial(n)
        digitos = len(str(resultado))
        texto = (
            f"{n}! = {formatear_entero_grande(resultado)}\n\n"
            f"Número de dígitos: {digitos}\n"
            f"Aproximación:      {_notacion_cientifica(resultado)}"
        )
        resumen = (f"{n}! = {resultado}" if digitos <= 40
                   else f"{n}! = {_notacion_cientifica(resultado)} ({digitos} dígitos)")
        return texto, resumen

    def _op_permutaciones_total(self) -> tuple[str, str]:
        return self._op_factorial()

    def _op_combinaciones(self) -> tuple[str, str]:
        n, r = int(self._leer("n")), int(self._leer("r"))
        if r > n:
            raise ErrorCombinatoria("r no puede ser mayor que n en las combinaciones")
        resultado = math.comb(n, r)
        texto = (
            f"C({n}, {r}) = {formatear_entero_grande(resultado)}\n\n"
            f"Formas de elegir {r} elementos de {n} sin importar el orden.\n"
            f"C({n}, {r}) = {n}! / ({r}! · {n - r}!)\n"
            f"Propiedad:  C({n}, {r}) = C({n}, {n - r}) = {math.comb(n, n - r)}"
        )
        return texto, f"C({n}, {r}) = {resultado}"

    def _op_permutaciones(self) -> tuple[str, str]:
        n, r = int(self._leer("n")), int(self._leer("r"))
        if r > n:
            raise ErrorCombinatoria("r no puede ser mayor que n en las permutaciones")
        resultado = math.perm(n, r)
        texto = (
            f"P({n}, {r}) = {formatear_entero_grande(resultado)}\n\n"
            f"Formas de elegir y ordenar {r} elementos de {n}.\n"
            f"P({n}, {r}) = {n}! / {n - r}!  =  C({n}, {r}) · {r}!"
        )
        return texto, f"P({n}, {r}) = {resultado}"

    def _op_variaciones_rep(self) -> tuple[str, str]:
        n, r = int(self._leer("n")), int(self._leer("r"))
        if n == 0 and r == 0:
            resultado = 1
        elif r * math.log10(max(n, 1)) > 100_000:
            raise ErrorCombinatoria("El resultado tendría más de 100 000 dígitos")
        else:
            resultado = n ** r
        texto = (
            f"{n}^{r} = {formatear_entero_grande(resultado)}\n\n"
            f"Secuencias de longitud {r} usando {n} símbolos, con repetición."
        )
        return texto, f"{n}^{r} = {_recortar(resultado)}"

    def _op_combinaciones_rep(self) -> tuple[str, str]:
        n, r = int(self._leer("n")), int(self._leer("r"))
        if n == 0 and r > 0:
            raise ErrorCombinatoria("Con n = 0 no se puede elegir ningún elemento")
        resultado = math.comb(n + r - 1, r)
        texto = (
            f"C({n} + {r} − 1, {r}) = {formatear_entero_grande(resultado)}\n\n"
            f"Formas de elegir {r} elementos de {n} tipos, con repetición y sin "
            f"importar el orden."
        )
        return texto, f"CR({n}, {r}) = {resultado}"

    def _op_doble_factorial(self) -> tuple[str, str]:
        n = int(self._leer("n"))
        if n > MAX_EXACTO:
            raise ErrorCombinatoria(f"n demasiado grande (máximo {MAX_EXACTO})")
        resultado = 1
        for k in range(n, 0, -2):
            resultado *= k
        paridad = "impares" if n % 2 else "pares"
        texto = (
            f"{n}!! = {formatear_entero_grande(resultado)}\n\n"
            f"Producto de los números {paridad} desde {n} hasta "
            f"{1 if n % 2 else 2}.\n"
            f"Número de dígitos: {len(str(resultado))}"
        )
        return texto, f"{n}!! = {_recortar(resultado)}"

    def _op_subfactorial(self) -> tuple[str, str]:
        n = int(self._leer("n"))
        if n > 5000:
            raise ErrorCombinatoria("n demasiado grande para el subfactorial (máximo 5000)")
        # Recurrencia !n = (n-1)·(!(n-1) + !(n-2)), exacta con enteros.
        anterior, actual = 1, 0  # !0 = 1, !1 = 0
        if n == 0:
            resultado = 1
        elif n == 1:
            resultado = 0
        else:
            for k in range(2, n + 1):
                anterior, actual = actual, (k - 1) * (actual + anterior)
            resultado = actual
        # La proporción tiende a 1/e. No se calcula como `resultado / n!` porque
        # para n grande la división de enteros desborda al pasar a coma flotante.
        if n == 0:
            proporcion = "1"
        else:
            log_proporcion = _log10_entero(resultado) - math.lgamma(n + 1) / math.log(10)
            proporcion = formatear(10 ** log_proporcion, 8)

        texto = (
            f"¡{n} = {formatear_entero_grande(resultado)}\n\n"
            f"Permutaciones de {n} elementos en las que ninguno queda en su "
            f"posición original (desórdenes).\n"
            f"Proporción sobre el total:  ¡{n} / {n}! ≈ {proporcion}"
            f"      (tiende a 1/e ≈ 0,3678794412)"
        )
        return texto, f"¡{n} = {_recortar(resultado)}"

    def _op_catalan(self) -> tuple[str, str]:
        n = int(self._leer("n"))
        if n > 5000:
            raise ErrorCombinatoria("n demasiado grande (máximo 5000)")
        resultado = math.comb(2 * n, n) // (n + 1)
        texto = (
            f"C₍{n}₎ = {formatear_entero_grande(resultado)}\n\n"
            f"Cₙ = C(2n, n) / (n + 1)\n"
            f"Cuenta, entre otras cosas, las formas de emparejar {n} pares de "
            f"paréntesis correctamente y las triangulaciones de un polígono de "
            f"{n + 2} lados."
        )
        return texto, f"Catalan({n}) = {_recortar(resultado)}"

    def _op_gamma(self) -> tuple[str, str]:
        x = self._leer("x", entero=False)
        if x <= 0 and float(x).is_integer():
            raise ErrorCombinatoria(
                "La función gamma no está definida en 0 ni en los enteros negativos"
            )
        try:
            resultado = math.gamma(x)
        except (ValueError, OverflowError) as e:
            raise ErrorCombinatoria(f"No se pudo calcular Γ({x}): {e}") from None
        texto = (
            f"Γ({formatear(x, 10)}) = {formatear(resultado, 12)}\n\n"
            f"Para enteros positivos, Γ(n) = (n − 1)!\n"
            f"Equivale al «factorial» de {formatear(x - 1, 10)}."
        )
        return texto, f"Γ({formatear(x, 6)}) = {formatear(resultado, 8)}"

    def _op_stirling(self) -> tuple[str, str]:
        n = int(self._leer("n"))
        if n == 0:
            raise ErrorCombinatoria("La aproximación de Stirling requiere n ≥ 1")

        log10_exacto = math.lgamma(n + 1) / math.log(10)
        log10_stirling = (
            0.5 * math.log10(2 * math.pi * n) + n * math.log10(n) - n / math.log(10)
        )
        digitos = int(log10_exacto) + 1

        lineas = [
            f"n = {n}",
            "",
            "Stirling:   n! ≈ √(2πn) · (n/e)^n",
            f"            ≈ {_desde_log10(log10_stirling)}",
            "Valor real (vía lgamma):",
            f"            ≈ {_desde_log10(log10_exacto)}",
            f"Dígitos:    {digitos:,}".replace(",", "."),
            "",
            f"Error relativo ≈ {formatear(10 ** (log10_stirling - log10_exacto) - 1, 6)}"
            f"   (tiende a 1/(12n) = {formatear(1 / (12 * n), 6)})",
        ]
        if n <= MAX_EXACTO:
            exacto = math.factorial(n)
            lineas.append("")
            lineas.append(f"Valor exacto: {formatear_entero_grande(exacto, 200)}")
        return "\n".join(lineas), f"Stirling({n}) ≈ {_desde_log10(log10_stirling)}"

    # ---------------------------------------------------------------- varios -- #

    def _copiar(self) -> None:
        from PyQt5.QtWidgets import QApplication
        portapapeles = QApplication.clipboard()
        if portapapeles is not None:
            portapapeles.setText(self.salida.toPlainText())

    def restaurar_datos(self, datos: dict) -> None:
        clave = datos.get("operacion")
        claves = [c for c, _, _ in self.OPERACIONES]
        if clave in claves:
            self.combo.setCurrentIndex(claves.index(clave))
        for nombre, valor in (datos.get("valores") or {}).items():
            campo = self.campos.get(nombre)
            if campo is not None:
                campo.setText(str(valor))
        self.calcular()

    def aplicar_paleta(self, paleta) -> None:
        return


# --------------------------------------------------------------------------- #
# Auxiliares
# --------------------------------------------------------------------------- #

_EXPLICACIONES = {
    "factorial": "n! = 1 · 2 · 3 · … · n. Por convenio, 0! = 1.",
    "combinaciones": "Cuántos subconjuntos de r elementos hay en un conjunto de n. "
                     "El orden no importa.",
    "permutaciones": "Cuántas secuencias ordenadas de r elementos se pueden formar "
                     "con n elementos distintos, sin repetir.",
    "variaciones_rep": "Secuencias de longitud r con n símbolos disponibles, "
                       "pudiendo repetir (por ejemplo, contraseñas).",
    "combinaciones_rep": "Elegir r elementos entre n tipos, permitiendo repetir y "
                         "sin importar el orden.",
    "permutaciones_total": "Todas las ordenaciones posibles de n elementos distintos.",
    "doble_factorial": "n!! multiplica n · (n−2) · (n−4) · … hasta llegar a 1 o a 2.",
    "subfactorial": "¡n cuenta las permutaciones sin ningún elemento en su sitio.",
    "catalan": "Sucesión de Catalan: 1, 1, 2, 5, 14, 42, 132…",
    "gamma": "Extiende el factorial a los números reales: Γ(n) = (n−1)!",
    "stirling": "Compara n! con su aproximación asintótica √(2πn)·(n/e)ⁿ.",
}


def _notacion_cientifica(n: int, cifras: int = 8) -> str:
    """Notación científica de un entero grande, sin convertirlo a float."""
    texto = str(abs(n))
    exponente = len(texto) - 1
    mantisa = texto[0] + "." + texto[1:cifras + 1].ljust(cifras, "0")
    signo = "-" if n < 0 else ""
    return f"{signo}{mantisa}e{exponente}" if exponente else f"{signo}{texto}"


def _log10_entero(n: int) -> float:
    """Logaritmo decimal de un entero arbitrariamente grande, sin desbordar."""
    if n <= 0:
        return -math.inf
    digitos = len(str(n))
    if digitos <= 15:
        return math.log10(n)
    # Se usan sólo las primeras cifras significativas.
    cabeza = int(str(n)[:15])
    return math.log10(cabeza) + (digitos - 15)


def _recortar(n: int, limite: int = 40) -> str:
    """Versión corta de un entero para la línea del historial."""
    texto = str(n)
    return texto if len(texto) <= limite else f"{_notacion_cientifica(n)} ({len(texto)} dígitos)"


def _desde_log10(log10_valor: float) -> str:
    """Reconstruye la notación científica a partir del logaritmo decimal."""
    exponente = math.floor(log10_valor)
    mantisa = 10 ** (log10_valor - exponente)
    return f"{mantisa:.6f}e{exponente}"


def _estimar_factorial(n: int) -> tuple[int, str]:
    """Número de dígitos y valor aproximado de n! sin calcularlo."""
    log10_valor = math.lgamma(n + 1) / math.log(10)
    return int(log10_valor) + 1, _desde_log10(log10_valor)
