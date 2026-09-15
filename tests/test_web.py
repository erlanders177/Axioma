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
    esperar_a_la_aplicacion(pagina)
    yield pagina
    contexto.close()


def esperar_a_la_aplicacion(pagina, con_motor: bool = True) -> None:
    """La interfaz aparece antes que el motor: son dos esperas distintas.

    Casi todas las pruebas calculan algo, así que necesitan el motor. Las que
    miden el arranque miran sólo la interfaz.
    """
    pagina.wait_for_selector("#menu-calculadora", timeout=ESPERA)
    if con_motor:
        pagina.wait_for_function("window.__motorListo === true", timeout=ESPERA)


def escribir_en_la_calculadora(pagina, texto: str) -> None:
    """Escribe en la pantalla de la calculadora.

    Con el dedo, ese campo va en sólo lectura para que el navegador no saque su
    teclado encima del que ya trae la aplicación. Quien quiera teclear pulsa el
    botón del teclado, que es justo lo que se hace aquí.
    """
    if pagina.get_attribute("#calc-entrada", "readonly") is not None:
        pagina.click("#btn-teclado")
    pagina.fill("#calc-entrada", texto)


def test_arranca_y_calcula(pagina):
    escribir_en_la_calculadora(pagina, "2*sin(30)+sqrt(16)")
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
    esperar_a_la_aplicacion(pagina)

    pagina.click("#btn-instalar")
    dialogo = pagina.text_content("#dialogo-instalar")
    assert "Descargar la aplicación de Android" in dialogo
    assert "Firefox" in dialogo and "tres puntos" in dialogo

    # Un enlace de verdad, no un botón que cambie la dirección de la página:
    # eso dejaba la aplicación en blanco mientras bajaban los 56 MB, y dentro
    # de la aplicación instalada abría una vista que ni descarga.
    descarga = pagina.locator("#dialogo-cuerpo a.accion").first
    assert descarga.get_attribute("href").endswith("Axioma.apk")
    # Sin `target`: abrirlo en otra pestaña deja una pestaña vacía que no carga
    # nada, que es exactamente lo que parece una descarga rota.
    assert descarga.get_attribute("target") is None

    # Y una salida por si la descarga directa no arranca.
    enlaces = pagina.locator("#dialogo-cuerpo a.accion")
    destinos = [enlaces.nth(i).get_attribute("href") for i in range(enlaces.count())]
    assert any(d.endswith("/releases/latest") for d in destinos), destinos
    contexto.close()


def test_el_iphone_recibe_los_pasos_de_safari(navegador, servidor):
    contexto = navegador.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                   "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    )
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina)

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
        esperar_a_la_aplicacion(pagina)
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
        esperar_a_la_aplicacion(pagina, con_motor=False)
        assert "NUEVA" in pagina.text_content("#menu-calculadora"), (
            "el navegador se quedó con la versión anterior"
        )

        # Y sin conexión sigue funcionando, que es para lo que está la caché.
        contexto.set_offline(True)
        pagina2 = contexto.new_page()
        pagina2.goto(url, wait_until="load")
        esperar_a_la_aplicacion(pagina2)
        escribir_en_la_calculadora(pagina2, "2+2")
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


def test_sigue_estando_la_verificacion_de_google():
    """Si se borra, la propiedad deja de estar verificada en Search Console.

    Es una etiqueta suelta en la cabecera, de las que se pierden sin ruido al
    reordenar el HTML, y nadie se entera hasta que hace falta.
    """
    bruto = (WEB / "index.html").read_text(encoding="utf-8")
    assert 'name="google-site-verification"' in bruto
    assert "75aCGIQ9zULCkgtBxh_g88g5E-TI-aBYwJNGNQMh63k" in bruto


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


# --------------------------------------------------------------------------- #
# Que se comporte como una aplicación y no como una instalación cada vez
# --------------------------------------------------------------------------- #

def test_la_interfaz_aparece_antes_que_el_motor(navegador, servidor):
    """Abrir la aplicación no puede costar cinco segundos de pantalla de carga.

    El motor de Python tarda unos segundos en arrancar aunque esté todo
    guardado. Antes se esperaba a que terminara con un cartel de «descargando
    Python entero», y cada apertura parecía una reinstalación. Ahora la
    calculadora se ve y se toca mientras el motor arranca por detrás.
    """
    contexto = navegador.new_context(viewport={"width": 390, "height": 844})
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="commit")

    # El teclado está puesto antes de que el motor conteste.
    pagina.wait_for_selector("#ap-calculadora .teclado button", timeout=30000)
    assert not pagina.evaluate("window.__motorListo === true"), (
        "el motor no debería estar listo tan pronto: la prueba no mide nada"
    )
    teclas = pagina.eval_on_selector_all("#ap-calculadora .teclado button", "n => n.length")
    assert teclas >= 25, teclas
    assert pagina.is_visible("#aviso-motor"), "hay que avisar de que aún se prepara"

    esperar_a_la_aplicacion(pagina)
    assert pagina.is_hidden("#aviso-motor"), "el aviso debe irse al estar listo"
    contexto.close()


def test_lo_escrito_antes_de_tiempo_no_se_pierde(navegador, servidor):
    """Si escribe mientras arranca, se le atiende en cuanto se pueda."""
    contexto = navegador.new_context(viewport={"width": 390, "height": 844})
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="commit")
    pagina.wait_for_selector("#calc-entrada", timeout=30000)

    escribir_en_la_calculadora(pagina, "2*sin(30)+sqrt(16)")
    pagina.keyboard.press("Enter")          # el motor todavía no está

    pagina.wait_for_function(
        "document.querySelector('#calc-entrada').value === '5'", timeout=ESPERA)
    contexto.close()


def test_al_volver_sigue_donde_lo_dejo(navegador, servidor):
    """Una aplicación no empieza de cero cada vez que se abre."""
    contexto = navegador.new_context(viewport={"width": 1280, "height": 800})
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina)

    pagina.click("#menu-geometria")
    pagina.select_option("#ap-geometria select", "Cilindro")
    campos = pagina.query_selector_all("#ap-geometria input[data-simbolo]")
    campos[0].fill("7 cm")
    campos[1].fill("3 cm")
    escribir_en_la_calculadora(pagina, "123+1")

    # Como cuando el móvil manda la aplicación al fondo.
    pagina.evaluate("document.dispatchEvent(new Event('visibilitychange'))")
    pagina.evaluate("""() => {
        Object.defineProperty(document, 'visibilityState', { value: 'hidden', configurable: true });
        document.dispatchEvent(new Event('visibilitychange'));
    }""")

    pagina2 = contexto.new_page()
    pagina2.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina2)

    assert pagina2.is_visible("#ap-geometria"), "debería reabrirse en Geometría"
    assert pagina2.locator("#ap-geometria select").first.input_value() == "Cilindro"
    valores = pagina2.eval_on_selector_all(
        "#ap-geometria input[data-simbolo]", "n => n.map(i => i.value)")
    assert valores[:2] == ["7 cm", "3 cm"], valores
    assert pagina2.input_value("#calc-entrada") == "123+1"
    contexto.close()


def test_sin_conexion_arranca_aunque_las_direcciones_lleven_huella(navegador, servidor):
    """Sin conexión tiene que arrancar, no quedarse en blanco.

    Las direcciones de los archivos llevan una huella del contenido
    (`app.js?v=07bd5c4b11`) y en la caché están sin ella. Sin buscar ignorando
    esa parte no se encontraban, y en su lugar se servía el index: HTML donde
    se espera JavaScript, y la aplicación en blanco justo cuando más falta
    hace, sin cobertura.
    """
    contexto = navegador.new_context(viewport={"width": 390, "height": 844})
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina)
    pagina.wait_for_function("navigator.serviceWorker.controller !== null", timeout=60000)

    contexto.set_offline(True)
    pagina2 = contexto.new_page()
    errores = []
    pagina2.on("pageerror", lambda e: errores.append(str(e)))
    pagina2.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina2, con_motor=False)

    assert not errores, errores
    apartados = pagina2.eval_on_selector_all("#menu button", "n => n.length")
    assert apartados == 7, apartados
    contexto.close()


def test_sin_conexion_funciona_entera_sin_haberla_recorrido(navegador, servidor):
    """Guardar sólo lo usado deja media aplicación muerta al quedarse sin red.

    Quien nunca abrió Ecuaciones no tenía sympy guardado, y sin cobertura se
    encontraba con que esa mitad no respondía. Ahora se guarda todo por detrás
    en cuanto arranca.
    """
    contexto = navegador.new_context(viewport={"width": 390, "height": 844})
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina)
    pagina.wait_for_function("navigator.serviceWorker.controller !== null", timeout=60000)

    # Se le da tiempo a guardar el resto; sólo se ha usado la calculadora.
    pagina.wait_for_timeout(20000)

    contexto.set_offline(True)
    pagina2 = contexto.new_page()
    pagina2.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina2)

    pagina2.click("#menu-ecuaciones")
    pagina2.fill("#ap-ecuaciones input", "x^2 - 5x + 6 = 0")
    pagina2.click("#ap-ecuaciones button.accion")
    pagina2.wait_for_function(
        "document.querySelector('#ap-ecuaciones .salida').textContent.includes('Incógnita')",
        timeout=ESPERA)
    salida = pagina2.text_content("#ap-ecuaciones .salida")
    assert "x1 = 2" in salida and "x2 = 3" in salida, salida
    contexto.close()


# --------------------------------------------------------------------------- #
# El teclado del móvil
# --------------------------------------------------------------------------- #

def test_con_el_dedo_no_sale_el_teclado_del_movil_en_la_calculadora(navegador, servidor):
    """La calculadora ya trae su teclado; el del sistema sólo lo tapa.

    Un campo de texto normal hace que el navegador saque su teclado en cuanto
    se toca, y en un móvil eso es media pantalla encima de las teclas de la
    aplicación. `readonly` es lo único que lo impide en todos los navegadores.
    """
    contexto = navegador.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina)

    assert pagina.get_attribute("#calc-entrada", "readonly") is not None
    assert pagina.get_attribute("#calc-entrada", "inputmode") == "none"

    # Y con todo, se escribe: las teclas de la aplicación siguen funcionando.
    for tecla in ("7", "+", "8"):
        pagina.click(f"#ap-calculadora .teclado button:text-is('{tecla}')")
    assert pagina.input_value("#calc-entrada") == "7+8"

    pagina.click("#ap-calculadora .teclado button.igual")
    assert pagina.input_value("#calc-entrada") == "15"
    contexto.close()


def test_el_teclado_del_movil_esta_a_un_toque_si_hace_falta(navegador, servidor):
    """Para un nombre de variable hay que poder teclear."""
    contexto = navegador.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina)

    pagina.click("#btn-teclado")
    assert pagina.get_attribute("#calc-entrada", "readonly") is None
    assert pagina.get_attribute("#calc-entrada", "inputmode") == "text"

    pagina.fill("#calc-entrada", "lado = 4")
    pagina.keyboard.press("Enter")
    pagina.wait_for_function(
        "document.querySelector('#btn-variables').textContent.includes('1')",
        timeout=30000)

    # Y se puede volver a dejarlo quieto.
    pagina.click("#btn-teclado")
    assert pagina.get_attribute("#calc-entrada", "readonly") is not None
    contexto.close()


def test_con_raton_la_calculadora_se_escribe_con_el_teclado(navegador, servidor):
    """En un ordenador no hay teclado en pantalla que tapar."""
    contexto = navegador.new_context(viewport={"width": 1280, "height": 800})
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina)

    assert pagina.get_attribute("#calc-entrada", "readonly") is None
    assert pagina.locator("#btn-teclado").count() == 0
    pagina.fill("#calc-entrada", "6*7")
    pagina.keyboard.press("Enter")
    assert pagina.input_value("#calc-entrada") == "42"
    contexto.close()


def test_con_el_teclado_abierto_se_quitan_las_pestanas(navegador, servidor):
    """Con el teclado encima, las pestañas son lo único prescindible."""
    contexto = navegador.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pagina = contexto.new_page()
    pagina.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina)

    assert pagina.is_visible("#menu")

    # Como cuando el teclado se come la mitad de abajo de la pantalla.
    pagina.evaluate("""() => {
        Object.defineProperty(window.visualViewport, 'height',
                              { value: window.innerHeight - 320, configurable: true });
        window.visualViewport.dispatchEvent(new Event('resize'));
    }""")
    assert pagina.is_hidden("#menu"), "las pestañas deberían apartarse"

    pagina.evaluate("""() => {
        Object.defineProperty(window.visualViewport, 'height',
                              { value: window.innerHeight, configurable: true });
        window.visualViewport.dispatchEvent(new Event('resize'));
    }""")
    assert pagina.is_visible("#menu"), "y volver al cerrarse"
    contexto.close()


def test_desde_la_app_instalada_se_lleva_el_enlace_al_navegador(navegador, servidor):
    """Firefox en Android no descarga archivos desde una app web instalada.

    Abre una vista incrustada que intenta cargar el APK como si fuera una
    página y se queda en blanco. Desde ahí no hay descarga posible: lo que se
    puede hacer es darle el enlace para que lo lleve al navegador de verdad.
    """
    contexto = navegador.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True,
        user_agent="Mozilla/5.0 (Android 14; Mobile; rv:130.0) Gecko/130.0 Firefox/130.0",
        permissions=["clipboard-read", "clipboard-write"],
    )
    pagina = contexto.new_page()
    # Como si estuviera instalada: sin barra de direcciones.
    pagina.add_init_script("""
        const original = window.matchMedia.bind(window);
        window.matchMedia = (consulta) => consulta.includes("display-mode: standalone")
            ? { matches: true, media: consulta, addEventListener() {}, removeEventListener() {} }
            : original(consulta);
    """)
    pagina.goto(servidor, wait_until="load")
    esperar_a_la_aplicacion(pagina)

    boton = pagina.locator("#btn-instalar")
    assert boton.is_visible(), "desde la app instalada tiene que haber puerta a la nativa"
    assert "Android" in boton.text_content()
    boton.click()

    dialogo = pagina.text_content("#dialogo-instalar")
    assert "no puede descargar" in dialogo
    assert "Copiar el enlace" in dialogo
    # Nada de enlaces directos al archivo: es lo que se queda en blanco.
    assert pagina.locator("#dialogo-cuerpo a[href$='Axioma.apk']").count() == 0
    # Y la dirección a la vista, para poder copiarla a mano.
    assert "Axioma.apk" in pagina.text_content("#dialogo-cuerpo .direccion")

    pagina.once("dialog", lambda d: d.accept())
    pagina.click("#dialogo-cuerpo button.accion:has-text('Copiar')")
    copiado = pagina.evaluate("navigator.clipboard.readText()")
    assert copiado.endswith("Axioma.apk"), copiado
    contexto.close()
