"""Pruebas de las funciones añadidas después de la versión 3.0.

Cubre la aritmética con unidades, el cálculo geométrico inverso y la
resolución paso a paso.
"""

from __future__ import annotations

import math
import os
import sys
import tempfile

os.environ.setdefault("APPDATA", tempfile.mkdtemp(prefix="axioma_extras_"))
os.environ.setdefault("XDG_DATA_HOME", os.environ["APPDATA"])
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
import sympy as sp  # noqa: E402

from src.core import figuras, magnitudes, pasos, simbolico  # noqa: E402


# --------------------------------------------------------------------------- #
# Aritmética con unidades
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("expresion,esperado", [
    ("5 km + 300 m", "5.3 km"),
    ("5km+300m", "5.3 km"),
    ("1 h + 30 min", "1.5 h"),
    ("100 kg - 500 g", "99.5 kg"),
    ("10 km / 2", "5 km"),
    ("5 km * 3", "15 km"),
    ("10 km / 2 km", "5"),
    ("(2 km + 500 m) * 2", "5 km"),
    ("-5 km + 10 km", "5 km"),
    ("3 + 4", "7"),
])
def test_unidades_calcula(expresion, esperado):
    assert magnitudes.evaluar(expresion).texto() == esperado


@pytest.mark.parametrize("expresion,esperado", [
    ("20 °C a °F", "68 °F"),
    ("100 °C a K", "373.15 K"),
    ("1 mi a km", "1.60934 km"),
    ("2 GB a MB", "2000 MB"),
    ("1 kWh a J", "3600000 J"),
    ("5 km en m", "5000 m"),
    ("1 h to min", "60 min"),
])
def test_unidades_convierte(expresion, esperado):
    assert magnitudes.evaluar(expresion).texto() == esperado


@pytest.mark.parametrize("expresion", [
    "5 km + 3 kg",       # categorías distintas
    "20 °C + 5 °C",      # las escalas afines no se suman
    "10 km / 2 h",       # exigiría una unidad derivada
    "5 km + 3",          # falta la unidad en un operando
    "5 km a kg",         # conversión imposible
    "2 km *",            # expresión incompleta
    "1 / 0 km",          # división entre cero
])
def test_unidades_rechaza(expresion):
    with pytest.raises(magnitudes.ErrorMagnitud):
        magnitudes.evaluar(expresion)


@pytest.mark.parametrize("expresion", [
    "5 km + 3 m", "5 km a m", "20 °C a °F", "1h+30min", "10 km / 2 km",
])
def test_unidades_se_detectan(expresion):
    assert magnitudes.contiene_unidades(expresion)


@pytest.mark.parametrize("expresion", [
    # Ninguna de estas debe desviarse al motor de unidades: son aritmética normal.
    "2+3*4", "sin(30)", "2sin(30)", "5!", "log10(1000)", "2^10", "pi*2",
    "ans*2", "3 a 5", "sqrt(16)", "gcd(12,18)", "mod(7,2)", "50%", "",
])
def test_unidades_no_interfieren(expresion):
    assert not magnitudes.contiene_unidades(expresion)


def test_unidades_conserva_la_unidad_del_primer_operando():
    """«300 m + 5 km» debe dar metros, no kilómetros."""
    assert magnitudes.evaluar("300 m + 5 km").texto() == "5300 m"


# --------------------------------------------------------------------------- #
# Geometría inversa
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("figura,etiqueta,objetivo,incognita,conocidos,esperado", [
    ("Cuadrado", "Área", 50.0, "l", {}, math.sqrt(50)),
    ("Cuadrado", "Perímetro", 20.0, "l", {}, 5.0),
    ("Cuadrado", "Diagonal", 10.0, "l", {}, 10 / math.sqrt(2)),
    ("Círculo", "Área", 100.0, "r", {}, math.sqrt(100 / math.pi)),
    ("Círculo", "Circunferencia", 2 * math.pi * 5, "r", {}, 5.0),
    ("Esfera", "Volumen", 4 / 3 * math.pi * 27, "r", {}, 3.0),
    ("Cubo", "Volumen", 27.0, "a", {}, 3.0),
    ("Cubo", "Área total", 54.0, "a", {}, 3.0),
    ("Rectángulo", "Área", 24.0, "h", {"b": 6.0}, 4.0),
    ("Cilindro", "Volumen", math.pi * 9 * 5, "h", {"r": 3.0}, 5.0),
    ("Cono", "Volumen", 12 * math.pi, "h", {"r": 3.0}, 4.0),
    ("Triángulo (base y altura)", "Área", 12.0, "b", {"h": 4.0}, 6.0),
    ("Hexágono regular", "Área", 6 * math.sqrt(3), "l", {}, 2.0),
    ("Tetraedro regular", "Área total", math.sqrt(3) * 36, "a", {}, 6.0),
])
def test_inverso(figura, etiqueta, objetivo, incognita, conocidos, esperado):
    hallado = figuras.resolver_inverso(figura, etiqueta, objetivo, incognita, conocidos)
    assert hallado == pytest.approx(esperado, rel=1e-6)


def test_inverso_es_coherente_con_el_calculo_directo():
    """Lo hallado, metido de vuelta en la figura, debe dar el objetivo."""
    objetivo = 137.5
    lado = figuras.resolver_inverso("Cuadrado", "Área", objetivo, "l", {})
    area = next(r.valor for r in figuras.calcular("Cuadrado", {"l": lado})
                if r.etiqueta == "Área")
    assert area == pytest.approx(objetivo, rel=1e-9)


@pytest.mark.parametrize("figura,etiqueta,objetivo,incognita,conocidos", [
    ("Cuadrado", "Área", -5.0, "l", {}),                      # objetivo negativo
    ("Cuadrado", "Área", 0.0, "l", {}),                       # objetivo nulo
    ("Polígono regular (n lados)", "Área", 50.0, "n", {"l": 3}),  # incógnita entera
    ("Cuadrado", "Área", 50.0, "zzz", {}),                    # parámetro inexistente
])
def test_inverso_rechaza(figura, etiqueta, objetivo, incognita, conocidos):
    with pytest.raises(figuras.ErrorFigura):
        figuras.resolver_inverso(figura, etiqueta, objetivo, incognita, conocidos)


def test_resultados_invertibles_excluye_adimensionales():
    invertibles = figuras.resultados_invertibles("Cuadrado")
    assert "Área" in invertibles and "Perímetro" in invertibles
    # Los ángulos de un cuadrado son siempre 90°: no dicen nada del tamaño.
    assert not any("ngulo" in etiqueta for etiqueta in invertibles)


def test_todas_las_figuras_declaran_sus_invertibles_sin_fallar():
    for nombre in figuras.FIGURAS:
        figuras.resultados_invertibles(nombre)


# --------------------------------------------------------------------------- #
# Paso a paso
# --------------------------------------------------------------------------- #

def _titulos(lista) -> str:
    return " | ".join(p.titulo for p in lista)


def _todo(lista) -> str:
    return "\n".join(f"{p.titulo} {p.detalle} {p.expresion}" for p in lista)


def test_pasos_derivada_producto():
    x = sp.Symbol("x")
    lista = pasos.pasos_derivada(simbolico.analizar("x^3*sin(x)"), x)
    titulos = _titulos(lista)
    assert "Regla del producto" in titulos
    assert "Regla de la potencia" in titulos
    assert "Derivada del seno" in titulos


def test_pasos_derivada_cadena():
    x = sp.Symbol("x")
    lista = pasos.pasos_derivada(simbolico.analizar("sin(x^2)"), x)
    assert "Regla de la cadena" in _titulos(lista)


def test_pasos_derivada_constante():
    x = sp.Symbol("x")
    lista = pasos.pasos_derivada(simbolico.analizar("x + 5"), x)
    assert "Regla de la constante" in _titulos(lista)


def test_pasos_derivada_acaba_en_el_resultado_correcto():
    x = sp.Symbol("x")
    lista = pasos.pasos_derivada(simbolico.analizar("x^3"), x)
    assert "3*x**2" in lista[-1].expresion


def test_pasos_integral_por_partes():
    x = sp.Symbol("x")
    lista = pasos.pasos_integral(simbolico.analizar("x*exp(x)"), x)
    assert "Integración por partes" in _titulos(lista)
    assert "(x - 1)*exp(x) + C" in _todo(lista)


def test_pasos_integral_comprueba_derivando():
    x = sp.Symbol("x")
    lista = pasos.pasos_integral(simbolico.analizar("2x"), x)
    assert "correcto" in _todo(lista)


def test_pasos_ecuacion_lineal():
    x = sp.Symbol("x")
    lista = pasos.pasos_ecuacion(simbolico.analizar("2x + 5 - 13"), x)
    texto = _todo(lista)
    assert "primer grado" in texto
    assert "x = 4" in texto
    assert "Sumamos 8" in texto  # b es negativo: se suma, no se resta


def test_pasos_ecuacion_cuadratica():
    x = sp.Symbol("x")
    lista = pasos.pasos_ecuacion(simbolico.analizar("x^2 - 5x + 6"), x)
    texto = _todo(lista)
    assert "segundo grado" in texto
    assert "discriminante" in texto
    assert "x = 2" in texto and "x = 3" in texto


def test_pasos_ecuacion_no_repite_la_aproximacion_de_una_raiz_exacta():
    x = sp.Symbol("x")
    lista = pasos.pasos_ecuacion(simbolico.analizar("x^2 - 5x + 6"), x)
    assert "2.0000000" not in _todo(lista)


def test_pasos_ecuacion_raiz_irracional_si_muestra_el_decimal():
    x = sp.Symbol("x")
    texto = _todo(pasos.pasos_ecuacion(simbolico.analizar("x^2 - 2"), x))
    assert "sqrt(2)" in texto and "1.4142" in texto


def test_pasos_ecuacion_discriminante_negativo():
    x = sp.Symbol("x")
    texto = _todo(pasos.pasos_ecuacion(simbolico.analizar("x^2 + 1"), x))
    assert "complejas" in texto


def test_pasos_sistema_gauss():
    x, y = sp.symbols("x y")
    ecuaciones = [sp.Eq(2 * x + 3 * y - 7, 0), sp.Eq(x - y - 1, 0)]
    lista = pasos.pasos_sistema(ecuaciones, [x, y])
    texto = _todo(lista)
    assert "matriz ampliada" in texto
    assert "x = 2" in texto and "y = 1" in texto


def test_pasos_sistema_no_escribe_el_factor_uno():
    """«F2 − F1» se lee mejor que «F2 − 1·F1»."""
    x, y = sp.symbols("x y")
    ecuaciones = [sp.Eq(x + y - 3, 0), sp.Eq(x - y - 1, 0)]
    assert "1·F" not in _titulos(pasos.pasos_sistema(ecuaciones, [x, y]))


def test_pasos_sistema_incompatible():
    x, y = sp.symbols("x y")
    ecuaciones = [sp.Eq(x + y - 2, 0), sp.Eq(x + y - 5, 0)]
    assert "incompatible" in _todo(pasos.pasos_sistema(ecuaciones, [x, y]))


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
