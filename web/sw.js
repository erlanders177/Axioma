/* Service worker: lo que hace que Axioma funcione sin conexión.
 *
 * La primera visita descarga Python entero (unos megas). A partir de ahí sale
 * de la caché, así que abre igual de rápido en el metro que en casa.
 *
 * Hay dos formas de tratar los archivos, y confundirlas cuesta caro:
 *
 * - **La aplicación** (HTML, JavaScript, estilos, el núcleo): se pide **a la
 *   red primero**, y sólo se tira de la copia guardada si no hay conexión. Con
 *   la regla contraria, un arreglo publicado no llegaba nunca al móvil: el
 *   navegador seguía sirviendo la copia vieja para siempre, y desde fuera se ve
 *   como una aplicación que no cambia por mucho que se recargue.
 *
 * - **Lo que no cambia nunca** (Pyodide, que viene con la versión en la
 *   dirección, y los iconos): la copia guardada, que para eso está. Son megas
 *   que no tiene sentido volver a bajar.
 */

//: Al subirlo se descarta la caché anterior entera. Media aplicación vieja y
//: media nueva es peor que volver a descargar.
const CACHE = "axioma-v6";

const PROPIOS = [
  "./", "./index.html", "./estilo.css", "./app.js",
  "./nucleo.json", "./manifest.webmanifest",
  "./icono.svg", "./icono-192.png", "./icono-512.png",
  "./icono-maskable-512.png", "./apple-touch-icon.png", "./social.png",
];

/** ¿Es un archivo de la aplicación, de los que cambian al publicar? */
function esDeLaAplicacion(url) {
  if (url.origin !== self.location.origin) return false;      // Pyodide, CDN…
  return /\.(html|js|css|json|webmanifest)$/.test(url.pathname) ||
         url.pathname.endsWith("/");
}

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(CACHE)
      .then((cache) => cache.addAll(PROPIOS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(
        claves.filter((c) => c !== CACHE).map((c) => caches.delete(c))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (evento) => {
  const peticion = evento.request;
  if (peticion.method !== "GET") return;
  const url = new URL(peticion.url);

  if (esDeLaAplicacion(url)) {
    evento.respondWith(
      // `no-store`: sin esto la petición aún puede resolverse contra la caché
      // HTTP del navegador, que guarda por su cuenta, y volvería la copia vieja
      // por la puerta de atrás. Aquí se quiere lo que hay en el servidor.
      fetch(peticion, { cache: "no-store" })
        .then((respuesta) => {
          if (respuesta.ok) {
            const copia = respuesta.clone();
            caches.open(CACHE).then((cache) => cache.put(peticion, copia));
          }
          return respuesta;
        })
        // Sin conexión, lo guardado. Es justo para lo que se guardó.
        //
        // `ignoreSearch` no es un detalle: las direcciones llevan una huella
        // del contenido (`app.js?v=07bd5c4b11`) y en la caché están sin ella,
        // así que sin esto no se encuentran. Y entonces se servía el index en
        // su lugar: HTML donde se espera JavaScript, «Unexpected token <», y
        // la aplicación en blanco sin conexión.
        .catch(() => caches.match(peticion, { ignoreVary: true, ignoreSearch: true })
          .then((guardado) => {
            if (guardado) return guardado;
            // El index sólo vale para una navegación. Devolverlo donde se
            // espera un script o una hoja de estilos rompe la página entera.
            if (peticion.mode === "navigate") return caches.match("./index.html");
            return Response.error();
          }))
    );
    return;
  }

  evento.respondWith(
    caches.match(peticion, { ignoreVary: true }).then((guardado) => {
      if (guardado) return guardado;
      return fetch(peticion).then((respuesta) => {
        if (respuesta.ok && (respuesta.type === "basic" || respuesta.type === "cors")) {
          const copia = respuesta.clone();
          caches.open(CACHE).then((cache) => cache.put(peticion, copia));
        }
        return respuesta;
      });
    })
  );
});


/* --------------------------------------------------------- guardarlo todo -- */

/* Con lo anterior, Pyodide se guarda a medida que se usa. Eso deja una
 * aplicación a medias: quien nunca abrió Ecuaciones no tiene sympy, y al
 * quedarse sin cobertura se encuentra con que media calculadora no responde.
 *
 * Así que en cuanto la aplicación termina de arrancar pide guardar el resto,
 * por detrás y sin que nadie espere. A partir de ahí está entera.
 */

//: De dónde salen los archivos del motor. Lleva la versión dentro, así que
//: nunca cambia sin cambiar de dirección.
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";

//: Lo que hace falta para que Ecuaciones y Cálculo funcionen sin conexión.
//: Los nombres exactos salen de pyodide-lock.json, que ya está guardado.
const PAQUETES = ["sympy", "mpmath"];

async function guardarloTodo() {
  const cache = await caches.open(CACHE);

  const base = ["pyodide.js", "pyodide.asm.js", "pyodide.asm.wasm",
                "python_stdlib.zip", "pyodide-lock.json"];
  await Promise.all(base.map((n) => guardarSiFalta(cache, PYODIDE + n)));

  // El candado dice qué archivo corresponde a cada paquete y de qué depende.
  try {
    const respuesta = await cache.match(PYODIDE + "pyodide-lock.json") ||
                      await fetch(PYODIDE + "pyodide-lock.json");
    const candado = await respuesta.clone().json();
    const pendientes = new Set(PAQUETES);
    const archivos = new Set();
    for (const nombre of pendientes) {
      const paquete = candado.packages?.[nombre];
      if (!paquete) continue;
      archivos.add(PYODIDE + paquete.file_name);
      for (const dependencia of paquete.depends || []) pendientes.add(dependencia);
    }
    await Promise.all([...archivos].map((u) => guardarSiFalta(cache, u)));
  } catch (e) {
    // Que falle esto no rompe nada: sólo significa que sympy se descargará la
    // primera vez que se abra Ecuaciones, como hasta ahora.
  }
}

async function guardarSiFalta(cache, url) {
  if (await cache.match(url, { ignoreVary: true })) return;
  try {
    const respuesta = await fetch(url, { mode: "cors" });
    if (respuesta.ok) await cache.put(url, respuesta);
  } catch {
    /* sin conexión: ya se guardará en otra ocasión */
  }
}

self.addEventListener("message", (evento) => {
  if (evento.data?.tipo === "guardar-todo") {
    evento.waitUntil(guardarloTodo());
  }
});
