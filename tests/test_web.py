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
def playwright():
    """Uno solo para todo el módulo: anidar `sync_playwright` da error."""
    with playwright_api.sync_playwright() as instancia:
        yield instancia


@pytest.fixture(scope="module")
def navegador(playwright):
    try:
        instancia = playwright.chromium.launch()
    except Exception as e:                                      # noqa: BLE001
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


def test_el_boton_instalar_siempre_ofrece_alguna_via(pagina):
    """Pulsar «Instalar» nunca puede acabar en un callejón sin salida."""
    pagina.click("#btn-instalar")
    dialogo = pagina.locator("#dialogo-instalar")
    assert dialogo.is_visible()
    texto = dialogo.text_content()
    assert any(pista in texto for pista in
               ("Instalar ahora", "APK", "menú", "Compartir")), texto


# --------------------------------------------------------------------------- #
# Instalarla desde cualquier navegador
# --------------------------------------------------------------------------- #

def test_firefox_de_android_ofrece_el_apk_y_los_pasos(navegador, servidor):
    """Firefox no implementa la instalación de un toque.

    No es algo que se pueda arreglar desde la página, así que lo que toca es
    ofrecer lo que sí funciona ahí: el APK, que en Android vale para cualquier
    navegador, y la ruta exacta del menú de Firefox.
    """
    contexto = navegador.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
        user_agent="Mozilla/5.0 (Android 14; Mobile; rv:130.0) Gecko/130.0 Firefox/130.0",
    )
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="load")
    pagina.wait_for_selector("#menu-calculadora", timeout=ESPERA)

    pagina.click("#btn-instalar")
    dialogo = pagina.text_content("#dialogo-instalar")
    assert "Descargar la aplicación (APK)" in dialogo
    assert "Firefox" in dialogo and "tres puntos" in dialogo

    # Se intercepta la descarga en vez de bajar el APK de verdad: son megas por
    # internet en cada ejecución, y lo que se comprueba es a dónde apunta.
    pedidas = []
    contexto.route("**/Axioma.apk*", lambda ruta: (
        pedidas.append(ruta.request.url), ruta.abort()))
    pagina.click("#dialogo-cuerpo button.accion")
    pagina.wait_for_timeout(1500)
    assert pedidas and pedidas[0].endswith("Axioma.apk"), pedidas
    contexto.close()


def test_el_iphone_recibe_los_pasos_de_safari(navegador, servidor):
    contexto = navegador.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    )
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="load")
    pagina.wait_for_selector("#menu-calculadora", timeout=ESPERA)

    pagina.click("#btn-instalar")
    dialogo = pagina.text_content("#dialogo-instalar")
    assert "Compartir" in dialogo and "pantalla de inicio" in dialogo
    # En un iPhone no se ofrece el APK, que no serviría de nada.
    assert "APK" not in dialogo
    contexto.close()


def test_firefox_real_muestra_el_dialogo(playwright, servidor):
    """Con el Firefox de verdad, no sólo con su identificación."""
    try:
        navegador = playwright.firefox.launch()
    except Exception as e:                                   # noqa: BLE001
        pytest.skip(f"no hay Firefox para Playwright: {e}")
    pagina = navegador.new_page(viewport={"width": 390, "height": 844})
    pagina.goto(servidor, wait_until="load")
    pagina.wait_for_selector("#menu-calculadora", timeout=ESPERA)
    assert pagina.is_visible("#btn-instalar")
    pagina.click("#btn-instalar")
    assert pagina.is_visible("#dialogo-instalar")
    assert pagina.text_content("#dialogo-instalar").strip()
    navegador.close()


# --------------------------------------------------------------------------- #
# Que una versión nueva llegue de verdad
# --------------------------------------------------------------------------- #

def _marcar_versiones_en(carpeta: pathlib.Path) -> None:
    """Repite sobre una copia lo que hace tools/preparar_web.py al publicar."""
    import hashlib
    import re

    indice = carpeta / "index.html"
    texto = indice.read_text(encoding="utf-8")
    for nombre in ("app.js", "estilo.css"):
        huella = hashlib.sha256((carpeta / nombre).read_bytes()).hexdigest()[:10]
        patron = re.compile(r'((?:src|href)=")' + re.escape(nombre)
                            + r'(?:\?v=[0-9a-f]+)?(")')
        texto = patron.sub(rf'\g<1>{nombre}?v={huella}\g<2>', texto)
    indice.write_text(texto, encoding="utf-8")


def test_una_version_nueva_llega_al_navegador(playwright, tmp_path_factory):
    """Publicar un arreglo no sirve de nada si el móvil sigue con lo viejo.

    Es lo que pasaba: el service worker servía la copia guardada de todo, HTML
    y JavaScript incluidos, así que la aplicación se quedaba congelada en la
    primera versión visitada por muchas veces que se recargara.
    """
    import shutil

    copia = tmp_path_factory.mktemp("web")
    shutil.copytree(WEB, copia / "web")
    servida = copia / "web"

    puerto = _puerto_libre()
    proceso = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(puerto), "-d", str(servida)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    url = f"http://127.0.0.1:{puerto}/"
    navegador = playwright.chromium.launch()
    try:
        contexto = navegador.new_context(viewport={"width": 390, "height": 844})
        pagina = contexto.new_page()
        pagina.goto(url, wait_until="load")
        pagina.wait_for_selector("#menu-calculadora", timeout=ESPERA)
        pagina.wait_for_function("navigator.serviceWorker.controller !== null",
                                 timeout=60000)
        assert "Calculadora" in pagina.text_content("#menu-calculadora")

        # Se publica una versión nueva mientras el navegador ya tiene la vieja.
        # Como al publicar de verdad: se cambia el código y se reempaqueta, que
        # es lo que renueva la huella de la dirección.
        app = servida / "app.js"
        app.write_text(
            app.read_text(encoding="utf-8").replace(
                'titulo: "Calculadora"', 'titulo: "Calculadora NUEVA"', 1),
            encoding="utf-8")
        _marcar_versiones_en(servida)

        pagina.reload(wait_until="load")
        pagina.wait_for_selector("#menu-calculadora", timeout=ESPERA)
        assert "NUEVA" in pagina.text_content("#menu-calculadora"), (
            "el navegador se quedó con la versión anterior"
        )

        # Y sin conexión sigue funcionando, que es para lo que está la caché.
        contexto.set_offline(True)
        pagina2 = contexto.new_page()
        pagina2.goto(url, wait_until="load")
        pagina2.wait_for_selector("#menu-calculadora", timeout=ESPERA)
        pagina2.fill("#calc-entrada", "2+2")
        pagina2.keyboard.press("Enter")
        assert pagina2.input_value("#calc-entrada") == "4"
    finally:
        navegador.close()
        proceso.terminate()


# --------------------------------------------------------------------------- #
# Que se pueda encontrar buscando, no sólo con el enlace exacto
# --------------------------------------------------------------------------- #

def test_la_pagina_dice_de_que_va_sin_ejecutar_javascript():
    """Un buscador lee el HTML tal cual llega, sin montar la aplicación.

    La interfaz se dibuja con JavaScript, así que si el HTML no cuenta nada,
    para Google esto es una página en blanco y no la enseña a nadie.
    """
    import html as htmlib
    import json
    import re

    bruto = (WEB / "index.html").read_text(encoding="utf-8")

    titulo = re.search(r"<title>(.*?)</title>", bruto, re.S).group(1)
    assert "alculadora" in titulo and len(titulo) > 25, titulo

    descripcion = re.search(r'name="description" content="(.*?)"', bruto).group(1)
    assert 60 < len(descripcion) < 300, f"descripción de {len(descripcion)} caracteres"

    # Texto legible: se quitan los scripts y las etiquetas, como haría un robot.
    visible = re.sub(r"<script.*?</script>", " ", bruto, flags=re.S)
    visible = htmlib.unescape(re.sub(r"<[^>]+>", " ", visible))
    palabras = len(visible.split())
    assert palabras > 90, f"sólo {palabras} palabras legibles sin JavaScript"
    for termino in ("Geometría", "Ecuaciones", "Conversiones", "instalar"):
        assert termino in visible, f"falta «{termino}» en el texto legible"

    # Ficha para compartir y para el buscador.
    for etiqueta in ("og:title", "og:description", "og:image", "og:url"):
        assert f'property="{etiqueta}"' in bruto, etiqueta
    assert 'rel="canonical"' in bruto

    datos = json.loads(re.search(r'application/ld\+json">(.*?)</script>', bruto, re.S).group(1))
    assert datos["@type"] == "SoftwareApplication"
    assert datos["name"] == "Axioma"


def test_hay_robots_y_sitemap():
    robots = (WEB / "robots.txt").read_text(encoding="utf-8")
    assert "Sitemap:" in robots and "Allow: /" in robots

    mapa = (WEB / "sitemap.xml").read_text(encoding="utf-8")
    # Con el namespace mal escrito, los buscadores descartan el archivo entero.
    assert "http://www.sitemaps.org/schemas/sitemap/0.9" in mapa
    assert "https://erlanders177.github.io/Axioma/" in mapa


def test_la_imagen_para_compartir_tiene_la_medida_que_esperan():
    from PIL import Image

    with Image.open(WEB / "social.png") as imagen:
        assert imagen.size == (1200, 630), imagen.size
