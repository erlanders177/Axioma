"""Resultados exactos, editor de fracciones y paso a paso de las cuentas.

Las tres piezas viven en el núcleo y las usan las tres versiones: si fallan
aquí, fallan en Windows, en la web y en el móvil a la vez.
"""

from __future__ import annotations

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import evaluador, exacto  # noqa: E402
from src.core import pasos_cuentas as pc  # noqa: E402
from src.core.editor import Editor, ErrorEditor  # noqa: E402


# --------------------------------------------------------------------------- #
# Resultados exactos
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("expresion,esperado", [
    ("sqrt(8)", "2√2"),
    ("sqrt(72)", "6√2"),
    ("sqrt(12)+sqrt(27)", "5√3"),
    ("6/8", "3/4"),
    ("1/3+1/6", "1/2"),
    ("1/3-1/2", "−1/6"),
    ("0.1+0.2", "3/10"),          # el clásico que en coma flotante da 0.30000000000000004
    ("sin(45)", "√2/2"),
    ("cos(30)", "√3/2"),
    ("tan(60)", "√3"),
    ("1/sqrt(2)", "√2/2"),         # racionalizado, como se pide en clase
    ("1/(1+sqrt(2))", "√2 − 1"),
    ("sqrt(8)+1/3", "2√2 + 1/3"),  # el número suelto, al final
    ("(1+sqrt(5))/2", "(√5 + 1)/2"),
    ("3*sqrt(5)/7", "3√5/7"),
    ("pi/4", "π/4"),
    ("e^2", "e²"),
    ("cbrt(16)", "2∛2"),
    ("7/3", "7/3"),
])
def test_forma_exacta(expresion, esperado):
    assert exacto.calcular(expresion, "DEG").exacto == esperado


@pytest.mark.parametrize("expresion", ["sin(1)", "log10(2)", "2^0.5^0.3", "ln(3)"])
def test_sin_forma_exacta_util_se_queda_en_decimal(expresion):
    """sin(1°) exacto es «sin(π/180)»: no le sirve a nadie."""
    resultado = exacto.calcular(expresion, "DEG")
    assert resultado.exacto is None
    assert not resultado.tiene_exacto


def test_un_entero_no_necesita_la_tecla_de_decimal():
    resultado = exacto.calcular("2*sin(30)+sqrt(16)", "DEG")
    assert resultado.exacto == "5"
    assert not resultado.tiene_exacto


@pytest.mark.parametrize("expresion", [
    "sqrt(8)+1/3", "sin(45)", "1/(1+sqrt(2))", "(2/3)^5", "cos(60)+sin(30)",
    "sqrt(50)-sqrt(8)", "pi/6", "1/7+1/11",
])
def test_el_exacto_vale_lo_mismo_que_el_decimal(expresion):
    """La garantía de todo esto: el exacto nunca dice otra cosa que el decimal."""
    resultado = exacto.calcular(expresion, "DEG")
    assert math.isclose(resultado.valor, evaluador.evaluar(expresion, "DEG"), rel_tol=1e-12)
    import sympy as sp
    assert math.isclose(float(sp.sympify(resultado.simbolico)), resultado.valor, rel_tol=1e-12)


@pytest.mark.parametrize("expresion", ["1/0", "sqrt(-1)", "tan(90)", "log(0)"])
def test_los_errores_son_los_de_siempre(expresion):
    with pytest.raises(evaluador.ErrorExpresion):
        exacto.calcular(expresion, "DEG")


def test_no_se_puede_salir_del_cercado():
    for ataque in ("__import__('os')", "().__class__", "open('x')", "Symbol('x')"):
        with pytest.raises(evaluador.ErrorExpresion):
            exacto.calcular(ataque)


def test_el_arbol_dibuja_fracciones_y_raices():
    arbol = exacto.calcular("3*sqrt(5)/7").arbol
    assert arbol == [{"t": "frac",
                      "n": [{"t": "txt", "v": "3"}, {"t": "raiz", "r": [{"t": "txt", "v": "5"}]}],
                      "d": [{"t": "txt", "v": "7"}]}]


def test_las_variables_conservan_su_valor_exacto():
    resultado = exacto.calcular("h*2", "DEG", {"h": "sqrt(2)"})
    assert resultado.exacto == "2√2"


# --------------------------------------------------------------------------- #
# El editor de fracciones
# --------------------------------------------------------------------------- #

def _calcular(editor: Editor) -> str:
    resultado = exacto.calcular(editor.lineal(), "DEG")
    return resultado.exacto or resultado.decimal


def test_la_tecla_de_fraccion_no_necesita_parentesis():
    """«2 + 3» sobre «4 + 5» es 5/9, no 2 + 3/4 + 5."""
    e = Editor()
    e.fraccion()
    e.escribir("2+3")
    e.derecha()
    e.escribir("4+5")
    assert _calcular(e) == "5/9"


def test_el_numero_de_antes_sube_al_numerador():
    e = Editor()
    e.escribir("12")
    e.fraccion()
    e.escribir("5")
    assert _calcular(e) == "12/5"


def test_con_la_tecla_se_sigue_en_el_hueco_hasta_la_flecha():
    """Como en una Casio: el «+» se queda en el denominador hasta salir."""
    e = Editor()
    e.fraccion()
    e.escribir("1")
    e.derecha()
    e.escribir("2+3")
    assert _calcular(e) == "1/5"
    e.derecha()                     # fuera de la fracción
    e.escribir("+1")
    assert _calcular(e) == "6/5"


@pytest.mark.parametrize("tecleado,esperado", [
    ("1/2+1/3", "5/6"),              # la barra tecleada respeta la prioridad
    ("(2+3)/(4+5)", "5/9"),
    ("1/2*3", "3/2"),
    ("2^3/4", "2"),                   # el numerador es 2³, no el 3 suelto
    ("1/2^3", "1/8"),
    ("1/2/3", "1/6"),
    ("3-1/4", "11/4"),
    ("-3/4", "−3/4"),
    ("0.5/2", "1/4"),
])
def test_teclear_la_barra_da_lo_mismo_que_en_una_linea(tecleado, esperado):
    e = Editor()
    e.escribir(tecleado)
    assert _calcular(e) == esperado
    assert math.isclose(exacto.calcular(e.lineal()).valor,
                        evaluador.evaluar(tecleado, "DEG"), rel_tol=1e-12)


def test_una_fraccion_a_medias_avisa():
    e = Editor()
    e.fraccion()
    e.escribir("1")
    with pytest.raises(ErrorEditor, match="denominador"):
        e.lineal()


def test_borrar_no_se_lleva_una_fraccion_llena_de_golpe():
    e = Editor()
    e.escribir("1/2")
    e.borrar()                       # el 2
    e.borrar()                       # sale al numerador
    assert e.arbol()[0]["t"] == "frac"
    e.borrar()                       # el 1
    e.borrar()                       # la fracción, ya vacía
    assert e.vacio


def test_el_cursor_no_se_pierde_con_las_flechas():
    e = Editor()
    e.escribir("1+2/3+4")
    e.inicio()
    for _ in range(12):
        e.derecha()
        assert str(e.arbol()).count("cursor") == 1
    for _ in range(12):
        e.izquierda()
        assert str(e.arbol()).count("cursor") == 1


def test_un_hueco_vacio_se_ve():
    e = Editor()
    e.fraccion()
    arbol = e.arbol()
    assert arbol[0]["n"] == [{"t": "hueco", "activo": True}]
    assert arbol[0]["d"] == [{"t": "hueco"}]


# --------------------------------------------------------------------------- #
# Paso a paso de las cuentas
# --------------------------------------------------------------------------- #

def _pasos(texto: str) -> list[str]:
    return [p.expresion for p in pc.pasos_expresion(texto, "DEG")]


def test_suma_de_fracciones_con_comun_denominador():
    pasos = _pasos("1/3+1/6")
    assert "1/3 + 1/6 = 2/6 + 1/6" in pasos
    assert "(2 + 1)/6 = 3/6" in pasos
    assert "3/6 = 1/2" in pasos


def test_sacar_factores_de_una_raiz():
    assert "√72 = √(36·2) = √36·√2 = 6√2" in _pasos("sqrt(72)")


def test_agrupar_raices_semejantes():
    pasos = _pasos("sqrt(8)+sqrt(18)")
    assert "2√2 + 3√2 = 5√2" in pasos


def test_racionalizar():
    assert "1/√2 = (1·√2)/(√2·√2) = √2/2" in _pasos("1/sqrt(2)")


def test_racionalizar_con_el_conjugado():
    pasos = _pasos("1/(1+sqrt(2))")
    assert any("conjugado" in p.detalle for p in pc.pasos_expresion("1/(1+sqrt(2))"))
    assert pasos[-1].startswith("√2 − 1")


def test_dividir_fracciones():
    pasos = _pasos("(2/3)/(4/9)")
    assert "(2/3) ÷ (4/9) = (2/3) · (9/4)" in pasos
    assert "18/12 = 3/2" in pasos


def test_valor_notable():
    assert "sin(45°) = √2/2" in _pasos("sin(45)")


def test_decimales_como_fracciones():
    assert "0.1 = 1/10,  0.2 = 1/5" in _pasos("0.1+0.2")


def test_el_ultimo_paso_es_el_resultado_con_su_decimal():
    ultimo = pc.pasos_expresion("sqrt(8)+1/3", "DEG")[-1]
    assert ultimo.titulo == "Resultado"
    assert ultimo.expresion == "2√2 + 1/3   ≈ 3.16176"


@pytest.mark.parametrize("expresion", [
    "1/3+1/6", "sqrt(72)", "(2/3)/(4/9)", "1/(1+sqrt(2))", "(2/3)^2", "2^-3",
    "sqrt(9/4)", "sin(45)+cos(45)", "3^2+4^2", "sqrt(50)-sqrt(8)+1/2",
])
def test_cada_paso_dice_la_verdad(expresion):
    """Cada igualdad de cada paso tiene que ser cierta, no sólo el final."""
    import re

    import sympy as sp
    from sympy.parsing.sympy_parser import (
        convert_xor, implicit_multiplication_application, parse_expr,
        standard_transformations,
    )

    superindices = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻", "0123456789-")

    def numero(lado: str) -> float:
        texto = lado.split("≈")[0]
        texto = re.sub(r"[⁻⁰¹²³⁴⁵⁶⁷⁸⁹]+",
                       lambda m: "**(" + m.group().translate(superindices) + ")", texto)
        texto = re.sub(r"√(\d+)", r"sqrt(\1)", texto).replace("√", "sqrt")
        texto = (texto.replace("·", "*").replace("−", "-").replace("÷", "/")
                 .replace("π", "pi").replace("°", ""))
        transformaciones = standard_transformations + (
            implicit_multiplication_application, convert_xor)
        return float(parse_expr(texto, transformations=transformaciones))

    for paso in pc.pasos_expresion(expresion, "DEG"):
        if "=" not in paso.expresion or "sin" in paso.expresion or "cos" in paso.expresion:
            continue
        lados = [lado.strip() for lado in paso.expresion.split("=")]
        try:
            valores = [numero(lado) for lado in lados]
        except (sp.SympifyError, TypeError, SyntaxError, ValueError):
            continue
        for valor in valores[1:]:
            assert math.isclose(valor, valores[0], rel_tol=1e-9), paso.expresion


# --------------------------------------------------------------------------- #
# Geometría y conversiones
# --------------------------------------------------------------------------- #

def test_geometria_sustituye_y_da_el_exacto():
    pasos = [p.expresion for p in pc.pasos_figura("Cilindro", {"r": 5.0, "h": 10.0}, "cm")]
    assert "V = π·r²·h = π·5²·10 = 250π ≈ 785.398 cm³" in pasos


def test_geometria_usa_los_valores_intermedios():
    pasos = [p.expresion for p in pc.pasos_figura("Rombo", {"D": 8.0, "d": 6.0})]
    assert "P = 4·lado = 4·5 = 20 u" in pasos


def test_todas_las_figuras_dan_pasos_sin_romperse():
    """61 fichas con fórmulas escritas a mano: ninguna puede tumbar el desarrollo."""
    from src.core import figuras as geo
    for nombre, figura in geo.FIGURAS.items():
        datos = {p.simbolo: p.predeterminado for p in figura.parametros}
        pasos = pc.pasos_figura(nombre, datos)
        assert pasos, nombre
        assert pasos[0].titulo == "Datos", nombre


def test_conversion_lineal():
    pasos = [p.expresion for p in pc.pasos_conversion(5, "km", "m", "Longitud")]
    assert pasos == ["1 km = 1000 m", "5 km × 1000 = 5000 m"]


def test_conversion_de_temperatura_con_la_formula_de_clase():
    pasos = [p.expresion for p in pc.pasos_conversion(20, "°C", "°F", "Temperatura")]
    assert pasos == ["°F = °C × 9/5 + 32", "20 × 9/5 + 32 = 68 °F"]
