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
const CACHE = "axioma-v3";

const PROPIOS = [
  "./", "./index.html", "./estilo.css", "./app.js",
  "./nucleo.json", "./manifest.webmanifest",
  "./icono.svg", "./icono-192.png", "./icono-512.png",
  "./icono-maskable-512.png", "./apple-touch-icon.png",
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
        .catch(() => caches.match(peticion, { ignoreVary: true })
          .then((guardado) => guardado || caches.match("./index.html")))
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
