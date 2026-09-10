"""Formateo de números para mostrar en la interfaz."""

from __future__ import annotations

import math
import sys
import unicodedata

#: Desde Python 3.11 convertir un entero a texto está limitado a 4300 dígitos
#: (protección contra ataques de denegación de servicio al analizar entradas
#: enormes). Esta aplicación muestra factoriales de decenas de miles de dígitos a
#: propósito, así que sube el límite; el tope real lo imponen los módulos que
#: calculan (por ejemplo, MAX_EXACTO en el panel de combinatoria).
_LIMITE_DIGITOS = 250_000
if hasattr(sys, "set_int_max_str_digits"):
    if sys.get_int_max_str_digits() < _LIMITE_DIGITOS:
        sys.set_int_max_str_digits(_LIMITE_DIGITOS)


def normalizar(texto: str) -> str:
    """Pasa a minúsculas y quita los acentos, para comparar y buscar.

    Así «esfer» encuentra también «Casquete esférico», que de otro modo no
    coincidiría por la tilde.
    """
    descompuesto = unicodedata.normalize("NFD", texto.casefold())
    return "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")



def formatear(valor, decimales: int = 6, *, unidad: str = "") -> str:
    """Convierte un número a texto legible.

    * Los enteros exactos se muestran sin decimales (``4`` en vez de ``4.000000``).
    * Se usa notación científica sólo cuando el número es demasiado grande o
      pequeño para leerse de corrido.
    * Se eliminan los ceros finales, así ``0.5`` no aparece como ``0.500000``.
    * No se agrupan los miles: el resultado debe poder copiarse y pegarse dentro
      de otra expresión sin tener que limpiarlo.
    """
    sufijo = f" {unidad}" if unidad else ""

    if isinstance(valor, complex):
        real = formatear(valor.real, decimales)
        imag = formatear(abs(valor.imag), decimales)
        signo = "-" if valor.imag < 0 else "+"
        return f"{real} {signo} {imag}i{sufijo}"

    if isinstance(valor, int) and not isinstance(valor, bool):
        return str(valor) + sufijo

    valor = float(valor)

    if math.isnan(valor):
        return "indefinido"
    if math.isinf(valor):
        return ("-∞" if valor < 0 else "∞") + sufijo
    if valor == 0:
        return "0" + sufijo

    decimales = max(1, min(15, int(decimales)))
    magnitud = abs(valor)

    if magnitud >= 1e15 or magnitud < 1e-9:
        mantisa, exponente = f"{valor:.{decimales}e}".split("e")
        return f"{_limpiar_ceros(mantisa)}e{int(exponente)}{sufijo}"

    if valor.is_integer():
        return str(int(valor)) + sufijo

    texto = f"{valor:.{decimales}g}"
    if "e" in texto.lower():
        mantisa, exponente = texto.lower().split("e")
        return f"{_limpiar_ceros(mantisa)}e{int(exponente)}{sufijo}"
    return _limpiar_ceros(texto) + sufijo


def agrupar_miles(n: int, separador: str = ".") -> str:
    """Agrupa los miles para lectura, p. ej. ``1.234.567``.

    Se usa sólo para textos informativos (nunca para valores reutilizables).
    """
    signo = "-" if n < 0 else ""
    digitos = str(abs(n))
    partes = [digitos[max(i - 3, 0) : i] for i in range(len(digitos), 0, -3)]
    return signo + separador.join(reversed(partes))


def _limpiar_ceros(texto: str) -> str:
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    return texto or "0"


def formatear_entero_grande(n: int, max_digitos: int = 400) -> str:
    """Muestra enteros enormes recortando el centro en lugar de colapsar la vista."""
    texto = str(n)
    if len(texto) <= max_digitos:
        return texto
    mitad = max_digitos // 2
    omitidos = len(texto) - 2 * mitad
    return f"{texto[:mitad]} … ({omitidos} dígitos omitidos) … {texto[-mitad:]}"
