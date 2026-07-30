"""Pruebas de la interfaz gráfica.

Se ejecutan sin ventana visible (plataforma «offscreen» de Qt), abren los doce
módulos y ejercitan cada uno de extremo a extremo.

Ejecutar con:  python -m pytest tests/test_interfaz.py
"""

from __future__ import annotations

import os
import sys
import tempfile

# Debe fijarse antes de importar Qt.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("APPDATA", tempfile.mkdtemp(prefix="axioma_ui_"))
os.environ.setdefault("XDG_DATA_HOME", os.environ["APPDATA"])
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402
from PyQt5.QtWidgets import QApplication, QMessageBox  # noqa: E402


@pytest.fixture(scope="session")
def app():
    aplicacion = QApplication.instance() or QApplication([])
    # Los diálogos modales bloquearían la ejecución sin interfaz: se anulan y se
    # registran para poder comprobar que se avisó al usuario.
    QMessageBox.warning = staticmethod(lambda *a, **k: _DIALOGOS.append(a[1:3]))
    QMessageBox.information = staticmethod(lambda *a, **k: _DIALOGOS.append(a[1:3]))
    QMessageBox.critical = staticmethod(lambda *a, **k: _DIALOGOS.append(a[1:3]))
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)
    yield aplicacion


_DIALOGOS: list = []


@pytest.fixture(scope="session")
def ventana(app):
    from src.ui.ventana_principal import MODULOS, VentanaPrincipal
    principal = VentanaPrincipal()
    principal.show()
    # Al abrir cada módulo se construye su panel de forma diferida.
    for indice in range(len(MODULOS)):
        principal.navegacion.setCurrentRow(indice)
    yield principal
    principal.close()


@pytest.fixture(autouse=True)
def limpiar_dialogos():
    _DIALOGOS.clear()
    yield


def panel(ventana, clave):
    return ventana._paneles[clave]


# --------------------------------------------------------------------------- #
# Arranque
# --------------------------------------------------------------------------- #

def test_se_abren_todos_los_modulos(ventana):
    from src.ui.ventana_principal import MODULOS
    assert len(ventana._paneles) == len(MODULOS) == 12


def test_cambio_de_tema_no_rompe_ningun_panel(ventana):
    ventana._alternar_tema()
    ventana._alternar_tema()


# --------------------------------------------------------------------------- #
# Calculadora
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("expresion,esperado", [
    ("2+3*4", "14"), ("sin(30)", "0.5"), ("5!", "120"),
    ("sqrt(16)", "4"), ("2^10", "1024"), ("log10(1000)", "3"),
])
def test_calculadora_calcula(ventana, expresion, esperado):
    calc = panel(ventana, "calculadora")
    calc.pantalla.setText(expresion)
    calc.calcular()
    assert calc.pantalla.text() == esperado


def test_calculadora_define_variables(ventana):
    calc = panel(ventana, "calculadora")
    calc._borrar_variables()
    calc.pantalla.setText("r = 5")
    calc.calcular()
    assert calc.variables["r"] == 5
    calc.pantalla.setText("pi*r^2")
    calc.calcular()
    assert calc.pantalla.text().startswith("78.5")
    calc._borrar_variables()
    assert not calc.variables


def test_calculadora_rechaza_nombre_reservado(ventana):
    calc = panel(ventana, "calculadora")
    calc.pantalla.setText("pi = 3")
    calc.calcular()
    assert _DIALOGOS, "debería avisar de que el nombre está reservado"
    assert "pi" not in calc.variables


def test_calculadora_avisa_de_expresion_invalida(ventana):
    calc = panel(ventana, "calculadora")
    calc.pantalla.setText("__import__('os')")
    calc.calcular()
    assert _DIALOGOS


def test_calculadora_memoria(ventana):
    calc = panel(ventana, "calculadora")
    calc._memoria_limpiar()
    calc.pantalla.setText("7")
    calc._memoria_sumar(1)
    assert calc.memoria == 7
    calc._memoria_sumar(-1)
    assert calc.memoria == 0


# --------------------------------------------------------------------------- #
# Conversiones
# --------------------------------------------------------------------------- #

def test_conversiones_recorre_todas_las_categorias(ventana):
    from src.core import unidades
    conv = panel(ventana, "conversiones")
    for grupo, categorias in unidades.GRUPOS.items():
        conv.combo_grupo.setCurrentText(grupo)
        for categoria in categorias:
            conv.combo_categoria.setCurrentText(categoria)
            assert conv.combo_origen.count() > 0, categoria
            assert conv.tabla.rowCount() > 0, categoria


def test_conversiones_convierte(ventana):
    conv = panel(ventana, "conversiones")
    conv.combo_grupo.setCurrentText("Básicas")
    conv.combo_categoria.setCurrentText("Longitud")
    conv.combo_origen.setCurrentIndex(conv.combo_origen.findData("km"))
    conv.combo_destino.setCurrentIndex(conv.combo_destino.findData("m"))
    conv.campo_valor.setText("1")
    conv.convertir()
    assert "1000" in conv.resultado.text()


def test_conversiones_buscador(ventana):
    conv = panel(ventana, "conversiones")
    conv.buscador.setText("nudo")
    conv._buscar_unidad()
    assert conv.combo_categoria.currentText() == "Velocidad"


# --------------------------------------------------------------------------- #
# Bases numéricas
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("texto,origen,destino,esperado", [
    ("255", 10, 16, "FF"), ("-1010", 2, 10, "-10"), ("101.101", 2, 10, "5.625"),
    ("ZZ", 36, 10, "1295"), ("0x1F", 16, 10, "31"),
])
def test_bases_convierte(ventana, texto, origen, destino, esperado):
    bas = panel(ventana, "bases")
    bas.entrada.setText(texto)
    bas.spin_origen.setValue(origen)
    bas.spin_destino.setValue(destino)
    bas.convertir()
    assert esperado in bas.resultado.text()


def test_bases_avisa_de_digito_invalido(ventana):
    bas = panel(ventana, "bases")
    bas.spin_origen.setValue(2)
    bas.entrada.setText("2")
    bas._convertir_en_vivo()
    assert "no existe" in bas.resultado.text()


def test_bases_operaciones_bit_a_bit(ventana):
    bas = panel(ventana, "bases")
    bas.bits_a.setText("12")
    bas.bits_b.setText("10")
    bas.combo_bits.setCurrentText("AND")
    bas.calcular_bits()
    filas = {bas.tabla.item(f, 0).text(): bas.tabla.item(f, 1).text()
             for f in range(bas.tabla.rowCount())}
    assert filas["Resultado (decimal)"] == "8"


# --------------------------------------------------------------------------- #
# Geometría
# --------------------------------------------------------------------------- #

def test_geometria_recorre_todas_las_figuras(ventana):
    from src.core import figuras
    geo = panel(ventana, "geometria")
    geo.buscador.clear()
    geo.combo_grupo.setCurrentText("Todas")
    for nombre in figuras.FIGURAS:
        geo.combo_figura.setCurrentText(nombre)
        assert geo.combo_figura.currentText() == nombre
        assert geo.tabla.rowCount() > 0, nombre


def test_geometria_filtro_ignora_acentos(ventana):
    geo = panel(ventana, "geometria")
    geo.buscador.setText("esfer")
    assert geo.combo_figura.count() >= 4
    geo.buscador.clear()


def test_geometria_guarda_en_el_historial(ventana):
    geo = panel(ventana, "geometria")
    geo.combo_figura.setCurrentText("Cubo")
    antes = geo.historial.lista.count()
    geo._calcular_y_guardar()
    assert geo.historial.lista.count() == antes + 1


# --------------------------------------------------------------------------- #
# Ecuaciones
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("ecuacion,esperados", [
    ("x^2 - 4 = 0", ["-2", "2"]),
    ("2x + 5 = 13", ["4"]),
    ("x^3 - 6x^2 + 11x - 6 = 0", ["1", "2", "3"]),
    ("x^2 + 1 = 0", ["complejas"]),
    ("sqrt(x + 2) = x", ["2"]),
    ("x + 1 = x + 2", ["no tiene solución"]),
    ("x + 1 = x + 1", ["IDENTIDAD"]),
    ("2y - 8 = 0", ["4"]),
])
def test_ecuaciones_resuelve(ventana, ecuacion, esperados):
    ecu = panel(ventana, "ecuaciones")
    ecu.entrada.setText(ecuacion)
    ecu.resolver(silencioso=True)
    salida = ecu.salida.toPlainText()
    for esperado in esperados:
        assert esperado in salida, f"{ecuacion}: falta «{esperado}» en\n{salida}"


@pytest.mark.parametrize("inecuacion,esperado", [
    ("x^2 - 4 > 0", "Solución"),
    ("2x + 1 <= 7", "Solución"),
    ("x^2 + 1 > 0", "cualquier valor real"),
    ("x^2 + 1 < 0", "No hay ningún valor"),
])
def test_ecuaciones_resuelve_inecuaciones(ventana, inecuacion, esperado):
    ecu = panel(ventana, "ecuaciones")
    ecu.entrada.setText(inecuacion)
    ecu.resolver(silencioso=True)
    assert esperado in ecu.salida.toPlainText()


@pytest.mark.parametrize("entrada", ["", "x + y = 1", "5 = 5", ")(", "x = = 1"])
def test_ecuaciones_no_revienta_con_entradas_malas(ventana, entrada):
    ecu = panel(ventana, "ecuaciones")
    ecu.entrada.setText(entrada)
    ecu.resolver(silencioso=True)


# --------------------------------------------------------------------------- #
# Sistemas
# --------------------------------------------------------------------------- #

def _resolver_sistema(ventana, lineas):
    sis = panel(ventana, "sistemas")
    sis.spin_cantidad.setValue(max(2, len(lineas)))
    for campo in sis.campos:
        campo.clear()
    for campo, texto in zip(sis.campos, lineas):
        campo.setText(texto)
    sis.resolver(silencioso=True)
    return sis.salida.toPlainText()


@pytest.mark.parametrize("lineas,esperado", [
    (["2x + 3y = 7", "x - y = 1"], "DETERMINADO"),
    (["x + y = 2", "2x + 2y = 4"], "INDETERMINADO"),
    (["x + y = 2", "x + y = 5"], "INCOMPATIBLE"),
    (["x + y + z = 6", "2x - y + z = 3", "x + 2y - z = 2"], "DETERMINADO"),
    (["2x = 3y + 1", "x + y = 3"], "DETERMINADO"),          # incógnitas a la derecha
    (["x + y = 7/2", "x - y = 1/2"], "DETERMINADO"),        # fracciones
    (["1.5x - 2.5y = 1", "0.5x + y = 3"], "DETERMINADO"),   # decimales
    (["x + y + z = 3", "x - y = 1"], "INDETERMINADO"),      # más incógnitas
    (["x*y = 4", "x + y = 5"], "no es lineal"),
    (["x^2 = 4", "x + y = 5"], "no es lineal"),
])
def test_sistemas(ventana, lineas, esperado):
    assert esperado in _resolver_sistema(ventana, lineas)


def test_sistema_da_la_solucion_correcta(ventana):
    salida = _resolver_sistema(ventana, ["2x + 3y = 7", "x - y = 1"])
    assert "x = 2" in salida and "y = 1" in salida


# --------------------------------------------------------------------------- #
# Cálculo
# --------------------------------------------------------------------------- #

def _calcular(ventana, operacion, valores):
    from src.core import calculo
    pan = panel(ventana, "calculo")
    claves = [c for c, _, _ in calculo.OPERACIONES]
    pan.combo.setCurrentIndex(claves.index(operacion))
    for nombre, valor in valores.items():
        widget = pan._campos.get(nombre)
        if widget is not None and hasattr(widget, "setText"):
            widget.setText(str(valor))
    pan.calcular()
    return {pan.tabla.item(f, 0).text(): pan.tabla.item(f, 1).text()
            for f in range(pan.tabla.rowCount())}


def test_calculo_derivada(ventana):
    filas = _calcular(ventana, "derivada", {"expresion": "x^3 + 2x", "variable": "x", "orden": 1})
    assert filas["Derivada de orden 1"] == "3*x**2 + 2"


def test_calculo_integral(ventana):
    filas = _calcular(ventana, "integral", {"expresion": "2x", "variable": "x"})
    assert filas["Integral indefinida"] == "x**2 + C"


def test_calculo_integral_definida(ventana):
    filas = _calcular(ventana, "integral_definida",
                      {"expresion": "x^2", "variable": "x", "desde": "0", "hasta": "3"})
    assert filas["Valor exacto"] == "9"


def test_calculo_limite(ventana):
    filas = _calcular(ventana, "limite",
                      {"expresion": "sin(x)/x", "variable": "x", "punto": "0"})
    assert filas["Límite"] == "1"


def test_calculo_taylor(ventana):
    filas = _calcular(ventana, "taylor",
                      {"expresion": "exp(x)", "variable": "x", "punto": "0", "orden": 3})
    assert "x**2/2" in filas["Serie de Maclaurin (orden 3)"]


def test_calculo_avisa_de_expresion_invalida(ventana):
    _calcular(ventana, "derivada", {"expresion": "__import__('os')", "variable": "x"})
    assert _DIALOGOS


# --------------------------------------------------------------------------- #
# Matrices
# --------------------------------------------------------------------------- #

def _operar_matrices(ventana, operacion, a, b=""):
    from src.core import matrices as mat
    pan = panel(ventana, "matrices")
    unarias = [c for c, _, _ in mat.OPERACIONES_UNARIAS]
    binarias = [c for c, _ in mat.OPERACIONES_BINARIAS]
    if operacion in unarias:
        pan.combo.setCurrentIndex(unarias.index(operacion))
    else:
        pan.combo.setCurrentIndex(len(unarias) + binarias.index(operacion))
    pan.editor_a.poner(a)
    if b:
        pan.editor_b.poner(b)
    pan.calcular()
    return pan.salida.toPlainText()


def test_matrices_determinante(ventana):
    assert "Determinante:  -2" in _operar_matrices(ventana, "determinante", "1 2\n3 4")


def test_matrices_inversa(ventana):
    assert "Inversa" in _operar_matrices(ventana, "inversa", "1 2\n3 4")


def test_matrices_singular_avisa(ventana):
    salida = _operar_matrices(ventana, "inversa", "1 2\n2 4")
    assert "singular" in salida


def test_matrices_producto_incompatible_avisa(ventana):
    salida = _operar_matrices(ventana, "multiplicar", "1 2 3", "1 2 3")
    assert "deben coincidir" in salida


def test_matrices_autovalores(ventana):
    salida = _operar_matrices(ventana, "autovalores", "2 0\n0 3")
    assert "Autovalor" in salida


def test_matrices_resuelve_sistema(ventana):
    salida = _operar_matrices(ventana, "sistema", "2 3\n1 -1", "7\n1")
    assert "DETERMINADO" in salida


# --------------------------------------------------------------------------- #
# Estadística
# --------------------------------------------------------------------------- #

def test_estadistica_descriptiva(ventana):
    pan = panel(ventana, "estadistica")
    pan.pestanas.setCurrentIndex(0)
    pan.datos.setPlainText("2 4 4 4 5 5 7 9")
    pan.analizar_datos()
    filas = {pan.tabla.item(f, 0).text(): pan.tabla.item(f, 1).text()
             for f in range(pan.tabla.rowCount())}
    assert filas["Media aritmética"] == "5"
    assert filas["Desviación típica poblacional"] == "2"


@pytest.mark.parametrize("grafico", [
    "Histograma", "Diagrama de caja", "Datos en orden", "Frecuencias acumuladas",
])
def test_estadistica_todos_los_graficos(ventana, grafico):
    pan = panel(ventana, "estadistica")
    pan.datos.setPlainText("1 2 3 4 5 6 7 8 9 10")
    pan.combo_grafico.setCurrentText(grafico)
    pan._redibujar_datos()


def test_estadistica_regresion(ventana):
    pan = panel(ventana, "estadistica")
    pan.pestanas.setCurrentIndex(1)
    pan.datos_x.setPlainText("1 2 3 4")
    pan.datos_y.setPlainText("2 4 6 8")
    pan.analizar_regresion()
    filas = {pan.tabla.item(f, 0).text(): pan.tabla.item(f, 1).text()
             for f in range(pan.tabla.rowCount())}
    assert filas["Pendiente (a)"] == "2"
    assert filas["Coeficiente de correlación r"] == "1"


def test_estadistica_regresion_series_desiguales_avisa(ventana):
    pan = panel(ventana, "estadistica")
    pan.pestanas.setCurrentIndex(1)
    pan.datos_x.setPlainText("1 2 3")
    pan.datos_y.setPlainText("1 2")
    pan.analizar_regresion()
    assert _DIALOGOS


@pytest.mark.parametrize("indice", [0, 1, 2])
def test_estadistica_distribuciones(ventana, indice):
    pan = panel(ventana, "estadistica")
    pan.pestanas.setCurrentIndex(2)
    pan.combo_distribucion.setCurrentIndex(indice)
    pan.analizar_distribucion()
    assert pan.tabla.rowCount() > 0


# --------------------------------------------------------------------------- #
# Números complejos
# --------------------------------------------------------------------------- #

def _complejos(ventana, operacion, z1, z2="", extra=""):
    from src.core import complejos as cpx
    pan = panel(ventana, "complejos")
    claves = [c for c, _, _, _ in cpx.OPERACIONES]
    pan.combo.setCurrentIndex(claves.index(operacion))
    pan.campo_z1.setText(z1)
    if z2:
        pan.campo_z2.setText(z2)
    if extra:
        pan.campo_extra.setText(extra)
    pan.calcular()
    return {pan.tabla.item(f, 0).text(): pan.tabla.item(f, 1).text()
            for f in range(pan.tabla.rowCount())}


def test_complejos_ficha(ventana):
    filas = _complejos(ventana, "ficha", "3+4i")
    assert filas["Módulo |z|"] == "5"
    assert filas["Cuadrante"] == "primero"


def test_complejos_forma_polar_de_entrada(ventana):
    filas = _complejos(ventana, "ficha", "5∠53.13010235")
    assert filas["Parte real"].startswith("3")


def test_complejos_producto(ventana):
    filas = _complejos(ventana, "multiplicar", "1+1i", "1-1i")
    assert filas["z₁ · z₂"] == "2"


def test_complejos_raices(ventana):
    filas = _complejos(ventana, "raices", "1", extra="3")
    assert sum(1 for k in filas if k.startswith("Raíz")) == 3


def test_complejos_entrada_invalida_avisa(ventana):
    _complejos(ventana, "ficha", "hola")
    assert _DIALOGOS


# --------------------------------------------------------------------------- #
# Graficador
# --------------------------------------------------------------------------- #

def test_graficador_dibuja_varias_funciones(ventana):
    graf = panel(ventana, "graficador")
    graf.campos[0].setText("sin(x)")
    graf.campos[1].setText("cos(x)")
    graf.campos[2].clear()
    graf.campos[3].clear()
    graf.dibujar()
    assert "sin(x)" in graf.informacion.toPlainText()


def test_graficador_marca_los_cortes(ventana):
    graf = panel(ventana, "graficador")
    for campo in graf.campos:
        campo.clear()
    graf.campos[0].setText("x^2 - 4")
    graf.dibujar()
    texto = graf.informacion.toPlainText()
    assert "cortes con el eje X" in texto and "-2" in texto


def test_graficador_avisa_de_intervalo_invalido(ventana):
    graf = panel(ventana, "graficador")
    graf.campos[0].setText("x")
    graf.x_min.setText("10")
    graf.x_max.setText("-10")
    graf.dibujar()
    assert _DIALOGOS
    graf.x_min.setText("-10")
    graf.x_max.setText("10")


def test_graficador_con_asintotas(ventana):
    graf = panel(ventana, "graficador")
    for campo in graf.campos:
        campo.clear()
    graf.campos[0].setText("1/x")
    graf.dibujar()


# --------------------------------------------------------------------------- #
# Combinatoria
# --------------------------------------------------------------------------- #

def _combinatoria(ventana, operacion, valores):
    pan = panel(ventana, "combinatoria")
    claves = [c for c, _, _ in pan.OPERACIONES]
    pan.combo.setCurrentIndex(claves.index(operacion))
    for nombre, valor in valores.items():
        pan.campos[nombre].setText(str(valor))
    pan.calcular()
    return pan.salida.toPlainText()


@pytest.mark.parametrize("operacion,valores,esperado", [
    ("factorial", {"n": 10}, "3628800"),
    ("factorial", {"n": 0}, "0! = 1"),
    ("combinaciones", {"n": 10, "r": 3}, "120"),
    ("permutaciones", {"n": 10, "r": 3}, "720"),
    ("variaciones_rep", {"n": 2, "r": 10}, "1024"),
    ("combinaciones_rep", {"n": 5, "r": 3}, "35"),
    ("doble_factorial", {"n": 9}, "945"),
    ("subfactorial", {"n": 4}, "9"),
    ("catalan", {"n": 5}, "42"),
    ("gamma", {"x": 0.5}, "1.77245"),
])
def test_combinatoria(ventana, operacion, valores, esperado):
    assert esperado in _combinatoria(ventana, operacion, valores)


def test_combinatoria_numeros_enormes(ventana):
    """El límite de Python para convertir enteros a texto no debe estorbar."""
    assert "dígitos" in _combinatoria(ventana, "factorial", {"n": 5000})
    assert _combinatoria(ventana, "subfactorial", {"n": 2000})


@pytest.mark.parametrize("operacion,valores", [
    ("combinaciones", {"n": 3, "r": 10}),
    ("factorial", {"n": -5}),
    ("factorial", {"n": 2.5}),
    ("gamma", {"x": 0}),
])
def test_combinatoria_rechaza_datos_invalidos(ventana, operacion, valores):
    _combinatoria(ventana, operacion, valores)
    assert _DIALOGOS


# --------------------------------------------------------------------------- #
# Historial
# --------------------------------------------------------------------------- #

def test_historial_guarda_filtra_y_borra_por_identidad(ventana):
    calc = panel(ventana, "calculadora")
    lista = calc.historial
    lista._limpiar_todo()

    calc.pantalla.setText("1+1")
    calc.calcular()
    calc.pantalla.setText("2+2")
    calc.calcular()
    assert lista.lista.count() == 2

    lista.buscador.setText("2+2")
    visibles = sum(0 if lista.lista.item(i).isHidden() else 1
                   for i in range(lista.lista.count()))
    assert visibles == 1
    lista.buscador.clear()

    lista.lista.item(0).setSelected(True)
    lista._borrar_seleccion()
    assert lista.lista.count() == 1

    # El borrado debe haberse aplicado también en disco.
    lista.recargar()
    assert lista.lista.count() == 1


def test_historial_se_restaura_con_doble_clic(ventana):
    calc = panel(ventana, "calculadora")
    calc.pantalla.setText("3*7")
    calc.calcular()
    calc.pantalla.clear()
    calc.historial._restaurar_elemento(calc.historial.lista.item(0))
    assert calc.pantalla.text() == "3*7"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
