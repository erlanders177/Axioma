"""Pruebas de la lógica de cálculo (no necesitan interfaz gráfica).

Ejecutar con:  python -m pytest tests/   ·   o bien:  python tests/test_nucleo.py
"""

from __future__ import annotations

import math
import os
import sys
import tempfile

# La configuración y el historial se escriben en el perfil del usuario; durante
# las pruebas se redirigen a una carpeta temporal.
os.environ.setdefault("APPDATA", tempfile.mkdtemp(prefix="axioma_test_"))
os.environ.setdefault("XDG_DATA_HOME", os.environ["APPDATA"])
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402

from src.core import bases, calculo, complejos, estadistica, figuras  # noqa: E402
from src.core import matrices, unidades  # noqa: E402
from src.core.evaluador import ErrorExpresion, evaluar  # noqa: E402
from src.core.formato import formatear, normalizar  # noqa: E402
from src.core.simbolico import ErrorSimbolico  # noqa: E402


# --------------------------------------------------------------------------- #
# Evaluador de expresiones
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("expresion,esperado", [
    ("1+2*3", 7), ("(1+2)*3", 9), ("2^10", 1024), ("10/4", 2.5), ("7//2", 3),
    ("5!", 120), ("(2+3)!", 120), ("sin(30)", 0.5), ("cos(60)", 0.5),
    ("tan(45)", 1.0), ("sqrt(16)", 4), ("√16", 4), ("2√9", 6),
    ("2π", 2 * math.pi), ("(2+3)(4)", 20), ("log10(1000)", 3), ("log2(8)", 3),
    ("ln(e)", 1), ("log(8,2)", 3), ("50%", 0.5), ("200*50%", 100),
    ("5²", 25), ("2³", 8), ("hypot(3,4)", 5), ("gcd(12,18)", 6),
    ("lcm(4,6)", 12), ("asin(0.5)", 30), ("atan(1)", 45), ("raiz(27,3)", 3),
    ("cbrt(-8)", -2), ("1.5e-3", 0.0015), ("round(3.14159,2)", 3.14),
    ("-2**2", -4), ("sin(180)", 0.0), ("mod(7,2)", 1), ("max(1,5,3)", 5),
])
def test_evaluador_calcula(expresion, esperado):
    assert evaluar(expresion, "DEG") == pytest.approx(esperado, abs=1e-9)


@pytest.mark.parametrize("expresion", [
    "__import__('os')", "open('a')", "print(1)", "lambda: 1", "[1,2]",
    "1 if 2 else 3", "1/0", "sqrt(-1)", "x+1", "1++", "((1+2)", "9**9**9",
    "log(0)", "asin(2)", "20000!", "tan(90)", "", "   ",
])
def test_evaluador_rechaza(expresion):
    """Ni ejecuta código ajeno ni deja escapar excepciones sin traducir."""
    with pytest.raises(ErrorExpresion):
        evaluar(expresion, "DEG")


def test_evaluador_usa_variables():
    assert evaluar("ans*2", "DEG", {"ans": 21}) == 42


@pytest.mark.parametrize("valor,esperado", [
    (4.0, "4"), (0.5, "0.5"), (1e20, "1e20"), (0.0, "0"), (-2.5, "-2.5"),
    (1 / 3, "0.333333"),
])
def test_formato(valor, esperado):
    assert formatear(valor) == esperado


def test_normalizar_quita_acentos():
    assert normalizar("Casquete ESFÉRICO") == "casquete esferico"


# --------------------------------------------------------------------------- #
# Unidades
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("valor,origen,destino,categoria,esperado", [
    (1, "km", "m", "Longitud", 1000),
    (1, "mi", "km", "Longitud", 1.609344),
    (1, "in", "cm", "Longitud", 2.54),
    (1, "acre", "m²", "Área", 4046.8564224),
    (1, "gal US", "L", "Volumen", 3.785411784),
    (1, "kg", "lb", "Masa", 2.2046226218),
    (0, "°C", "°F", "Temperatura", 32),
    (100, "°C", "°F", "Temperatura", 212),
    (-40, "°C", "°F", "Temperatura", -40),
    (0, "K", "°C", "Temperatura", -273.15),
    (100, "°C", "°De", "Temperatura", 0),
    (180, "°", "rad", "Ángulo", math.pi),
    (100, "km/h", "m/s", "Velocidad", 27.7777777778),
    (1, "kn", "km/h", "Velocidad", 1.852),
    (1, "atm", "Pa", "Presión", 101325),
    (1, "psi", "Pa", "Presión", 6894.757293168),
    (1, "kWh", "J", "Energía y trabajo", 3.6e6),
    (1, "hp", "W", "Potencia", 745.699871582),
    (1, "GiB", "MiB", "Almacenamiento de datos", 1024),
    (1, "GB", "MB", "Almacenamiento de datos", 1000),
    (1, "Ci", "Bq", "Actividad radioactiva", 3.7e10),
    (10, "L/100km", "mi/gal US", "Consumo de combustible", 23.52145833),
    (1, "taza US", "mL", "Medidas de cocina", 236.5882365),
])
def test_conversion(valor, origen, destino, categoria, esperado):
    assert unidades.convertir(valor, origen, destino, categoria) == pytest.approx(esperado, rel=1e-9)


def test_todas_las_unidades_van_y_vuelven():
    """Convertir a la unidad base y volver debe devolver el valor original."""
    for nombre, categoria in unidades.CATEGORIAS.items():
        base = categoria.unidad_base.simbolo
        for unidad in categoria.unidades:
            for valor in (1.0, 7.5, -3.25, 1234.5):
                try:
                    ida = unidades.convertir(valor, unidad.simbolo, base, nombre)
                    vuelta = unidades.convertir(ida, base, unidad.simbolo, nombre)
                except unidades.ErrorConversion:
                    continue
                assert vuelta == pytest.approx(valor, abs=1e-6, rel=1e-9), \
                    f"{nombre} / {unidad.simbolo}"


def test_catalogo_de_unidades_es_coherente():
    assert len(unidades.CATEGORIAS) >= 50
    assert sum(len(c.unidades) for c in unidades.CATEGORIAS.values()) >= 550
    for categoria in unidades.CATEGORIAS.values():
        assert len(categoria.simbolos) == len(set(categoria.simbolos))


def test_busqueda_de_unidades_ignora_acentos():
    resultados = unidades.buscar("metro cubico")
    assert any(u.simbolo == "m³" for _, u in resultados)


# --------------------------------------------------------------------------- #
# Figuras
# --------------------------------------------------------------------------- #

def _resultados(nombre, valores):
    return {r.etiqueta: r.valor for r in figuras.calcular(nombre, valores)}


@pytest.mark.parametrize("nombre,valores,etiqueta,esperado", [
    ("Cuadrado", {"l": 4}, "Área", 16),
    ("Rectángulo", {"b": 6, "h": 3}, "Diagonal", math.sqrt(45)),
    ("Rombo", {"D": 8, "d": 6}, "Lado", 5),
    ("Triángulo (3 lados)", {"a": 3, "b": 4, "c": 5}, "Área", 6),
    ("Triángulo (3 lados)", {"a": 3, "b": 4, "c": 5}, "Radio circunscrito", 2.5),
    ("Triángulo rectángulo", {"a": 3, "b": 4}, "Hipotenusa", 5),
    ("Círculo", {"r": 5}, "Área", 25 * math.pi),
    ("Sector circular", {"r": 6, "a": 90}, "Área", 9 * math.pi),
    ("Elipse", {"a": 5, "b": 3}, "Excentricidad", 0.8),
    ("Hexágono regular", {"l": 2}, "Área", 6 * math.sqrt(3)),
    ("Polígono regular (n lados)", {"n": 4, "l": 5}, "Apotema", 2.5),
    ("Cubo", {"a": 3}, "Volumen", 27),
    ("Cono", {"r": 3, "h": 4}, "Generatriz", 5),
    ("Esfera", {"r": 3}, "Volumen", 36 * math.pi),
    ("Casquete esférico", {"R": 5, "h": 2}, "Radio de la base", 4),
    ("Tetraedro regular", {"a": 6}, "Área total", 36 * math.sqrt(3)),
    ("Toro (donut)", {"R": 5, "r": 2}, "Volumen", 2 * math.pi ** 2 * 20),
    ("Pirámide cuadrangular", {"l": 6, "h": 4}, "Apotema lateral", 5),
])
def test_figura(nombre, valores, etiqueta, esperado):
    assert _resultados(nombre, valores)[etiqueta] == pytest.approx(esperado, rel=1e-9)


@pytest.mark.parametrize("nombre,valores", [
    ("Triángulo (3 lados)", {"a": 1, "b": 2, "c": 10}),   # no cierra
    ("Cuadrado", {"l": 0}),                                # lado nulo
    ("Cuadrado", {"l": -3}),                               # lado negativo
    ("Cuadrado", {}),                                      # falta el dato
    ("Corona circular (anillo)", {"R": 3, "r": 5}),        # radios cruzados
    ("Casquete esférico", {"R": 2, "h": 9}),               # h mayor que el diámetro
    ("Toro (donut)", {"R": 2, "r": 5}),                    # el tubo no cabe
    ("Polígono regular (n lados)", {"n": 5.5, "l": 3}),    # n no entero
    ("Triángulo isósceles", {"b": 10, "a": 3}),            # los lados no llegan
])
def test_figura_rechaza_datos_imposibles(nombre, valores):
    with pytest.raises(figuras.ErrorFigura):
        figuras.calcular(nombre, valores)


def test_todas_las_figuras_calculan_con_sus_ejemplos():
    for nombre, figura in figuras.FIGURAS.items():
        valores = {p.simbolo: p.predeterminado for p in figura.parametros}
        resultados = figura.calcular(valores)
        assert resultados, nombre
        for resultado in resultados:
            assert not math.isnan(float(resultado.valor)), f"{nombre} / {resultado.etiqueta}"
        figura.primitivas(valores)  # el dibujo tampoco debe fallar


def test_catalogo_de_figuras_es_coherente():
    assert len(figuras.FIGURAS) >= 60


# --------------------------------------------------------------------------- #
# Bases numéricas
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("texto,origen,destino,esperado", [
    ("255", 10, 16, "FF"),
    ("1010", 2, 10, "10"),
    ("-1010", 2, 10, "-10"),
    ("FF", 16, 2, "11111111"),
    ("101.101", 2, 10, "5.625"),
    ("0.5", 10, 2, "0.1"),
    ("ZZ", 36, 10, "1295"),
    ("0x1F", 16, 10, "31"),
    ("1_0000", 2, 10, "16"),
    ("777", 8, 10, "511"),
])
def test_cambio_de_base(texto, origen, destino, esperado):
    assert bases.convertir(texto, origen, destino) == esperado


@pytest.mark.parametrize("texto,origen", [
    ("2", 2), ("G", 16), ("", 10), ("1.2.3", 10), ("0b10", 16),
])
def test_base_rechaza_entradas_invalidas(texto, origen):
    with pytest.raises(bases.ErrorBase):
        bases.a_decimal(texto, origen)


def test_operaciones_bit_a_bit():
    filas = dict(bases.operacion_bits("AND", 12, 10))
    assert filas["Resultado (decimal)"] == "8"
    assert dict(bases.operacion_bits("OR", 12, 10))["Resultado (decimal)"] == "14"
    assert dict(bases.operacion_bits("XOR", 12, 10))["Resultado (decimal)"] == "6"
    assert dict(bases.operacion_bits("<<", 3, 2))["Resultado (decimal)"] == "12"
    assert dict(bases.operacion_bits(">>", 12, 2))["Resultado (decimal)"] == "3"


# --------------------------------------------------------------------------- #
# Cálculo simbólico
# --------------------------------------------------------------------------- #

def _valor(filas, etiqueta):
    return next(v for k, v in filas if k == etiqueta)


def test_derivada():
    filas = calculo.derivar("x^3 + 2x", "x", 1)
    assert _valor(filas, "Derivada de orden 1") == "3*x**2 + 2"


def test_derivada_segunda():
    filas = calculo.derivar("x^4", "x", 2)
    assert _valor(filas, "Derivada de orden 2") == "12*x**2"


def test_integral_indefinida():
    filas = calculo.integrar("2x", "x")
    assert _valor(filas, "Integral indefinida") == "x**2 + C"


def test_integral_definida():
    filas = calculo.integrar_definida("x^2", "x", "0", "3")
    assert _valor(filas, "Valor exacto") == "9"


def test_limite_notable():
    filas = calculo.limite("sin(x)/x", "x", "0")
    assert _valor(filas, "Límite") == "1"


def test_limite_lateral_distinto():
    filas = calculo.limite("1/x", "x", "0")
    assert "no existe" in _valor(filas, "Límite")


def test_serie_de_taylor():
    filas = calculo.serie_taylor("exp(x)", "x", "0", 3)
    assert "x**2/2" in _valor(filas, "Serie de Maclaurin (orden 3)")


def test_puntos_criticos():
    filas = calculo.puntos_criticos("x^2", "x")
    assert any("mínimo local" in v for _, v in filas)


def test_analisis_detecta_paridad():
    assert "par" in _valor(calculo.analizar_funcion("x^2", "x"), "Simetría")
    assert "impar" in _valor(calculo.analizar_funcion("x^3", "x"), "Simetría")


@pytest.mark.parametrize("expresion", [
    "__import__('os')", "open('x')", "", "x." + "a", "desconocida(x)",
])
def test_calculo_rechaza_entradas_peligrosas(expresion):
    with pytest.raises(ErrorSimbolico):
        calculo.derivar(expresion, "x")


# --------------------------------------------------------------------------- #
# Matrices
# --------------------------------------------------------------------------- #

def test_matriz_se_analiza_con_varios_separadores():
    a = matrices.analizar_matriz("1 2\n3 4")
    b = matrices.analizar_matriz("1, 2; 3, 4".replace(";", "\n"))
    assert a == b
    assert a.shape == (2, 2)


def test_matriz_determinante_e_inversa():
    m = matrices.analizar_matriz("1 2\n3 4")
    assert _valor(matrices.operar("determinante", m), "Determinante") == "-2"
    filas = matrices.operar("inversa", m)
    assert "1" in _valor(filas, "Comprobación A·A⁻¹")


def test_matriz_singular_no_tiene_inversa():
    m = matrices.analizar_matriz("1 2\n2 4")
    with pytest.raises(matrices.ErrorMatriz):
        matrices.operar("inversa", m)


def test_matriz_producto_comprueba_dimensiones():
    a = matrices.analizar_matriz("1 2 3")
    b = matrices.analizar_matriz("1 2 3")
    with pytest.raises(matrices.ErrorMatriz):
        matrices.operar("multiplicar", a, b)


def test_matriz_filas_desiguales():
    with pytest.raises(matrices.ErrorMatriz):
        matrices.analizar_matriz("1 2 3\n4 5")


def test_matriz_autovalores():
    m = matrices.analizar_matriz("2 0\n0 3")
    filas = matrices.operar("autovalores", m)
    valores = [v for k, v in filas if k == "Autovalor λ"]
    assert any(v.startswith("2") for v in valores)
    assert any(v.startswith("3") for v in valores)


def test_matriz_rango_y_traza():
    m = matrices.analizar_matriz("1 2\n3 4")
    filas = dict(matrices.propiedades(m))
    assert filas["Rango"] == "2"
    assert filas["Traza"] == "5"


def test_sistema_matricial_determinado():
    a = matrices.analizar_matriz("2 3\n1 -1")
    b = matrices.analizar_matriz("7\n1")
    filas = matrices.operar("sistema", a, b)
    assert "DETERMINADO" in _valor(filas, "Clasificación")


def test_sistema_matricial_incompatible():
    a = matrices.analizar_matriz("1 1\n1 1")
    b = matrices.analizar_matriz("2\n5")
    assert "INCOMPATIBLE" in _valor(matrices.operar("sistema", a, b), "Clasificación")


def test_matriz_admite_fracciones_y_raices():
    m = matrices.analizar_matriz("1/2 sqrt(2)\n0 1")
    assert matrices.operar("determinante", m)


# --------------------------------------------------------------------------- #
# Estadística
# --------------------------------------------------------------------------- #

def test_datos_admiten_varios_separadores():
    assert estadistica.analizar_datos("1 2 3") == [1, 2, 3]
    assert estadistica.analizar_datos("1,2,3") == [1, 2, 3]
    assert estadistica.analizar_datos("1\n2\n3") == [1, 2, 3]


def test_datos_rechazan_texto():
    with pytest.raises(estadistica.ErrorEstadistica):
        estadistica.analizar_datos("1 2 hola")


def test_descriptiva():
    filas = dict(estadistica.descriptiva([2, 4, 4, 4, 5, 5, 7, 9]))
    assert filas["Media aritmética"] == "5"
    assert filas["Mediana"] == "4.5"
    assert filas["Moda"] == "4"
    assert filas["Desviación típica poblacional"] == "2"
    assert filas["Número de datos (n)"] == "8"


def test_descriptiva_detecta_atipicos():
    filas = dict(estadistica.descriptiva([1, 2, 3, 4, 5, 100]))
    assert filas["Valores atípicos (criterio 1,5·IQR)"] != "ninguno"


def test_regresion_perfecta():
    filas = dict(estadistica.regresion_lineal([1, 2, 3, 4], [2, 4, 6, 8]))
    assert filas["Pendiente (a)"] == "2"
    assert filas["Coeficiente de correlación r"] == "1"


def test_regresion_exige_series_iguales():
    with pytest.raises(estadistica.ErrorEstadistica):
        estadistica.regresion_lineal([1, 2, 3], [1, 2])


def test_distribucion_normal():
    filas = dict(estadistica.normal(0, 1, 0))
    assert filas["P(X ≤ x)"] == "0.5"


def test_distribucion_binomial():
    filas = dict(estadistica.binomial(10, 0.5, 5))
    # Los valores se devuelven ya formateados a 6 cifras significativas.
    assert float(filas["P(X = k)"]) == pytest.approx(0.2460938, rel=1e-5)
    assert filas["Media (n·p)"] == "5"


def test_distribucion_poisson():
    filas = dict(estadistica.poisson(2, 0))
    assert float(filas["P(X = k)"]) == pytest.approx(math.exp(-2), rel=1e-5)


@pytest.mark.parametrize("funcion,args", [
    (estadistica.normal, (0, -1, 0)),      # desviación negativa
    (estadistica.binomial, (10, 1.5, 5)),  # probabilidad fuera de rango
    (estadistica.binomial, (10, 0.5, 20)),  # k mayor que n
    (estadistica.poisson, (-1, 3)),        # lambda negativo
])
def test_distribuciones_rechazan_parametros_invalidos(funcion, args):
    with pytest.raises(estadistica.ErrorEstadistica):
        funcion(*args)


# --------------------------------------------------------------------------- #
# Números complejos
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("texto,esperado", [
    ("3+4i", complex(3, 4)),
    ("3 + 4i", complex(3, 4)),
    ("-2i", complex(0, -2)),
    ("i", complex(0, 1)),
    ("5", complex(5, 0)),
    ("2-3I", complex(2, -3)),
])
def test_analizar_complejo_binomico(texto, esperado):
    assert complejos.analizar_complejo(texto) == pytest.approx(esperado)


def test_analizar_complejo_polar():
    z = complejos.analizar_complejo("5∠53.13010235")
    assert z.real == pytest.approx(3, abs=1e-6)
    assert z.imag == pytest.approx(4, abs=1e-6)


def test_complejo_rechaza_texto():
    with pytest.raises(complejos.ErrorComplejo):
        complejos.analizar_complejo("hola")


def test_ficha_de_complejo():
    filas = dict(complejos.ficha(complex(3, 4)))
    assert filas["Módulo |z|"] == "5"
    assert filas["Conjugado z̄"] == "3 − 4i"
    assert filas["Cuadrante"] == "primero"


def test_producto_de_complejos():
    filas = dict(complejos.operar("multiplicar", complex(1, 1), complex(1, -1)))
    assert filas["z₁ · z₂"] == "2"


def test_division_entre_cero():
    with pytest.raises(complejos.ErrorComplejo):
        complejos.operar("dividir", complex(1, 1), 0)


def test_raices_n_esimas():
    raices = complejos.lista_raices(complex(1, 0), 3)
    assert len(raices) == 3
    # Las tres raíces cúbicas de 1 elevadas al cubo vuelven a dar 1.
    for raiz in raices:
        assert raiz ** 3 == pytest.approx(complex(1, 0), abs=1e-9)


def test_de_moivre():
    filas = dict(complejos.potencia(complex(0, 1), 4))
    assert filas["Resultado"] == "1"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
