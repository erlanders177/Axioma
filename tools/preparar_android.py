"""Copia el núcleo y el puente dentro de la aplicación de Android.

La app es nativa, pero la matemática es la misma: dentro corre `src/core` con
un intérprete de Python empotrado. Aquí se copia tal cual, sin tocar una línea,
igual que `preparar_web.py` hace su copia para el navegador.

El puente (`web/puente.py`) también se reutiliza: ya traduce entre el núcleo y
una interfaz cualquiera devolviendo JSON, que es justo lo que hace falta.

Uso:
    python tools/preparar_android.py
"""

from __future__ import annotations

import pathlib
import shutil
import sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
NUCLEO = RAIZ / "src" / "core"
PUENTE = RAIZ / "web" / "puente.py"
DESTINO = RAIZ / "android" / "app" / "src" / "main" / "python"

#: El mismo nombre que en la web, para que el puente valga sin cambios.
PAQUETE = "axioma_nucleo"


def preparar() -> list[str]:
    """Deja el destino como debe estar y devuelve lo que ha copiado."""
    paquete = DESTINO / PAQUETE
    if paquete.exists():
        shutil.rmtree(paquete)
    paquete.mkdir(parents=True, exist_ok=True)

    copiados = []
    for ruta in sorted(NUCLEO.glob("*.py")):
        shutil.copy2(ruta, paquete / ruta.name)
        copiados.append(f"{PAQUETE}/{ruta.name}")

    shutil.copy2(PUENTE, DESTINO / "puente.py")
    copiados.append("puente.py")
    return copiados


def main() -> int:
    if not NUCLEO.exists() or not PUENTE.exists():
        print("Falta src/core o web/puente.py", file=sys.stderr)
        return 1
    copiados = preparar()
    print(f"{DESTINO.relative_to(RAIZ)}: {len(copiados)} archivos")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
