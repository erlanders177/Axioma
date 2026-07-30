"""Pruebas de los módulos de análisis avanzado.

Ecuaciones diferenciales, métodos numéricos, transformadas y ajuste de curvas.
"""

from __future__ import annotations

import math
import os
import sys
import tempfile

os.environ.setdefault("APPDATA", tempfile.mkdtemp(prefix="axioma_avanzado_"))
os.environ.setdefault("XDG_DATA_HOME", os.environ["APPDATA"])
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
import sympy as sp  # noqa: E402

from src.core import ajuste, edo, numerico, transformadas  # noqa: E402


def _valor(filas, etiqueta):
    return next((v for k, v in filas if k == etiqueta), None)


def _todo(filas):
    return "\n".join(f"{k} {v}" for k, v in filas)


# --------------------------------------------------------------------------- #
# Ecuaciones diferenciales
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("ecuacion,esperado", [
    ("y' + 2y = 0", "exp(-2*x)"),
    ("y' = y", "exp(x)"),
    ("y' = 2x", "x**2"),
])
def test_edo_solucion_general(ecuacion, esperado):
    filas = edo.resolver(ecuacion)
    assert esperado in _valor(filas, "Solución general")


@pytest.mark.parametrize("ecuacion,condiciones,esperado", [
    ("y' = x*y", "y(0) = 1", "exp(x**2/2)"),
    ("y' + y = 0", "y(0) = 3", "3*exp(-x)"),
])
def test_edo_solucion_particular(ecuacion, condiciones, esperado):
    filas = edo.resolver(ecuacion, condiciones)
    assert esperado in _valor(filas, "Solución particular")


def test_edo_segundo_orden():
    filas = edo.resolver("y'' - 3y' + 2y = 0", "y(0) = 1, y'(0) = 0")
    assert _valor(filas, "Orden") == "2"
    assert "correcta" in _valor(filas, "Comprobación")


def test_edo_notacion_leibniz():
    """dy/dx debe entenderse igual que y'."""
    con_prima = edo.resolver("y' = y")
    con_leibniz = edo.resolver("dy/dx = y")
    assert _valor(con_prima, "Solución general") == _valor(con_leibniz, "Solución general")


def test_edo_coeficiente_pegado():
    """«2y» sin asterisco: el \\b de las regex no casa entre dígito y letra."""
    filas = edo.resolver("y' + 2y = 0")
    assert "exp(-2*x)" in _valor(filas, "Solución general")


def test_edo_clasifica():
    filas = edo.resolver("y' + 2y = 0")
    assert "separables" in _valor(filas, "Tipo") or "lineal" in _valor(filas, "Tipo")
    assert _valor(filas, "Linealidad") == "lineal"


def test_edo_comprueba_la_solucion():
    filas = edo.resolver("y' = x*y", "y(0) = 1")
    assert "correcta" in _valor(filas, "Comprobación")


def test_edo_variables_personalizadas():
    filas = edo.resolver("u' = u", "", "u", "t")
    assert "exp(t)" in _valor(filas, "Solución general")


@pytest.mark.parametrize("entrada", [
    "",                       # vacía
    "x + 1 = 0",              # sin derivada
    "y' + = 3",               # sintaxis rota
    "__import__('os')",       # entrada peligrosa
])
def test_edo_rechaza(entrada):
    with pytest.raises(edo.ErrorEDO):
        edo.resolver(entrada)


def test_edo_rechaza_variables_iguales():
    with pytest.raises(edo.ErrorEDO):
        edo.resolver("y' = y", "", "x", "x")


def test_edo_sistema():
    filas = edo.resolver_sistema(["x' = y", "y' = -x"])
    texto = _todo(filas)
    assert "sin(t)" in texto and "cos(t)" in texto


def test_edo_campo_de_direcciones():
    pendiente, expresion = edo.campo_direcciones("y' = x - y")
    assert pendiente(1.0, 2.0) == pytest.approx(-1.0)
    assert "x - y" in expresion


def test_edo_campo_solo_primer_orden():
    with pytest.raises(edo.ErrorEDO):
        edo.campo_direcciones("y'' + y = 0")


# --------------------------------------------------------------------------- #
# Métodos numéricos
# --------------------------------------------------------------------------- #

def test_biseccion_encuentra_raiz():
    raiz, iteraciones, nota = numerico.biseccion("x^2 - 2", 0, 2)
    assert raiz == pytest.approx(math.sqrt(2), abs=1e-9)
    assert iteraciones and "convergió" in nota


def test_biseccion_exige_cambio_de_signo():
    with pytest.raises(numerico.ErrorNumerico):
        numerico.biseccion("x^2 + 1", 0, 2)


def test_newton_converge_mas_rapido_que_biseccion():
    _, it_newton, _ = numerico.newton_raphson("x^2 - 2", 1)
    _, it_biseccion, _ = numerico.biseccion("x^2 - 2", 0, 2)
    assert len(it_newton) < len(it_biseccion)


def test_newton_avisa_si_la_derivada_se_anula():
    with pytest.raises(numerico.ErrorNumerico):
        numerico.newton_raphson("x^3", 0)


def test_secante_encuentra_raiz():
    raiz, _, _ = numerico.secante("x^2 - 2", 1, 2)
    assert raiz == pytest.approx(math.sqrt(2), abs=1e-9)


def test_secante_exige_puntos_distintos():
    with pytest.raises(numerico.ErrorNumerico):
        numerico.secante("x^2 - 2", 1, 1)


@pytest.mark.parametrize("metodo", [numerico.trapecio, numerico.simpson])
def test_integracion_numerica(metodo):
    valor, _, _ = metodo("x^2", 0, 3, 200)
    assert valor == pytest.approx(9.0, rel=1e-4)


def test_simpson_es_mas_preciso_que_trapecio():
    v_trapecio, _, _ = numerico.trapecio("sin(x)", 0, math.pi, 20)
    v_simpson, _, _ = numerico.simpson("sin(x)", 0, math.pi, 20)
    assert abs(v_simpson - 2.0) < abs(v_trapecio - 2.0)


def test_integracion_compara_con_el_valor_exacto():
    _, _, nota = numerico.simpson("x^2", 0, 3, 50)
    assert "valor exacto" in nota


def test_integracion_rechaza_intervalo_invertido():
    with pytest.raises(numerico.ErrorNumerico):
        numerico.trapecio("x", 5, 1, 10)


@pytest.mark.parametrize("metodo", ["lagrange", "newton"])
def test_interpolacion(metodo):
    polinomio, _, _ = numerico.interpolar([(0, 1), (1, 3), (2, 7)], metodo)
    x = sp.Symbol("x")
    assert sp.simplify(polinomio - (x ** 2 + x + 1)) == 0


def test_los_dos_metodos_de_interpolacion_coinciden():
    puntos = [(0, 1), (1, 3), (2, 7), (3, 13)]
    a, _, _ = numerico.interpolar(puntos, "lagrange")
    b, _, _ = numerico.interpolar(puntos, "newton")
    assert sp.simplify(a - b) == 0


def test_interpolacion_rechaza_x_repetida():
    with pytest.raises(numerico.ErrorNumerico):
        numerico.interpolar([(0, 1), (0, 2)])


def test_runge_kutta_es_mas_preciso_que_euler():
    """y′ = y con y(0) = 1 debe dar e en x = 1."""
    it_euler, _ = numerico.euler("y", 0, 1, 0.1, 10)
    it_rk4, _ = numerico.runge_kutta_4("y", 0, 1, 0.1, 10)
    error_euler = abs(it_euler[-1].valores["yₙ"] - math.e)
    error_rk4 = abs(it_rk4[-1].valores["yₙ"] - math.e)
    assert error_rk4 < error_euler / 1000


def test_edo_numerica_rechaza_paso_nulo():
    with pytest.raises(numerico.ErrorNumerico):
        numerico.euler("y", 0, 1, 0, 10)


# --------------------------------------------------------------------------- #
# Transformadas
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("funcion,esperado", [
    ("1", "1/s"),
    ("t", "s**(-2)"),
    ("t^2", "2/s**3"),
    ("exp(3*t)", "1/(s - 3)"),
])
def test_laplace(funcion, esperado):
    filas = transformadas.laplace(funcion)
    assert esperado in _valor(filas, "Transformada")


def test_laplace_comprueba_antitransformando():
    filas = transformadas.laplace("t^2")
    assert "correcta" in _valor(filas, "Comprobación (antitransformar)")


@pytest.mark.parametrize("funcion,esperado", [
    ("1/(s-2)", "exp(2*t)"),
    ("1/s^2", "t"),
])
def test_laplace_inversa(funcion, esperado):
    filas = transformadas.laplace_inversa(funcion)
    assert esperado in _valor(filas, "Transformada inversa")


def test_serie_de_fourier_de_x():
    """Resultado conocido: 2·sen(x) − sen(2x) + (2/3)·sen(3x) − …"""
    filas = transformadas.serie_fourier("x", "-pi", "pi", 3)
    serie = _valor(filas, "Serie truncada (orden 3)")
    assert "2*sin(x)" in serie
    assert "sin(2*x)" in serie
    assert _valor(filas, "a₀ (término constante)") == "0"


def test_serie_de_fourier_detecta_simetria_impar():
    filas = transformadas.serie_fourier("x", "-pi", "pi", 2)
    assert "impar" in _valor(filas, "Simetría")


def test_serie_de_fourier_detecta_simetria_par():
    filas = transformadas.serie_fourier("x^2", "-pi", "pi", 2)
    assert "par" in _valor(filas, "Simetría")


def test_serie_rechaza_orden_excesivo():
    with pytest.raises(transformadas.ErrorTransformada):
        transformadas.serie_fourier("x", "-pi", "pi", 500)


def test_serie_rechaza_intervalo_vacio():
    with pytest.raises(transformadas.ErrorTransformada):
        transformadas.serie_fourier("x", "1", "1", 3)


def test_transformada_rechaza_variables_iguales():
    with pytest.raises(transformadas.ErrorTransformada):
        transformadas.laplace("t", "t", "t")


def test_tabla_de_laplace_existe():
    assert len(transformadas.TABLA_LAPLACE) >= 10
    assert all(len(fila) == 3 for fila in transformadas.TABLA_LAPLACE)


# --------------------------------------------------------------------------- #
# Ajuste de curvas
# --------------------------------------------------------------------------- #

def test_ajuste_lineal_exacto():
    resultado = ajuste.ajustar([1, 2, 3, 4], [3, 5, 7, 9], "poli1")
    assert resultado.r2 == pytest.approx(1.0)
    assert resultado.evaluar(5) == pytest.approx(11.0, rel=1e-6)


def test_ajuste_cuadratico_exacto():
    x = [1, 2, 3, 4, 5]
    y = [2 * v ** 2 + 1 for v in x]
    resultado = ajuste.ajustar(x, y, "poli2")
    assert resultado.r2 == pytest.approx(1.0)
    assert resultado.evaluar(6) == pytest.approx(73.0, rel=1e-6)


def test_ajuste_exponencial_exacto():
    x = [0, 1, 2, 3, 4]
    y = [2 * math.exp(0.5 * v) for v in x]
    resultado = ajuste.ajustar(x, y, "exponencial")
    assert resultado.r2 == pytest.approx(1.0, abs=1e-9)
    assert resultado.linealizado


def test_ajuste_potencial_exacto():
    x = [1, 2, 3, 4, 5]
    y = [3 * v ** 2 for v in x]
    resultado = ajuste.ajustar(x, y, "potencial")
    assert resultado.r2 == pytest.approx(1.0, abs=1e-9)


def test_comparar_elige_el_modelo_correcto():
    """Con datos exponenciales, el mejor ajuste debe ser el exponencial."""
    x = [0, 1, 2, 3, 4, 5]
    y = [2 * math.exp(0.5 * v) for v in x]
    candidatos, _ = ajuste.comparar(x, y)
    assert candidatos[0].clave == "exponencial"


def test_comparar_ordena_por_calidad():
    x = [1, 2, 3, 4, 5, 6]
    y = [v ** 2 for v in x]
    candidatos, _ = ajuste.comparar(x, y)
    assert candidatos == sorted(candidatos, key=lambda a: a.r2, reverse=True)


def test_comparar_informa_de_los_descartados():
    """Con X negativos, el logarítmico y el potencial no son aplicables."""
    _, filas = ajuste.comparar([-2, -1, 1, 2, 3], [1, 2, 3, 4, 5])
    assert "no aplicable" in _todo(filas)


def test_ajuste_avisa_del_modelo_linealizado():
    x = [0, 1, 2, 3, 4]
    y = [2 * math.exp(0.5 * v) for v in x]
    _, filas = ajuste.comparar(x, y)
    assert "linealizando" in _todo(filas)


@pytest.mark.parametrize("x,y,modelo", [
    ([1, 2, 3], [1, -2, 3], "exponencial"),   # Y negativo
    ([-1, 2, 3], [1, 2, 3], "logaritmico"),   # X negativo
    ([-1, 2, 3], [1, -2, 3], "potencial"),    # ambos
    ([1, 2], [1, 2], "poli1"),                # muy pocos datos
    ([1, 1, 1], [1, 2, 3], "poli1"),          # X constante
])
def test_ajuste_rechaza(x, y, modelo):
    with pytest.raises(ajuste.ErrorAjuste):
        ajuste.ajustar(x, y, modelo)


def test_ajuste_rechaza_series_de_distinta_longitud():
    with pytest.raises(ajuste.ErrorAjuste):
        ajuste.ajustar([1, 2, 3], [1, 2], "poli1")


def test_ajuste_rechaza_grado_imposible():
    """No se puede ajustar un polinomio de grado 5 con 4 puntos."""
    with pytest.raises(ajuste.ErrorAjuste):
        ajuste.ajustar([1, 2, 3, 4], [1, 2, 3, 4], "polinomico", 5)


def test_prediccion():
    """La recta y = 2x + 1 vale 21 en x = 10."""
    resultado = ajuste.ajustar([1, 2, 3, 4], [3, 5, 7, 9], "poli1")
    filas = ajuste.predecir(resultado, [10.0])
    assert "21" in _todo(filas)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
