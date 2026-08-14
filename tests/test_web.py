"""Pruebas de la versión web, en un navegador de verdad.

Comprueban lo que de nada sirve suponer: que Pyodide arranca, que el núcleo
Python responde dentro del navegador y que **da los mismos resultados** que la
versión de escritorio. Un cilindro de radio 5 cm y altura 50 mm tiene que dar
392.699 cm³ en los dos sitios o hay dos calculadoras distintas.

Se saltan solas si no está instalado Playwright, para que quien clone el
repositorio no se encuentre con fallos por una herramienta que no pidió.

    pip install playwright && playwright install chromium
    python -m pytest tests/test_web.py
"""

from __future__ import annotations

import contextlib
import pathlib
import socket
import subprocess
import sys
import time

import pytest

playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="hace falta playwright para probar la web"
)

RAIZ = pathlib.Path(__file__).resolve().parent.parent
WEB = RAIZ / "web"
#: Pyodide se descarga de un CDN la primera vez; en una conexión lenta tarda.
ESPERA = 180_000


def _puerto_libre() -> int:
    with contextlib.closing(socket.socket()) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def servidor():
    """Sirve `web/` por HTTP: con file:// no funcionan ni fetch ni el worker."""
    puerto = _puerto_libre()
    proceso = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(puerto), "-d", str(WEB)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    try:
        yield f"http://127.0.0.1:{puerto}/"
    finally:
        proceso.terminate()
        proceso.wait(timeout=10)


@pytest.fixture(scope="module")
def navegador():
    with playwright_api.sync_playwright() as p:
        try:
            instancia = p.chromium.launch()
        except Exception as e:                                  # noqa: BLE001
            pytest.skip(f"no hay Chromium instalado para Playwright: {e}")
        yield instancia
        instancia.close()


@pytest.fixture(params=[("movil", 390, 844, True), ("escritorio", 1280, 800, False)],
                ids=["movil", "escritorio"])
def pagina(request, navegador, servidor):
    """La misma aplicación en un teléfono y en un ordenador."""
    _, ancho, alto, movil = request.param
    contexto = navegador.new_context(
        viewport={"width": ancho, "height": alto}, is_mobile=movil, has_touch=movil,
    )
    pagina = contexto.new_page()
    pagina.errores = []                                          # type: ignore[attr-defined]
    pagina.on("pageerror", lambda e: pagina.errores.append(str(e)))
    pagina.goto(servidor, wait_until="load")
    pagina.wait_for_selector("#menu-calculadora", timeout=ESPERA)
    yield pagina
    contexto.close()


def test_arranca_y_calcula(pagina):
    pagina.fill("#calc-entrada", "2*sin(30)+sqrt(16)")
    pagina.keyboard.press("Enter")
    assert pagina.input_value("#calc-entrada") == "5"


def test_la_barra_opera_con_unidades(pagina):
    pagina.fill("#barra-entrada", "3 km + 200 m")
    pagina.keyboard.press("Enter")
    assert "3.2 km" in pagina.text_content("#barra-resultado")


def test_geometria_mezcla_unidades_igual_que_el_escritorio(pagina):
    pagina.click("#menu-geometria")
    pagina.select_option("#ap-geometria select", "Cilindro")
    campos = pagina.query_selector_all("#ap-geometria input[data-simbolo]")
    campos[0].fill("5 cm")
    campos[1].fill("50 mm")
    pagina.click("#ap-geometria button.accion")
    assert "392.699 cm³" in pagina.text_content("#ap-geometria .resultados")


def test_resuelve_ecuaciones(pagina):
    pagina.click("#menu-ecuaciones")
    pagina.fill("#ap-ecuaciones input", "x^2 - 5x + 6 = 0")
    pagina.click("#ap-ecuaciones button.accion")
    pagina.wait_for_function(
        "document.querySelector('#ap-ecuaciones .salida').textContent.includes('Incógnita')",
        timeout=ESPERA,
    )
    salida = pagina.text_content("#ap-ecuaciones .salida")
    assert "x1 = 2" in salida and "x2 = 3" in salida


def test_deriva(pagina):
    pagina.click("#menu-calculo")
    pagina.fill("#ap-calculo input", "x^3")
    pagina.click("#ap-calculo button.accion")
    pagina.wait_for_function(
        "document.querySelector('#ap-calculo .resultados').children.length > 0",
        timeout=ESPERA,
    )
    assert "3*x**2" in pagina.text_content("#ap-calculo .resultados")


def test_combinatoria(pagina):
    pagina.click("#menu-combinatoria")
    # De partida muestra el factorial: 10! = 3 628 800.
    assert "3628800" in pagina.text_content("#ap-combinatoria .salida")

    pagina.select_option("#ap-combinatoria select", "combinaciones")
    assert "210" in pagina.text_content("#ap-combinatoria .salida")   # C(10,4)


def test_bases(pagina):
    pagina.click("#menu-bases")
    assert "11111111" in pagina.text_content("#ap-bases .resultados")  # 255 en binario


def test_el_movil_muestra_un_apartado_y_el_ordenador_varios(pagina):
    pagina.click("#menu-geometria")
    pagina.click("#menu-ecuaciones")
    visibles = pagina.eval_on_selector_all(
        ".apartado", "nodos => nodos.filter(n => !n.classList.contains('oculto')).length"
    )
    if pagina.viewport_size["width"] < 860:
        assert visibles == 1, "en un teléfono no caben dos a la vez"
    else:
        assert visibles >= 2, "en un ordenador sí caben varios"


def test_el_resultado_de_un_apartado_sirve_en_otro(pagina):
    """Guardar el volumen en Geometría y usarlo en la barra."""
    pagina.click("#menu-geometria")
    pagina.select_option("#ap-geometria select", "Cilindro")
    campos = pagina.query_selector_all("#ap-geometria input[data-simbolo]")
    campos[0].fill("5")
    campos[1].fill("5")
    pagina.click("#ap-geometria button.accion")

    pagina.once("dialog", lambda d: d.accept("volumen"))
    pagina.click("#ap-geometria .resultados .fila-res")

    pagina.fill("#barra-entrada", "volumen / 2")
    pagina.keyboard.press("Enter")
    assert "196.35" in pagina.text_content("#barra-resultado")


def test_no_hay_errores_de_javascript(pagina):
    pagina.click("#menu-conversiones")
    pagina.wait_for_timeout(300)
    assert not pagina.errores, pagina.errores


def test_el_aviso_de_instalacion_se_escucha_desde_el_principio(pagina):
    """El navegador avisa al cargar; si se escucha tarde, se pierde.

    Ese aviso (`beforeinstallprompt`) es lo único que permite instalar con un
    toque en lugar de mandar al usuario a rebuscar por los menús. Llegaba antes
    de que el motor de cálculo terminara de cargar, así que el detector tiene
    que estar puesto desde la primera línea de la página.
    """
    assert pagina.evaluate("'__peticionInstalacion' in window"), (
        "el detector no está registrado: se perdería el aviso del navegador"
    )
    # Y el registro ocurre en el HTML, antes de cargar app.js.
    html = pagina.content()
    assert html.index("beforeinstallprompt") < html.index("app.js")


def test_si_no_hay_instalacion_automatica_se_ofrece_el_apk(pagina):
    """En un navegador sin instalación nativa, «Instalar» lleva al APK."""
    pagina.on("dialog", lambda d: d.accept())          # acepta el «¿descargar?»
    with pagina.expect_download(timeout=30000) as descarga:
        pagina.click("#btn-instalar")
    # La URL final no es la de GitHub: redirige a su almacén de descargas, así
    # que lo que identifica el archivo es el nombre que llega, no la dirección.
    assert descarga.value.suggested_filename == "Axioma.apk"
