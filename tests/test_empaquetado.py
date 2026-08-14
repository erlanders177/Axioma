"""Comprobaciones sobre la receta de PyInstaller (``Axioma.spec``).

Empaquetar es lento (varios minutos) y el fallo típico no aparece hasta que se
ejecuta el `.exe` en otro ordenador. Estas pruebas detectan en segundos los dos
errores que de verdad ocurren:

* excluir un módulo que la aplicación sí necesita (le pasó a Pillow: parecía que
  sólo lo usaba el generador del icono, pero ``matplotlib.colors`` lo importa al
  cargarse, y el ejecutable no llegaba a abrir la ventana);
* referenciar en `datas` un archivo que no existe.
"""

from __future__ import annotations

import ast
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SPEC = RAIZ / "Axioma.spec"

#: Se excluyen del ejecutable pero las pruebas sí las necesitan.
HERRAMIENTAS_DE_DESARROLLO = {
    "pytest", "IPython", "notebook", "jupyter", "jupyter_client",
    "ipykernel", "nbconvert", "nbformat",
}


def _valor_del_spec(clave: str):
    arbol = ast.parse(SPEC.read_text(encoding="utf-8"))
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.keyword) and nodo.arg == clave:
            return ast.literal_eval(nodo.value)
    return None


def test_el_spec_se_puede_analizar():
    assert SPEC.exists(), "falta Axioma.spec"
    assert _valor_del_spec("excludes"), "el spec no declara exclusiones"


def test_los_archivos_de_datas_existen():
    """Si una ruta de `datas` no existe, PyInstaller falla al empaquetar."""
    for origen, _destino in _valor_del_spec("datas") or []:
        assert (RAIZ / origen).exists(), f"datas apunta a un archivo inexistente: {origen}"


def test_el_icono_del_spec_existe():
    contenido = SPEC.read_text(encoding="utf-8")
    for linea in contenido.splitlines():
        if linea.strip().startswith("icon="):
            ruta = linea.split("=", 1)[1].strip().strip("',\"")
            assert (RAIZ / ruta).exists(), f"el icono del spec no existe: {ruta}"
            return
    pytest.skip("el spec no define icono")


def test_ningun_modulo_excluido_hace_falta_en_ejecucion():
    """Importa toda la interfaz con los módulos excluidos bloqueados.

    Se hace en un subproceso porque bloquear importaciones envenena el
    intérprete para el resto de la sesión de pruebas.
    """
    excluidos = {
        modulo for modulo in _valor_del_spec("excludes")
        if not modulo.startswith("PyQt5.")
    } - HERRAMIENTAS_DE_DESARROLLO

    guion = f"""
import importlib.abc, sys

BLOQUEADOS = {sorted(excluidos)!r}
culpables = set()

class Bloqueador(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        raiz = fullname.split(".")[0]
        if raiz in BLOQUEADOS:
            culpables.add(raiz)
            raise ImportError(fullname)
        return None

sys.meta_path.insert(0, Bloqueador())
sys.path.insert(0, {str(RAIZ)!r})

try:
    # Importar la ventana principal arrastra los doce paneles y, con ellos,
    # todo lo que la aplicación necesita para arrancar.
    import src.ui.ventana_principal  # noqa: F401
except ImportError as e:
    print("FALTA:" + ",".join(sorted(culpables)) + "|" + str(e))
    sys.exit(1)
print("OK")
"""

    entorno = dict(os.environ)
    entorno["QT_QPA_PLATFORM"] = "offscreen"
    entorno.setdefault("APPDATA", tempfile.mkdtemp(prefix="axioma_spec_"))

    resultado = subprocess.run(
        [sys.executable, "-c", guion],
        capture_output=True, text=True, env=entorno, timeout=300,
    )

    salida = (resultado.stdout + resultado.stderr).strip()
    assert resultado.returncode == 0, (
        "El .spec excluye módulos que la aplicación necesita para arrancar.\n"
        "Quítelos de `excludes` o el ejecutable no abrirá.\n\n" + salida
    )
    assert "OK" in resultado.stdout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))


# --------------------------------------------------------------------------- #
# La versión web lleva una copia del núcleo: no puede quedarse vieja
# --------------------------------------------------------------------------- #

def test_el_nucleo_de_la_web_esta_al_dia():
    """`web/nucleo.json` debe coincidir con `src/core`.

    La web ejecuta el mismo núcleo que el escritorio, pero copiado en un JSON
    que se genera a mano con `python tools/preparar_web.py`. Sin esta prueba,
    un arreglo en el núcleo saldría en Windows y no en el móvil, que es la peor
    clase de fallo: dos calculadoras que no dan lo mismo.
    """
    import json
    import sys

    raiz = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(raiz))
    from tools.preparar_web import recopilar

    archivo = raiz / "web" / "nucleo.json"
    assert archivo.exists(), "falta web/nucleo.json: ejecute python tools/preparar_web.py"

    guardado = json.loads(archivo.read_text(encoding="utf-8"))
    actual = recopilar()

    faltan = sorted(set(actual) - set(guardado))
    sobran = sorted(set(guardado) - set(actual))
    distintos = sorted(n for n in set(actual) & set(guardado) if actual[n] != guardado[n])

    assert not (faltan or sobran or distintos), (
        "web/nucleo.json no coincide con el código: ejecute "
        "«python tools/preparar_web.py».\n"
        f"  faltan: {faltan}\n  sobran: {sobran}\n  distintos: {distintos}"
    )
