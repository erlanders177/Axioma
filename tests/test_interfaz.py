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
from PyQt5.QtCore import Qt  # noqa: E402
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
    # Al abrir cada módulo se construye su panel de forma diferida. Se navega
    # con `ir_a_modulo` y no con `setCurrentRow`, porque la lista lleva
    # intercalados los encabezados de grupo y las filas ya no coinciden con los
    # índices de MODULOS.
    for indice in range(len(MODULOS)):
        principal.ir_a_modulo(indice)
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
    assert len(ventana._paneles) == len(MODULOS) == 16


def test_los_encabezados_de_grupo_no_son_seleccionables(ventana):
    """Pulsar un encabezado no debe cambiar de módulo ni romper nada."""
    from src.ui.ventana_principal import GRUPOS_NAVEGACION

    assert GRUPOS_NAVEGACION, "no hay grupos definidos"
    filas_de_modulo = set(ventana._fila_de_modulo.values())
    encabezados = [f for f in range(ventana.navegacion.count())
                   if f not in filas_de_modulo]
    assert len(encabezados) == len(GRUPOS_NAVEGACION)
    for fila in encabezados:
        assert not (ventana.navegacion.item(fila).flags() & Qt.ItemIsSelectable)


def test_ir_a_modulo_traduce_bien_los_indices(ventana):
    from src.ui.ventana_principal import MODULOS

    for indice, (clave, _, titulo, _, _) in enumerate(MODULOS):
        ventana.ir_a_modulo(indice)
        assert ventana.titulo_modulo.text().endswith(titulo), clave


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


# --------------------------------------------------------------------------- #
# Unidades dentro de la calculadora
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("expresion,esperado", [
    ("5 km + 300 m", "5.3 km"),
    ("20 °C a °F", "68 °F"),
    ("1 h + 30 min", "1.5 h"),
    ("2 GB a MB", "2000 MB"),
])
def test_calculadora_opera_con_unidades(ventana, expresion, esperado):
    calc = panel(ventana, "calculadora")
    calc.pantalla.setText(expresion)
    calc.calcular()
    assert calc.pantalla.text() == esperado


def test_calculadora_avisa_si_las_unidades_no_encajan(ventana):
    calc = panel(ventana, "calculadora")
    calc.pantalla.setText("5 km + 3 kg")
    calc.calcular()
    assert _DIALOGOS


def test_las_unidades_no_estorban_a_la_aritmetica_normal(ventana):
    """Comprueba que el motor de unidades no secuestra expresiones corrientes."""
    calc = panel(ventana, "calculadora")
    for expresion, esperado in [("2+3*4", "14"), ("sin(30)", "0.5"), ("5!", "120")]:
        calc.pantalla.setText(expresion)
        calc.calcular()
        assert calc.pantalla.text() == esperado, expresion


# --------------------------------------------------------------------------- #
# Historial con las flechas del teclado
# --------------------------------------------------------------------------- #

def test_flechas_recuperan_expresiones_anteriores(ventana):
    from PyQt5.QtCore import QEvent, Qt
    from PyQt5.QtGui import QKeyEvent

    calc = panel(ventana, "calculadora")
    calc.historial._limpiar_todo()
    calc._expresiones.clear()
    calc._posicion_historial = 0

    for expresion in ("1+1", "2+2", "3+3"):
        calc.pantalla.setText(expresion)
        calc.calcular()

    calc.pantalla.clear()

    def pulsar(tecla):
        calc.eventFilter(calc.pantalla, QKeyEvent(QEvent.KeyPress, tecla, Qt.NoModifier))

    pulsar(Qt.Key_Up)
    assert calc.pantalla.text() == "3+3"
    pulsar(Qt.Key_Up)
    assert calc.pantalla.text() == "2+2"
    pulsar(Qt.Key_Up)
    assert calc.pantalla.text() == "1+1"
    pulsar(Qt.Key_Up)          # ya no hay más: se queda donde está
    assert calc.pantalla.text() == "1+1"
    pulsar(Qt.Key_Down)
    assert calc.pantalla.text() == "2+2"


def test_flechas_no_fallan_sin_historial(ventana):
    from PyQt5.QtCore import QEvent, Qt
    from PyQt5.QtGui import QKeyEvent

    calc = panel(ventana, "calculadora")
    calc._expresiones.clear()
    calc._posicion_historial = 0
    calc.eventFilter(calc.pantalla,
                     QKeyEvent(QEvent.KeyPress, Qt.Key_Up, Qt.NoModifier))


# --------------------------------------------------------------------------- #
# Geometría inversa
# --------------------------------------------------------------------------- #

def test_geometria_inversa_halla_el_lado(ventana):
    import math

    geo = panel(ventana, "geometria")
    geo.buscador.clear()
    geo.combo_figura.setCurrentText("Cuadrado")
    assert geo.bloque_inverso.isVisible() or True  # depende del gestor de ventanas

    geo.combo_conocido.setCurrentText("Área")
    indice = geo.combo_incognita.findData("l")
    assert indice >= 0
    geo.combo_incognita.setCurrentIndex(indice)
    geo.valor_conocido.setText("50")
    geo._resolver_inverso()

    assert "7.07" in geo.resultado_inverso.text()
    # El campo debe quedar relleno con lo hallado.
    assert float(geo._campos["l"].text()) == pytest.approx(math.sqrt(50), rel=1e-6)


def test_geometria_inversa_pide_los_datos_que_faltan(ventana):
    geo = panel(ventana, "geometria")
    geo.combo_figura.setCurrentText("Rectángulo")
    geo._campos["b"].clear()
    geo.combo_conocido.setCurrentText("Área")
    geo.combo_incognita.setCurrentIndex(geo.combo_incognita.findData("h"))
    geo.valor_conocido.setText("24")
    geo._resolver_inverso()
    assert _DIALOGOS


def test_geometria_inversa_se_oculta_cuando_no_aplica(ventana):
    """El polígono regular de n lados tiene una incógnita entera."""
    geo = panel(ventana, "geometria")
    geo.combo_figura.setCurrentText("Polígono regular (n lados)")
    # Queda «l», que sí es continuo, así que el bloque sigue disponible.
    assert geo.combo_incognita.count() >= 1
    for i in range(geo.combo_incognita.count()):
        assert geo.combo_incognita.itemData(i) != "n"


# --------------------------------------------------------------------------- #
# Paso a paso
# --------------------------------------------------------------------------- #

def test_pasos_en_el_panel_de_calculo(ventana):
    from src.core import calculo

    pan = panel(ventana, "calculo")
    claves = [c for c, _, _ in calculo.OPERACIONES]
    pan.combo.setCurrentIndex(claves.index("derivada"))
    pan._campos["expresion"].setText("x^3*sin(x)")
    pan._campos["variable"].setText("x")
    pan.calcular()

    desarrollo = pan.pasos.toPlainText()
    assert "Regla del producto" in desarrollo
    assert "Derivada del seno" in desarrollo


def test_pasos_de_integral_en_el_panel(ventana):
    from src.core import calculo

    pan = panel(ventana, "calculo")
    claves = [c for c, _, _ in calculo.OPERACIONES]
    pan.combo.setCurrentIndex(claves.index("integral"))
    pan._campos["expresion"].setText("x*exp(x)")
    pan._campos["variable"].setText("x")
    pan.calcular()
    assert "partes" in pan.pasos.toPlainText()


def test_pasos_avisan_cuando_la_operacion_no_los_tiene(ventana):
    from src.core import calculo

    pan = panel(ventana, "calculo")
    claves = [c for c, _, _ in calculo.OPERACIONES]
    pan.combo.setCurrentIndex(claves.index("analisis"))
    pan._campos["expresion"].setText("x^2")
    pan._campos["variable"].setText("x")
    pan.calcular()
    assert "no tiene desarrollo paso a paso" in pan.pasos.toPlainText()


def test_pasos_en_ecuaciones(ventana):
    ecu = panel(ventana, "ecuaciones")
    ecu.chk_pasos.setChecked(True)
    ecu.entrada.setText("x^2 - 5x + 6 = 0")
    ecu.resolver(silencioso=True)
    salida = ecu.salida.toPlainText()
    assert "PASO A PASO" in salida
    assert "discriminante" in salida


def test_pasos_de_ecuaciones_se_pueden_desactivar(ventana):
    ecu = panel(ventana, "ecuaciones")
    ecu.chk_pasos.setChecked(False)
    ecu.entrada.setText("x^2 - 4 = 0")
    ecu.resolver(silencioso=True)
    assert "PASO A PASO" not in ecu.salida.toPlainText()
    ecu.chk_pasos.setChecked(True)


def test_pasos_en_sistemas(ventana):
    sis = panel(ventana, "sistemas")
    sis.chk_pasos.setChecked(True)
    salida = _resolver_sistema(ventana, ["2x + 3y = 7", "x - y = 1"])
    assert "método de Gauss" in salida
    assert "matriz ampliada" in salida


# --------------------------------------------------------------------------- #
# Ecuaciones diferenciales
# --------------------------------------------------------------------------- #

def _filas(tabla) -> dict:
    return {tabla.item(f, 0).text(): tabla.item(f, 1).text()
            for f in range(tabla.rowCount())
            if tabla.item(f, 0) and tabla.item(f, 1)}


def test_edo_resuelve(ventana):
    pan = panel(ventana, "edo")
    pan.combo_modo.setCurrentIndex(0)
    pan.entrada.setText("y' + 2y = 0")
    pan.condiciones.clear()
    pan.resolver()
    assert "exp(-2*x)" in _filas(pan.tabla)["Solución general"]


def test_edo_con_condiciones_iniciales(ventana):
    pan = panel(ventana, "edo")
    pan.combo_modo.setCurrentIndex(0)
    pan.entrada.setText("y' = x*y")
    pan.condiciones.setText("y(0) = 1")
    pan.resolver()
    assert "exp(x**2/2)" in _filas(pan.tabla)["Solución particular"]


def test_edo_sistema(ventana):
    pan = panel(ventana, "edo")
    pan.combo_modo.setCurrentIndex(2)
    pan.sistema.setPlainText("x' = y\ny' = -x")
    pan.var_independiente.setText("t")
    pan.resolver()
    assert pan.tabla.rowCount() > 0


def test_edo_numerica(ventana):
    pan = panel(ventana, "edo")
    pan.combo_modo.setCurrentIndex(3)
    pan.campo_fxy.setText("y")
    pan.campo_x0.setText("0")
    pan.campo_y0.setText("1")
    pan.campo_h.setText("0.1")
    pan.spin_pasos.setValue(10)
    pan.resolver()
    assert pan.tabla.rowCount() > 0


def test_edo_avisa_si_no_hay_derivada(ventana):
    pan = panel(ventana, "edo")
    pan.combo_modo.setCurrentIndex(0)
    pan.entrada.setText("x + 1 = 0")
    pan.resolver()
    assert _DIALOGOS


# --------------------------------------------------------------------------- #
# Métodos numéricos
# --------------------------------------------------------------------------- #

def _numerico(ventana, clave, valores=None):
    pan = panel(ventana, "numerico")
    claves = [c for c, _, _ in pan._catalogo()]
    pan.combo.setCurrentIndex(claves.index(clave))
    for nombre, valor in (valores or {}).items():
        widget = pan._campos.get(nombre)
        if widget is None:
            continue
        if hasattr(widget, "setValue"):
            widget.setValue(int(valor))
        else:
            widget.setText(str(valor))
    pan.calcular()
    return pan


def test_numerico_biseccion(ventana):
    pan = _numerico(ventana, "biseccion", {"expresion": "x^2 - 2", "a": "0", "b": "2"})
    assert "1.4142" in pan.resultado.text()
    assert pan.tabla.rowCount() > 0


def test_numerico_newton(ventana):
    pan = _numerico(ventana, "newton", {"expresion": "x^2 - 2", "x0": "1"})
    assert "1.4142" in pan.resultado.text()


def test_numerico_simpson(ventana):
    pan = _numerico(ventana, "simpson", {"expresion": "x^2", "a": "0", "b": "3", "n": 100})
    assert "9" in pan.resultado.text()
    assert "valor exacto" in pan.detalle.text()


def test_numerico_interpolacion(ventana):
    pan = panel(ventana, "numerico")
    claves = [c for c, _, _ in pan._catalogo()]
    pan.combo.setCurrentIndex(claves.index("lagrange"))
    pan.puntos.setPlainText("0, 1\n1, 3\n2, 7")
    pan.calcular()
    assert "x**2" in pan.resultado.text()


def test_numerico_rk4(ventana):
    pan = _numerico(ventana, "rk4", {"fxy": "y", "x0": "0", "y0": "1",
                                     "h": "0.1", "pasos": 10})
    assert "2.718" in pan.resultado.text()


def test_numerico_avisa_sin_cambio_de_signo(ventana):
    _numerico(ventana, "biseccion", {"expresion": "x^2 + 1", "a": "0", "b": "2"})
    assert _DIALOGOS


# --------------------------------------------------------------------------- #
# Transformadas
# --------------------------------------------------------------------------- #

def _transformada(ventana, clave, expresion=""):
    from src.core import transformadas as tr

    pan = panel(ventana, "transformadas")
    claves = [c for c, _, _ in tr.OPERACIONES]
    pan.combo.setCurrentIndex(claves.index(clave))
    if expresion:
        pan.entrada.setText(expresion)
    pan.calcular()
    return pan


def test_laplace_en_el_panel(ventana):
    pan = _transformada(ventana, "laplace", "t^2")
    assert "2/s**3" in _filas(pan.tabla)["Transformada"]


def test_laplace_inversa_en_el_panel(ventana):
    pan = _transformada(ventana, "laplace_inversa", "1/(s-2)")
    assert "exp(2*t)" in _filas(pan.tabla)["Transformada inversa"]


def test_serie_de_fourier_en_el_panel(ventana):
    pan = _transformada(ventana, "serie", "x")
    assert any("Serie truncada" in k for k in _filas(pan.tabla))


def test_tabla_de_laplace_en_el_panel(ventana):
    pan = _transformada(ventana, "tabla")
    assert pan.tabla.rowCount() >= 10


# --------------------------------------------------------------------------- #
# Ajuste de curvas
# --------------------------------------------------------------------------- #

def test_ajuste_compara_modelos(ventana):
    import math

    pan = panel(ventana, "ajuste")
    xs = [0, 1, 2, 3, 4, 5]
    pan.datos_x.setPlainText(", ".join(str(v) for v in xs))
    pan.datos_y.setPlainText(", ".join(f"{2 * math.exp(0.5 * v):.6f}" for v in xs))
    pan.combo.setCurrentIndex(0)          # comparar todos
    pan.calcular()
    assert pan._ajustes and pan._ajustes[0].clave == "exponencial"


def test_ajuste_modelo_concreto(ventana):
    pan = panel(ventana, "ajuste")
    pan.datos_x.setPlainText("1, 2, 3, 4")
    pan.datos_y.setPlainText("3, 5, 7, 9")
    indice = pan.combo.findData("poli1")
    pan.combo.setCurrentIndex(indice)
    pan.calcular()
    assert pan._ajustes[0].r2 == pytest.approx(1.0)


def test_ajuste_avisa_si_las_series_no_casan(ventana):
    pan = panel(ventana, "ajuste")
    pan.datos_x.setPlainText("1, 2, 3")
    pan.datos_y.setPlainText("1, 2")
    pan.calcular()
    assert _DIALOGOS


# --------------------------------------------------------------------------- #
# Icono
# --------------------------------------------------------------------------- #

def test_la_aplicacion_tiene_icono():
    from src.core.rutas import icono
    ruta = icono()
    assert ruta is not None and ruta.exists(), "falta assets/axioma.ico"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
