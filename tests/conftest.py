"""Las pruebas nunca tocan los datos de verdad del usuario.

La aplicación guarda historial y preferencias en %APPDATA%/Axioma (o en
~/.local/share/Axioma). Antes cada archivo de pruebas ponía una carpeta
temporal con ``os.environ.setdefault``, que en Windows no hace nada: APPDATA
siempre existe. Así, pasar las pruebas en el ordenador de quien usa Axioma le
llenaba el historial de cuentas de prueba y le cambiaba las preferencias.

Aquí se pone una carpeta temporal **siempre**, antes de que se importe nada de
la aplicación (conftest.py se carga el primero).
"""

import os
import tempfile

_TEMPORAL = tempfile.mkdtemp(prefix="axioma_pruebas_")
os.environ["APPDATA"] = _TEMPORAL
os.environ["XDG_DATA_HOME"] = _TEMPORAL
