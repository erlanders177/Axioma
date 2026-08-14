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

import json
import pathlib
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
