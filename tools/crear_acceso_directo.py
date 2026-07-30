"""Crea un acceso directo a Axioma en el escritorio (sólo Windows).

    python tools/crear_acceso_directo.py

Apunta al ejecutable de ``dist/`` si existe, y si no al lanzador ``Axioma.pyw``,
que arranca el código fuente sin ventana de consola. En ambos casos usa el icono
de la aplicación.

Se hace con un script en lugar de a mano para que se pueda repetir después de
recompilar, y para no depender de que el usuario sepa dónde quedó el `.exe`.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Plantilla de PowerShell: crear un `.lnk` necesita COM, y WScript.Shell está
# siempre disponible en Windows sin instalar nada.
_PLANTILLA = """
$atajo = (New-Object -ComObject WScript.Shell).CreateShortcut('{destino}')
$atajo.TargetPath       = '{objetivo}'
$atajo.Arguments        = '{argumentos}'
$atajo.WorkingDirectory = '{directorio}'
$atajo.IconLocation     = '{icono}'
$atajo.Description      = 'Axioma - calculadora cientifica multifuncion'
$atajo.Save()
"""


def _escritorio() -> Path:
    """Carpeta del escritorio, contando con que OneDrive puede redirigirla."""
    candidatos = [
        Path.home() / "OneDrive" / "Escritorio",
        Path.home() / "OneDrive" / "Desktop",
        Path.home() / "Escritorio",
        Path.home() / "Desktop",
    ]
    for candidato in candidatos:
        if candidato.is_dir():
            return candidato
    raise SystemExit("No se encontró la carpeta del escritorio")


def _objetivo() -> tuple[str, str]:
    """(programa a ejecutar, argumentos). Prefiere el .exe si está compilado."""
    ejecutable = RAIZ / "dist" / "Axioma.exe"
    if ejecutable.exists():
        return str(ejecutable), ""

    lanzador = RAIZ / "Axioma.pyw"
    if not lanzador.exists():
        raise SystemExit(
            "No hay ni dist/Axioma.exe ni Axioma.pyw. Genere el ejecutable con "
            "«pyinstaller Axioma.spec» o ejecute este script desde la raíz del "
            "proyecto."
        )

    # pythonw.exe evita la ventana de consola; python.exe la abriría.
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    interprete = pythonw if pythonw.exists() else Path(sys.executable)
    return str(interprete), f'"{lanzador}"'


def main() -> int:
    if sys.platform != "win32":
        print("Este script sólo crea accesos directos en Windows.")
        print("En Linux cree un archivo .desktop; en macOS, un alias.")
        return 1

    objetivo, argumentos = _objetivo()
    icono = RAIZ / "assets" / "axioma.ico"
    destino = _escritorio() / "Axioma.lnk"

    guion = _PLANTILLA.format(
        destino=destino,
        objetivo=objetivo,
        argumentos=argumentos.replace("'", "''"),
        directorio=RAIZ,
        icono=icono if icono.exists() else objetivo,
    )

    resultado = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", guion],
        capture_output=True, text=True,
    )
    if resultado.returncode != 0:
        print("No se pudo crear el acceso directo:")
        print(resultado.stdout, resultado.stderr)
        return 1

    print(f"Acceso directo creado en:  {destino}")
    print(f"Apunta a:                  {objetivo} {argumentos}".rstrip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
