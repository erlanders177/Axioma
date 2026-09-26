"""La calculadora común a las tres versiones: teclas, Ans, S⇔D y el exacto sin sympy.

La clase :class:`Calculadora` es la que usan el escritorio, la web y Android.
Si algo falla aquí, falla en las tres.
"""

from __future__ import annotations

import math
import os
import subprocess
import sys

import pytest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)

from src.core import evaluador, exacto, variables  # noqa: E402
from src.core.calculadora import Calculadora, paso_a_dict  # noqa: E402
from src.core.editor import Editor  # noqa: E402
from src.core.paso import Paso  # noqa: E402


@pytest.fixture(autouse=True)
def _sin_variables():
    variables.borrar_todas()
    yield
    variables.borrar_todas()


def teclear(calculadora: Calculadora, texto: str) -> dict:
    """Escribe como con el teclado: «/» abre una fracción, «=» calcula."""
    estado = calculadora.estado()
    for caracter in texto:
        if caracter == "=":
            estado = calculadora.tecla("calcular")
        else:
            estado = calculadora.tecla("insertar", caracter)
    return estado


# --------------------------------------------------------------------------- #
# El exacto no necesita sympy
# --------------------------------------------------------------------------- #

def test_la_calculadora_no_carga_sympy():
    """En el navegador, cargar sympy congela la pantalla de 5 a 25 segundos."""
    codigo = ("import sys; from src.core import calculadora, exacto; "
              "c = calculadora.Calculadora(); "
              "[c.tecla('insertar', k) for k in 'sin(45)']; c.tecla('calcular'); "
              "assert c.resultado['exacto'] == '√2/2', c.resultado; "
              "assert 'sympy' not in sys.modules")
    subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, check=True)


@pytest.mark.parametrize("expresion,modo,esperado", [
    ("sin(15)", "DEG", "(√6 − √2)/4"),
    ("tan(15)", "DEG", "2 − √3"),
    ("cos(36)", "DEG", "(√5 + 1)/4"),
    ("sin(225)", "DEG", "−√2/2"),
    ("asin(1/2)", "DEG", "30"),
    ("acos(-sqrt(2)/2)", "DEG", "135"),
    ("sin(pi/4)", "RAD", "√2/2"),
    ("asin(1/2)", "RAD", "π/6"),
    ("sin(50)", "GRAD", "√2/2"),
    ("degrees(1)", "DEG", "180/π"),
    ("1/(2*pi)", "DEG", "1/(2π)"),
    ("log(8, 4)", "DEG", "3/2"),
    ("ln(e^3)", "DEG", "3"),
    ("-(1+sqrt(5))/2", "DEG", "−(√5 + 1)/2"),
    ("phi", "DEG", "(√5 + 1)/2"),
    ("1/(sqrt(3)-sqrt(2))", "DEG", "√2 + √3"),
    ("(1+sqrt(2))^3", "DEG", "5√2 + 7"),
    ("sqrt(2)*sqrt(3)", "DEG", "√6"),
    ("cbrt(-27/8)", "DEG", "−3/2"),
    ("8^(2/3)", "DEG", "4"),
    ("0.5", "DEG", "1/2"),
    ("50%", "DEG", "1/2"),
])
def test_mas_formas_exactas(expresion, modo, esperado):
    assert exacto.calcular(expresion, modo).exacto == esperado


@pytest.mark.parametrize("expresion", [
    "sqrt(2)*cbrt(2)",        # 2^(5/6): no es una raíz cuadrada ni cúbica
    "sqrt(3+2*sqrt(2))",      # raíces anidadas
    "1/(1+sqrt(2)+sqrt(3))",  # tres términos en el denominador
    "1e-20",                  # 1/100000000000000000000 no aclara nada
    "sin(20)",
])
def test_lo_que_no_cabe_se_queda_en_decimal(expresion):
    resultado = exacto.calcular(expresion, "DEG")
    assert resultado.exacto is None
    assert resultado.valor == evaluador.evaluar(expresion, "DEG")


@pytest.mark.parametrize("expresion", [
    "sin(15)*cos(75)", "tan(75)^2", "(sqrt(5)-1)/4*4", "1/(1+sqrt(2))^4",
    "sqrt(0.08)", "asin(sqrt(3)/2)+acos(1/2)", "phi^5", "pi^2/6+e",
])
def test_el_exacto_sin_sympy_vale_lo_mismo_que_el_decimal(expresion):
    resultado = exacto.calcular(expresion, "DEG")
    assert resultado.exacto is not None
    assert math.isclose(evaluador.evaluar(resultado.simbolico, "DEG"),
                        evaluador.evaluar(expresion, "DEG"), rel_tol=1e-12)


# --------------------------------------------------------------------------- #
# La calculadora
# --------------------------------------------------------------------------- #

def test_fracciones_tecleadas_dan_fraccion():
    c = Calculadora()
    estado = teclear(c, "1/2+1/3=")
    assert estado["resultado"]["texto"] == "5/6"
    assert estado["resultado"]["tiene_exacto"]
    assert estado["anotar"]["texto"] == "1/2+1/3 = 5/6 ≈ 0.833333"


def test_la_tecla_sd_alterna_exacto_y_decimal():
    c = Calculadora()
    teclear(c, "√(8)=")
    assert c.estado()["resultado"]["texto"] == "2√2"
    assert c.tecla("sd")["resultado"]["texto"] == "2.82843"
    assert c.tecla("sd")["resultado"]["texto"] == "2√2"


def test_sd_no_hace_nada_con_un_entero():
    c = Calculadora()
    estado = teclear(c, "2+2=")
    assert not estado["resultado"]["tiene_exacto"]
    assert c.tecla("sd")["resultado"]["texto"] == "4"


def test_un_operador_tras_el_igual_sigue_desde_ans():
    c = Calculadora()
    teclear(c, "√(2)=")
    estado = teclear(c, "×√(2)=")
    assert estado["texto"] == "Ans×√(2)"
    assert estado["resultado"]["texto"] == "2"


def test_ans_guarda_la_forma_exacta():
    c = Calculadora()
    teclear(c, "1/3=")
    estado = teclear(c, "+1/6=")
    assert estado["resultado"]["texto"] == "1/2"


def test_una_cifra_tras_el_igual_empieza_de_nuevo():
    c = Calculadora()
    teclear(c, "2+2=")
    estado = teclear(c, "5")
    assert estado["texto"] == "5"
    assert estado["resultado"] is None
    assert estado["previa"] == "= 5"


def test_repetir_el_igual_repite_la_cuenta():
    c = Calculadora()
    teclear(c, "3=")
    teclear(c, "×2=")
    assert c.tecla("calcular")["resultado"]["texto"] == "12"
    assert c.tecla("calcular")["resultado"]["texto"] == "24"


def test_borrar_tras_el_igual_vuelve_a_la_expresion():
    c = Calculadora()
    teclear(c, "12+34=")
    estado = c.tecla("borrar")
    assert not estado["calculado"]
    assert estado["texto"] == "12+3"
    assert estado["previa"] == "= 15"


def test_la_tecla_de_negativo_empieza_una_cuenta_nueva():
    c = Calculadora()
    teclear(c, "10=")
    estado = c.tecla("negativo")
    assert estado["texto"] == "−"


def test_un_hueco_vacio_es_un_error_claro():
    c = Calculadora()
    c.tecla("fraccion")
    estado = c.tecla("calcular")
    assert estado["error"] == "Falta el numerador de una fracción"
    assert not estado["calculado"]


def test_la_tecla_de_fraccion_dibuja_dos_huecos():
    c = Calculadora()
    estado = c.tecla("fraccion")
    assert estado["entrada"] == [{"t": "frac", "n": [{"t": "hueco", "activo": True}],
                                  "d": [{"t": "hueco"}]}]


def test_asignar_una_variable():
    c = Calculadora()
    teclear(c, "r")
    c.tecla("insertar", "=")          # el «=» escrito, no la tecla de calcular
    estado = teclear(c, "5=")
    assert estado["resultado"]["variable"] == "r"
    assert variables.valores()["r"] == 5
    c.tecla("limpiar")
    assert teclear(c, "r^2=")["resultado"]["texto"] == "25"


def test_cuentas_con_unidades():
    c = Calculadora()
    estado = teclear(c, "5km+300m=")
    assert estado["resultado"]["texto"] == "5.3 km"
    assert c.pasos()[0].titulo == "Cuenta con unidades"


def test_los_errores_del_evaluador_se_ven():
    c = Calculadora()
    estado = teclear(c, "1÷0=")
    assert estado["error"]
    assert not estado["calculado"]


def test_la_vista_previa_cierra_los_parentesis():
    c = Calculadora()
    assert teclear(c, "sin(30")["previa"] == "= 0.5"


def test_el_modo_de_angulo_cuenta():
    c = Calculadora(modo="RAD")
    assert teclear(c, "sin(π/6)=")["resultado"]["texto"] == "1/2"


def test_el_paso_a_paso_de_la_ultima_cuenta():
    c = Calculadora()
    teclear(c, "sin(45)=")
    assert [p.expresion for p in c.pasos()][0] == "sin(45°) = √2/2"


def test_el_paso_a_paso_sin_nada_escrito():
    assert Calculadora().pasos() == [Paso("No hay nada que desarrollar",
                                          "Escriba una cuenta primero.")]


def test_los_pasos_se_leen_como_a_mano():
    paso = Paso("Ecuación", "", "x**2 - 5*x + 6 = 0")
    assert paso_a_dict(paso)["expresion"] == "x^2 - 5·x + 6 = 0"


# --------------------------------------------------------------------------- #
# El editor, en una línea y de vuelta
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("texto", [
    "(2+3)/(4+5)", "1/2+1/3", "2^(1/2)", "6÷(1/2)", "sqrt(2)/2", "√(2)/2", "√2/2",
    "5!/3", "3²/4", "2^3/4", "sin(30)/2", "Ans/3",
])
def test_el_texto_del_editor_se_vuelve_a_cargar_igual(texto):
    """Lo que se guarda en el historial, cargado otra vez, vale lo mismo."""
    entorno = {"Ans": 7}
    original = Editor()
    original.cargar(texto)
    copia = Editor()
    copia.cargar(original.texto())
    esperado = evaluador.evaluar(texto, "DEG", entorno)
    assert math.isclose(evaluador.evaluar(original.lineal(), "DEG", entorno), esperado)
    assert math.isclose(evaluador.evaluar(copia.lineal(), "DEG", entorno), esperado)


def test_cargar_no_deja_parentesis_dentro_de_la_fraccion():
    e = Editor()
    e.cargar("(2+3)/(4+5)")
    assert e.arbol(con_cursor=False) == [{
        "t": "frac",
        "n": [{"t": "txt", "v": "2+3"}],
        "d": [{"t": "txt", "v": "4+5"}],
    }]


@pytest.mark.parametrize("expresion,esperado", [
    ("(2)²", "4"), ("√(2)²", "2"), ("(1+2)³", "27"), ("π²", "π²"), ("sin(30)²", "1/4"),
])
def test_la_tecla_del_cuadrado_detras_de_un_parentesis(expresion, esperado):
    """La tecla x² escribe «²»: detrás de «)» o de π no es una multiplicación."""
    c = Calculadora()
    c.tecla("cargar", expresion)
    assert c.tecla("calcular")["resultado"]["texto"] == esperado
