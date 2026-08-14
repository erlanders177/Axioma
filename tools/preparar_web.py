"""Empaqueta ``src/core`` para que el navegador pueda cargarlo.

La versión web ejecuta **el mismo código** que la de escritorio: Pyodide es
Python compilado a WebAssembly, así que el núcleo se copia dentro del navegador
tal cual y allí se importa. Nada de reescribir la matemática en JavaScript, que
es como se acaba con dos calculadoras que no dan el mismo resultado.

El resultado es ``web/nucleo.json``: un solo archivo con el texto de cada
módulo. Se prefiere JSON a un .zip porque se lee en el repositorio, se compara
en un diff y no exige descomprimir nada en el navegador.

Uso:
    python tools/preparar_web.py
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
NUCLEO = RAIZ / "src" / "core"
DESTINO = RAIZ / "web" / "nucleo.json"

#: El puente vive en `web/` pero se ejecuta dentro de Pyodide, así que viaja
#: con el núcleo.
EXTRA = {"puente.py": RAIZ / "web" / "puente.py"}


#: El núcleo viaja como **paquete**, no como archivos sueltos: usa importaciones
#: relativas (`from . import unidades`) y aplanarlo obligaría a reescribirlo.
#: Así el código que corre en el navegador es idéntico al del escritorio.
PAQUETE = "axioma_nucleo"


def recopilar() -> dict[str, str]:
    """Ruta dentro del navegador -> código fuente, en orden estable."""
    modulos = {
        f"{PAQUETE}/{ruta.name}": ruta.read_text(encoding="utf-8")
        for ruta in sorted(NUCLEO.glob("*.py"))
    }
    for nombre, ruta in EXTRA.items():
        if ruta.exists():
            modulos[nombre] = ruta.read_text(encoding="utf-8")
    return modulos


#: Archivos cuya dirección se marca con una huella de su contenido.
#:
#: Sin esto, el navegador sirve su propia copia guardada durante minutos y una
#: corrección publicada no llega: ni siquiera llega a preguntar al service
#: worker. Al cambiar el contenido cambia la dirección, y entonces no le queda
#: más remedio que descargarla.
VERSIONADOS = ("app.js", "estilo.css", "nucleo.json")


def _huella(ruta: pathlib.Path) -> str:
    return hashlib.sha256(ruta.read_bytes()).hexdigest()[:10]


def marcar_versiones() -> list[str]:
    """Pone «?v=huella» en las referencias del index. Devuelve lo que cambió."""
    indice = RAIZ / "web" / "index.html"
    texto = indice.read_text(encoding="utf-8")
    cambios = []

    for nombre in VERSIONADOS:
        archivo = RAIZ / "web" / nombre
        if not archivo.exists():
            continue
        huella = _huella(archivo)
        # Sólo en los atributos que cargan el archivo: si se busca el nombre
        # suelto, también se marca cuando aparece dentro de un comentario.
        patron = re.compile(
            r'((?:src|href)=")' + re.escape(nombre) + r'(?:\?v=[0-9a-f]+)?(")'
        )
        nuevo, cuantos = patron.subn(rf"\g<1>{nombre}?v={huella}\g<2>", texto)
        if cuantos and nuevo != texto:
            cambios.append(f"{nombre} -> {huella}")
        texto = nuevo

    indice.write_text(texto, encoding="utf-8")
    return cambios


def main() -> int:
    modulos = recopilar()
    if not modulos:
        print("No se encontró ningún módulo en src/core", file=sys.stderr)
        return 1

    DESTINO.parent.mkdir(parents=True, exist_ok=True)
    DESTINO.write_text(
        json.dumps(modulos, ensure_ascii=False, indent=1, sort_keys=True),
        encoding="utf-8",
    )
    peso = DESTINO.stat().st_size / 1024
    print(f"{DESTINO.relative_to(RAIZ)}: {len(modulos)} módulos, {peso:.0f} KB")

    for cambio in marcar_versiones():
        print(f"  {cambio}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
