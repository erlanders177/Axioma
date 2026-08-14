/* Service worker: lo que hace que Axioma funcione sin conexión.
 *
 * La primera visita descarga Python entero (unos megas). A partir de ahí todo
 * sale de la caché, así que la aplicación abre igual de rápido en el metro que
 * en casa. Al cambiar de versión se borra la caché anterior entera: media
 * aplicación vieja y media nueva es peor que volver a descargar.
 */

const CACHE = "axioma-v1";
const PROPIOS = [
  "./", "./index.html", "./estilo.css", "./app.js",
  "./nucleo.json", "./manifest.webmanifest", "./icono.svg",
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PROPIOS)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(claves.filter((c) => c !== CACHE).map((c) => caches.delete(c))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (evento) => {
  const peticion = evento.request;
  if (peticion.method !== "GET") return;

  // Primero la caché, y si no está se descarga y se guarda. Vale igual para lo
  // propio que para Pyodide, que viene de un CDN y es lo que más pesa.
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
