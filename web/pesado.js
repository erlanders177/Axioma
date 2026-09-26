/* Axioma web — el hilo de las cuentas pesadas.
 *
 * El paso a paso, las ecuaciones, las derivadas y las integrales necesitan
 * sympy. Cargarlo es caro: son más de 800 archivos de Python que el navegador
 * compila al importarlos, y eso lleva de 5 a 25 segundos (más en un móvil).
 * Hecho en el hilo de la pantalla, la aplicación se quedaba congelada todo ese
 * rato. Aquí, en un hilo aparte, la calculadora sigue respondiendo mientras
 * tanto.
 *
 * Es otro Python, con el mismo núcleo y el mismo puente que el de la pantalla.
 * Lo único que no comparten son las variables del usuario: viajan con cada
 * petición.
 */

"use strict";

let despachar = null;
let arranque = null;

/* sympy ya compilado, guardado de una vez para las siguientes.
 *
 * Pyodide trae sympy como código fuente y lo compila cada vez que se abre la
 * aplicación. Aquí, la primera vez se compila entero y se guarda en el
 * almacenamiento del navegador; las siguientes se lee lo guardado, que es
 * mucho más rápido. Si el navegador no deja guardar (ventana privada, sin
 * espacio), se compila cada vez, como antes: más lento, pero funciona.
 */
async function montarCompilados(py) {
  try {
    py.FS.mkdirTree("/compilado");
    py.FS.mount(py.FS.filesystems.IDBFS, {}, "/compilado");
    await new Promise((cumplir, fallar) =>
      py.FS.syncfs(true, (e) => (e ? fallar(e) : cumplir())));
    return true;
  } catch {
    return false;
  }
}

function guardarCompilados(py) {
  return new Promise((cumplir) => py.FS.syncfs(false, () => cumplir()));
}

async function arrancar(urlPyodide, version) {
  importScripts(urlPyodide);
  const py = await loadPyodide();
  const [, nucleo, conCache] = await Promise.all([
    py.loadPackage("sympy"),
    fetch("nucleo.json", { cache: "no-cache" }).then((r) => r.json()),
    montarCompilados(py),
  ]);

  const creados = new Set();
  for (const [ruta, codigo] of Object.entries(nucleo)) {
    const carpeta = ruta.includes("/") ? ruta.slice(0, ruta.lastIndexOf("/")) : "";
    if (carpeta && !creados.has(carpeta)) {
      py.FS.mkdirTree("/home/pyodide/" + carpeta);
      creados.add(carpeta);
    }
    py.FS.writeFile("/home/pyodide/" + ruta, codigo);
  }

  // `version` separa lo compilado de cada Pyodide: el de otra versión no vale.
  const recienCompilado = py.runPython(`
import sys
sys.path.insert(0, "/home/pyodide")
import puente
recien = puente.preparar_pesado(${conCache ? JSON.stringify("/compilado/" + version) : "None"})

def _despachar(nombre, variables, *args):
    puente.poner_variables(variables)
    return getattr(puente, nombre)(*args)
recien
`);
  if (conCache && recienCompilado) await guardarCompilados(py);
  return py.globals.get("_despachar");
}

self.onmessage = async (evento) => {
  const { id, tipo, funcion, args, variables } = evento.data;

  if (tipo === "arrancar") {
    arranque = arrancar(evento.data.pyodide, evento.data.version);
    try {
      despachar = await arranque;
      self.postMessage({ tipo: "listo" });
    } catch (e) {
      self.postMessage({ tipo: "fallo", error: String(e?.message || e) });
    }
    return;
  }

  let respuesta;
  try {
    const funcionPython = despachar || await arranque;
    respuesta = funcionPython(funcion, JSON.stringify(variables || {}), ...(args || []));
  } catch (e) {
    respuesta = JSON.stringify({ ok: false, error: String(e?.message || e) });
  }
  self.postMessage({ id, respuesta });
};
