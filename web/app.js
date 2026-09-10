/* Axioma web — interfaz.
 *
 * Aquí no hay matemática: todo lo resuelve el mismo núcleo Python que usa la
 * versión de escritorio, ejecutado en el navegador con Pyodide. Este archivo
 * pinta la pantalla, recoge lo que escribe el usuario y muestra lo que
 * responde el núcleo.
 */

"use strict";

const APARTADOS = [
  { clave: "calculadora",  icono: "π",  titulo: "Calculadora" },
  { clave: "conversiones", icono: "⇄",  titulo: "Conversiones" },
  { clave: "geometria",    icono: "△",  titulo: "Geometría" },
  { clave: "ecuaciones",   icono: "ƒ",  titulo: "Ecuaciones" },
  { clave: "calculo",      icono: "∫",  titulo: "Cálculo" },
  { clave: "combinatoria", icono: "n!", titulo: "Combinatoria" },
  { clave: "bases",        icono: "01", titulo: "Bases" },
];

//: El motor de Python. La versión va en la dirección, así que el archivo
//: guardado nunca se queda viejo.
const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/pyodide.js";

//: Se muestra en la cabecera. Debe subir en cada publicación.
const VERSION = "4.3.0";

//: La aplicación de Android, adjunta a la última versión publicada. Es la
//: salida para los navegadores que no ofrecen instalación automática.
const ENLACE_APK =
  "https://github.com/erlanders177/Axioma/releases/latest/download/Axioma.apk";
//: Y la de Windows, para quien llegue desde un ordenador.
const ENLACE_EXE =
  "https://github.com/erlanders177/Axioma/releases/latest/download/Axioma.exe";

const estado = {
  py: null,
  puente: null,
  sympyCargado: false,
  listo: false,
  pendientes: [],
  fases: {},
  abiertos: new Set(["calculadora"]),
  movil: () => window.matchMedia("(max-width: 859px)").matches,
  modo: "DEG",
};

const $ = (sel) => document.querySelector(sel);
const crear = (etiqueta, clase, texto) => {
  const nodo = document.createElement(etiqueta);
  if (clase) nodo.className = clase;
  if (texto !== undefined) nodo.textContent = texto;
  return nodo;
};

/* ------------------------------------------------------------- arranque -- */

/* La interfaz se monta **antes** que el motor de cálculo.
 *
 * Antes se esperaba a Pyodide con una pantalla de carga a pantalla completa que
 * decía «descargando Python entero». Aunque no descargara nada —a partir de la
 * segunda vez sale todo de la caché— eran cinco segundos de cartel de
 * instalación cada vez que se abría la aplicación. Parecía que se reinstalaba.
 *
 * Ahora se ve la calculadora al momento y el motor arranca por detrás. Lo que
 * necesita Python espera su turno con `cuandoListo`.
 */

/** Ejecuta algo en cuanto el motor esté listo. Si ya lo está, ahora mismo. */
function cuandoListo(tarea) {
  if (estado.listo) {
    tarea();
    return;
  }
  estado.pendientes.push(tarea);
  window.__pend = estado.pendientes.length;
}

function motorListo() {
  estado.listo = true;
  // Señal para las pruebas y para quien quiera saber desde fuera si ya se
  // puede calcular: la interfaz aparece antes que el motor.
  window.__motorListo = true;
  document.dispatchEvent(new Event("axioma:motor-listo"));
  const tareas = estado.pendientes.splice(0);
  for (const tarea of tareas) {
    try {
      tarea();
    } catch (e) {
      console.error("tarea pendiente:", e);
    }
  }
  document.body.classList.remove("preparando");
  $("#aviso-motor").hidden = true;
}

function avisarDelMotor(texto, error = false) {
  const aviso = $("#aviso-motor");
  aviso.hidden = false;
  aviso.textContent = texto;
  aviso.classList.toggle("error", error);
}

async function arrancar() {
  // Lo primero, la interfaz: es lo que convierte esto en una aplicación que
  // abre al instante en lugar de en una página que se instala cada vez.
  montar();
  restaurarEstado();
  $("#cargando").classList.add("listo");
  document.body.classList.add("preparando");
  avisarDelMotor("Preparando el motor de cálculo…");

  // Que el navegador no borre lo guardado. Sin esto puede desalojar la caché
  // cuando le falte espacio, y entonces sí habría que descargarlo todo otra vez.
  asegurarAlmacenamiento();

  const lento = setTimeout(() => {
    avisarDelMotor("Está tardando más de lo normal. La primera vez son unos " +
                   "15 MB; con mala cobertura puede llevar un par de minutos.");
  }, 25000);

  try {
    const marca = (n) => { estado.fases[n] = Math.round(performance.now()); };
    await cargarElMotor();
    marca('script');
    estado.py = await loadPyodide();
    marca('pyodide');

    const nucleo = await (await fetch("nucleo.json", { cache: "no-cache" })).json();
    const creados = new Set();
    for (const [ruta, codigo] of Object.entries(nucleo)) {
      const carpeta = ruta.includes("/") ? ruta.slice(0, ruta.lastIndexOf("/")) : "";
      if (carpeta && !creados.has(carpeta)) {
        estado.py.FS.mkdirTree("/home/pyodide/" + carpeta);
        creados.add(carpeta);
      }
      estado.py.FS.writeFile("/home/pyodide/" + ruta, codigo);
    }

    // Un despachador en Python: desde JavaScript, un módulo no se puede
    // recorrer por nombre, pero una función sí se llama sin más.
    estado.py.runPython(`
import sys
sys.path.insert(0, "/home/pyodide")
import puente

def _despachar(nombre, *args):
    return getattr(puente, nombre)(*args)
`);
    estado.puente = estado.py.globals.get("_despachar");
    marca("nucleo");

    // Una cuenta de verdad antes de darlo por bueno: si el núcleo no funciona,
    // es mejor saberlo aquí que a la primera tecla del usuario.
    const prueba = JSON.parse(estado.puente("calcular", "2+2"));
    if (!prueba.ok || prueba.datos.texto !== "4") {
      throw new Error("el núcleo no devuelve resultados correctos");
    }

    marca('listo');
    window.__fases = estado.fases;
    clearTimeout(lento);
    motorListo();
    guardarloTodoDeFondo();
  } catch (e) {
    clearTimeout(lento);
    document.body.classList.remove("preparando");
    avisarDelMotor("No se pudo arrancar el motor: " + e.message + " · Toque para reintentar", true);
    $("#aviso-motor").onclick = () => location.reload();
  }
}

/** Trae el JavaScript del motor, ya con la interfaz a la vista. */
function cargarElMotor() {
  if (typeof loadPyodide === "function") return Promise.resolve();
  return new Promise((cumplir, fallar) => {
    const script = document.createElement("script");
    script.src = PYODIDE;
    script.onload = () => cumplir();
    script.onerror = () => fallar(new Error(
      "no se pudo descargar el motor de Python. Compruebe la conexión, y si " +
      "está en una red con filtros (trabajo, universidad) pruebe con los " +
      "datos del móvil: se descarga de cdn.jsdelivr.net."
    ));
    document.head.append(script);
  });
}

/** Pide que lo guardado sea permanente, para no volver a descargar nunca. */
async function asegurarAlmacenamiento() {
  try {
    if (!navigator.storage?.persist) return;
    if (await navigator.storage.persisted()) return;
    await navigator.storage.persist();
  } catch {
    // Si el navegador no lo concede, se sigue igual: sólo significa que en
    // algún apuro de espacio podría borrar la caché.
  }
}

/** Guarda el resto de la aplicación por detrás, sin que nadie espere. */
function guardarloTodoDeFondo() {
  navigator.serviceWorker?.controller?.postMessage({ tipo: "guardar-todo" });
}

/** Llama a una función del puente y devuelve el objeto ya interpretado. */
function llamar(funcion, ...args) {
  if (!estado.puente) {
    return { ok: false, esperando: true,
             error: "El motor de cálculo todavía se está preparando…" };
  }
  try {
    return JSON.parse(estado.puente(funcion, ...args));
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

/** sympy pesa varios segundos: se descarga la primera vez que hace falta. */
async function asegurarSympy() {
  if (estado.sympyCargado) return;
  await estado.py.loadPackage("sympy");
  estado.sympyCargado = true;
}

/* ----------------------------------------------------------------- menú -- */

function montar() {
  const menu = $("#menu");
  for (const ap of APARTADOS) {
    const boton = crear("button");
    boton.append(crear("span", "icono", ap.icono), crear("span", null, ap.titulo));
    boton.setAttribute("aria-pressed", estado.abiertos.has(ap.clave));
    boton.onclick = () => alternar(ap.clave);
    boton.id = "menu-" + ap.clave;
    menu.append(boton);
  }

  for (const ap of APARTADOS) construirApartado(ap);
  refrescarMenu();
  prepararBarra();
  prepararTema();
  prepararInstalacion();
  // La versión, a la vista: sin ella no hay forma de saber si el móvil está
  // usando la copia guardada de hace tres días o la de verdad.
  $("#version").textContent = "web · v" + VERSION;
}

function alternar(clave) {
  if (estado.movil()) {
    // En un teléfono cabe uno cada vez: pulsar cambia de apartado.
    estado.abiertos = new Set([clave]);
  } else if (estado.abiertos.has(clave)) {
    if (estado.abiertos.size > 1) estado.abiertos.delete(clave);
  } else {
    estado.abiertos.add(clave);
  }
  refrescarMenu();
}

function refrescarMenu() {
  for (const ap of APARTADOS) {
    const abierto = estado.abiertos.has(ap.clave);
    document.getElementById("menu-" + ap.clave)
      ?.setAttribute("aria-pressed", String(abierto));
    document.getElementById("ap-" + ap.clave)?.classList.toggle("oculto", !abierto);
  }
}

/* ----------------------------------------------------------- apartados -- */

function construirApartado(ap) {
  const seccion = crear("section", "apartado oculto");
  seccion.id = "ap-" + ap.clave;
  const titulo = crear("h2");
  titulo.append(crear("span", null, ap.titulo));
  seccion.append(titulo);

  ({
    calculadora: montarCalculadora,
    conversiones: montarConversiones,
    geometria: montarGeometria,
    ecuaciones: montarEcuaciones,
    calculo: montarCalculo,
    combinatoria: montarCombinatoria,
    bases: montarBases,
  })[ap.clave](seccion);

  seccion.append(montarHistorial(ap.clave));
  $("#lienzo").append(seccion);
}

/* ------------------------------------------------------- calculadora -- */

const TECLAS = [
  ["sin", "fn", "sin("], ["cos", "fn", "cos("], ["tan", "fn", "tan("],
  ["√", "fn", "sqrt("], ["C", "op", "#limpiar"],
  ["ln", "fn", "ln("], ["log", "fn", "log10("], ["(", "op", "("],
  [")", "op", ")"], ["⌫", "op", "#borrar"],
  ["7", "", "7"], ["8", "", "8"], ["9", "", "9"], ["÷", "op", "/"], ["^", "op", "^"],
  ["4", "", "4"], ["5", "", "5"], ["6", "", "6"], ["×", "op", "*"], ["π", "fn", "pi"],
  ["1", "", "1"], ["2", "", "2"], ["3", "", "3"], ["−", "op", "-"], ["!", "fn", "!"],
  ["0", "", "0"], [".", "", "."], ["ans", "fn", "ans"], ["+", "op", "+"], ["=", "igual", "#calcular"],
];

function montarCalculadora(seccion) {
  const pantalla = crear("div", "pantalla");
  const entrada = crear("input");
  entrada.id = "calc-entrada";
  entrada.placeholder = "0";
  entrada.autocomplete = "off";
  const previa = crear("div", "previa");
  pantalla.append(entrada, previa);

  const modo = crear("select");
  for (const m of ["DEG — grados", "RAD — radianes", "GRAD — gradianes"]) {
    modo.append(new Option(m, m.slice(0, m.indexOf(" "))));
  }
  modo.onchange = () => { estado.modo = modo.value; };

  const teclado = crear("div", "teclado");
  for (const [texto, clase, orden] of TECLAS) {
    const tecla = crear("button", clase, texto);
    tecla.type = "button";
    tecla.onclick = () => pulsar(entrada, orden, previa, "calculadora");
    teclado.append(tecla);
  }

  entrada.oninput = () => actualizarPrevia(entrada, previa);
  entrada.onkeydown = (e) => {
    if (e.key === "Enter") pulsar(entrada, "#calcular", previa, "calculadora");
  };

  seccion.append(pantalla, modo, teclado);
}

function pulsar(entrada, orden, previa, clave) {
  if (orden === "#limpiar") { entrada.value = ""; previa.textContent = ""; return; }
  if (orden === "#borrar") { entrada.value = entrada.value.slice(0, -1); }
  else if (orden === "#calcular") {
    // Se puede escribir mientras el motor arranca: el cálculo se atiende en
    // cuanto esté, en vez de perderse con un error.
    if (!estado.listo) {
      previa.textContent = "Preparando el motor…";
      cuandoListo(() => pulsar(entrada, "#calcular", previa, clave));
      return;
    }
    const r = llamar("calcular", entrada.value, estado.modo);
    if (r.ok) {
      anotar(clave, entrada.value + " = " + r.datos.texto, entrada.value);
      entrada.value = r.datos.variable ? "" : r.datos.texto;
      previa.textContent = r.datos.variable
        ? r.datos.variable + " = " + r.datos.texto : "";
      refrescarVariables();
    } else {
      previa.innerHTML = '<span class="error">' + r.error + "</span>";
    }
    return;
  } else {
    entrada.value += orden;
  }
  actualizarPrevia(entrada, previa);
  entrada.focus();
}

function actualizarPrevia(entrada, previa) {
  const r = llamar("vista_previa", entrada.value, estado.modo);
  previa.textContent = r.ok && r.datos.texto ? "= " + r.datos.texto : "";
}

/* ------------------------------------------------------- conversiones -- */

function montarConversiones(seccion) {
  const categoria = crear("select");
  // Las 51 magnitudes las enumera el núcleo, así que esta parte espera; el
  // resto del apartado ya está a la vista mientras tanto.
  cuandoListo(() => {
    const grupos = llamar("categorias");
    if (!grupos.ok) return;
    for (const { grupo, nombres } of grupos.datos) {
      const bloque = crear("optgroup");
      bloque.label = grupo;
      for (const nombre of nombres) bloque.append(new Option(nombre, nombre));
      categoria.append(bloque);
    }
    cargarUnidades();
  });

  const valor = crear("input");
  valor.value = "1";
  valor.inputMode = "decimal";
  const origen = crear("select");
  const destino = crear("select");
  const salida = crear("div", "salida", "—");
  const tabla = crear("div", "resultados");

  const cargarUnidades = () => {
    const r = llamar("unidades_de", categoria.value);
    if (!r.ok) return;
    origen.replaceChildren();
    destino.replaceChildren();
    for (const u of r.datos.unidades) {
      origen.append(new Option(u.etiqueta, u.simbolo));
      destino.append(new Option(u.etiqueta, u.simbolo));
    }
    destino.selectedIndex = Math.min(1, destino.options.length - 1);
    convertir();
  };

  const convertir = () => {
    const r = llamar("convertir", parseFloat(valor.value || "0"),
                     origen.value, destino.value, categoria.value);
    if (!r.ok) { salida.innerHTML = '<span class="error">' + r.error + "</span>"; return; }
    salida.textContent = `${valor.value} ${origen.value}  =  ${r.datos.texto} ${destino.value}`;
    tabla.replaceChildren(...r.datos.tabla.map((f) =>
      filaResultado(f.etiqueta, f.texto, f.valor)));
  };

  categoria.onchange = cargarUnidades;
  valor.oninput = convertir;
  origen.onchange = convertir;
  destino.onchange = convertir;

  const guardar = crear("button", "accion secundaria", "Guardar en el historial");
  guardar.onclick = () => anotar("conversiones", salida.textContent, null);

  seccion.append(rotulo("Magnitud"), categoria, rotulo("Valor"), valor,
                 rotulo("De"), origen, rotulo("A"), destino, salida, tabla, guardar);
}

/* ----------------------------------------------------------- geometría -- */

function montarGeometria(seccion) {
  const figura = crear("select");
  cuandoListo(() => {
    const lista = llamar("lista_figuras");
    if (!lista.ok) return;
    const porGrupo = {};
    for (const f of lista.datos) (porGrupo[f.grupo] ||= []).push(f.nombre);
    for (const [grupo, nombres] of Object.entries(porGrupo)) {
      const bloque = crear("optgroup");
      bloque.label = grupo;
      for (const nombre of nombres) bloque.append(new Option(nombre, nombre));
      figura.append(bloque);
    }
    cargar();
  });

  const campos = crear("div");
  const resultados = crear("div", "resultados");
  const formulas = crear("div", "pista");
  const calcular = crear("button", "accion", "Calcular");

  const cargar = () => {
    const r = llamar("parametros_de", figura.value);
    if (!r.ok) return;
    campos.replaceChildren();
    for (const p of r.datos.parametros) {
      const campo = crear("input");
      campo.dataset.simbolo = p.simbolo;
      campo.value = p.predeterminado;
      campo.placeholder = p.entero ? "número entero" : "admite 5 cm, 50 mm…";
      campo.onkeydown = (e) => { if (e.key === "Enter") hacer(); };
      const etiqueta = p.unidad && !["u", ""].includes(p.unidad)
        ? `${p.etiqueta} (${p.unidad})` : p.etiqueta;
      campos.append(rotulo(etiqueta), campo);
    }
    formulas.textContent = r.datos.formulas.join("     ");
    hacer();
  };

  const hacer = (guardar = false) => {
    const valores = {};
    for (const campo of campos.querySelectorAll("input")) {
      valores[campo.dataset.simbolo] = campo.value;
    }
    const r = llamar("calcular_figura", figura.value, JSON.stringify(valores));
    if (!r.ok) {
      resultados.innerHTML = '<span class="error">' + r.error + "</span>";
      return;
    }
    resultados.replaceChildren(...r.datos.resultados.map((f) =>
      filaResultado(f.etiqueta, f.texto, f.valor)));
    if (guardar) {
      const resumen = r.datos.resultados.slice(0, 2)
        .map((f) => `${f.etiqueta}: ${f.texto}`).join(", ");
      anotar("geometria", `${figura.value} → ${resumen}`, null);
    }
  };

  figura.onchange = cargar;
  calcular.onclick = () => hacer(true);
  seccion.append(rotulo("Figura"), figura, campos, calcular, resultados, formulas);
}

/* ---------------------------------------------------------- ecuaciones -- */

function montarEcuaciones(seccion) {
  const entrada = crear("input");
  entrada.placeholder = "x^2 - 5x + 6 = 0";
  entrada.value = "x^2 - 5x + 6 = 0";
  const salida = crear("div", "salida", "—");
  const resolver = crear("button", "accion", "Resolver");

  const hacer = async () => {
    salida.textContent = "Resolviendo…";
    await asegurarSympy();
    const r = llamar("resolver_ecuacion", entrada.value);
    if (!r.ok) { salida.innerHTML = '<span class="error">' + r.error + "</span>"; return; }
    const d = r.datos;
    const lineas = [
      "Normalizada:  " + d.normalizada,
      "Incógnita:    " + d.incognita,
      "Factorizada:  " + d.factorizada,
      "",
      ...d.soluciones.map((s, i) =>
        `${d.incognita}${i + 1} = ${s.exacto}` +
        (s.aproximado ? `   ≈ ${s.aproximado}` : "")),
    ];
    salida.textContent = lineas.join("\n");
    anotar("ecuaciones", entrada.value + "  →  " +
      d.soluciones.map((s) => s.exacto).join(", "), entrada.value);
  };

  resolver.onclick = hacer;
  entrada.onkeydown = (e) => { if (e.key === "Enter") hacer(); };
  seccion.append(rotulo("Ecuación"), entrada, resolver, salida);
}

/* ------------------------------------------------------------- cálculo -- */

function montarCalculo(seccion) {
  const operacion = crear("select");
  for (const [valor, texto] of [
    ["derivada", "Derivada"], ["integral", "Integral indefinida"],
    ["integral_definida", "Integral definida"], ["limite", "Límite"],
    ["analisis", "Análisis de la función"],
  ]) operacion.append(new Option(texto, valor));

  const funcion = crear("input");
  funcion.value = "x^2*sin(x)";
  funcion.placeholder = "f(x)";
  const variable = crear("input");
  variable.value = "x";
  const desde = crear("input");
  desde.placeholder = "desde";
  const hasta = crear("input");
  hasta.placeholder = "hasta";
  const extremos = crear("div", "fila");
  extremos.append(desde, hasta);

  const salida = crear("div", "resultados");
  const boton = crear("button", "accion", "Calcular");

  const ajustar = () => {
    const op = operacion.value;
    extremos.style.display =
      op === "integral_definida" || op === "limite" ? "flex" : "none";
    hasta.style.display = op === "limite" ? "none" : "";
    desde.placeholder = op === "limite" ? "tiende a" : "desde";
  };

  const hacer = async () => {
    salida.textContent = "Calculando…";
    await asegurarSympy();
    const r = llamar("calculo", operacion.value, funcion.value,
                     variable.value || "x", desde.value, hasta.value);
    if (!r.ok) { salida.innerHTML = '<span class="error">' + r.error + "</span>"; return; }
    salida.replaceChildren(...r.datos.filas.map((f) =>
      filaResultado(f.etiqueta, f.valor, null)));
    anotar("calculo", `${operacion.selectedOptions[0].text} de ${funcion.value}`,
           funcion.value);
  };

  operacion.onchange = ajustar;
  boton.onclick = hacer;
  funcion.onkeydown = (e) => { if (e.key === "Enter") hacer(); };
  seccion.append(rotulo("Operación"), operacion, rotulo("Función"), funcion,
                 rotulo("Variable"), variable, extremos, boton, salida);
  ajustar();
}

/* -------------------------------------------------------- combinatoria -- */

function montarCombinatoria(seccion) {
  const operacion = crear("select");
  for (const [valor, texto] of [
    ["factorial", "Factorial  n!"],
    ["combinaciones", "Combinaciones  C(n, r)"],
    ["permutaciones", "Permutaciones  P(n, r)"],
    ["variaciones_rep", "Variaciones con repetición  nʳ"],
    ["combinaciones_rep", "Combinaciones con repetición"],
  ]) operacion.append(new Option(texto, valor));

  const n = crear("input");
  n.value = "10";
  n.inputMode = "numeric";
  const r = crear("input");
  r.value = "4";
  r.inputMode = "numeric";
  const etiquetaR = rotulo("r");
  const salida = crear("div", "salida", "—");
  const boton = crear("button", "accion", "Calcular");

  const ajustar = () => {
    const soloN = operacion.value === "factorial";
    etiquetaR.style.display = r.style.display = soloN ? "none" : "";
  };

  const hacer = () => {
    const resultado = llamar("combinatoria", operacion.value,
                             parseInt(n.value || "0", 10), parseInt(r.value || "0", 10));
    if (!resultado.ok) {
      salida.innerHTML = '<span class="error">' + resultado.error + "</span>";
      return;
    }
    salida.textContent = resultado.datos.valor;
    anotar("combinatoria",
           `${operacion.selectedOptions[0].text.split("  ")[0]}(${n.value}` +
           (operacion.value === "factorial" ? "" : `, ${r.value}`) + ") = " +
           resultado.datos.valor.slice(0, 40), null);
  };

  operacion.onchange = () => { ajustar(); hacer(); };
  n.oninput = hacer;
  r.oninput = hacer;
  boton.onclick = hacer;
  seccion.append(rotulo("Operación"), operacion, rotulo("n"), n, etiquetaR, r,
                 boton, salida);
  ajustar();
  cuandoListo(hacer);
}

/* --------------------------------------------------------------- bases -- */

function montarBases(seccion) {
  const entrada = crear("input");
  entrada.value = "255";
  const base = crear("select");
  for (const [b, n] of [[10, "decimal"], [2, "binario"], [8, "octal"], [16, "hexadecimal"]]) {
    base.append(new Option(`${n} (base ${b})`, b));
  }
  const tabla = crear("div", "resultados");

  const hacer = () => {
    const r = llamar("convertir_base", entrada.value, parseInt(base.value, 10));
    if (!r.ok) { tabla.innerHTML = '<span class="error">' + r.error + "</span>"; return; }
    tabla.replaceChildren(...r.datos.tabla.map((f) =>
      filaResultado(`${f.nombre} (base ${f.base})`, f.texto, null)));
  };

  entrada.oninput = hacer;
  base.onchange = hacer;
  seccion.append(rotulo("Número"), entrada, rotulo("Base de partida"), base, tabla);
  cuandoListo(hacer);
}

/* --------------------------------------------------- piezas compartidas -- */

function rotulo(texto) {
  return crear("label", null, texto);
}

/** Una fila de resultado; al pulsarla se guarda como variable compartida. */
function filaResultado(etiqueta, texto, valor) {
  const fila = crear("div", "fila-res");
  fila.append(crear("span", "etiqueta", etiqueta), crear("span", "valor", texto));
  fila.title = "Pulse para guardarlo como variable y usarlo en otro apartado";
  fila.onclick = () => usarComoVariable(etiqueta, valor !== null ? valor : texto);
  return fila;
}

function usarComoVariable(etiqueta, valor) {
  const sugerido = etiqueta.normalize("NFD").replace(/[̀-ͯ]/g, "")
    .replace(/[^0-9A-Za-z]+/g, "_").replace(/^_|_$/g, "").toLowerCase() || "resultado";
  const nombre = prompt(
    `Guardar ${valor} como variable.\nPodrá usar ese nombre en cualquier apartado.`,
    sugerido);
  if (!nombre) return;
  const numero = typeof valor === "number" ? valor : parseFloat(String(valor));
  const r = llamar("definir_variable", nombre.trim(), numero);
  if (!r.ok) { alert(r.error); return; }
  refrescarVariables();
}

/* ----------------------------------------------------- barra de cálculo -- */

function prepararBarra() {
  const entrada = $("#barra-entrada");
  const resultado = $("#barra-resultado");
  const recordadas = [];
  let posicion = 0;

  entrada.oninput = () => {
    const r = llamar("vista_previa", entrada.value, estado.modo);
    resultado.textContent = r.ok && r.datos.texto ? "= " + r.datos.texto : "";
  };

  entrada.onkeydown = (e) => {
    if (e.key === "ArrowUp" && recordadas.length) {
      posicion = Math.max(0, posicion - 1);
      entrada.value = recordadas[posicion];
      e.preventDefault();
    } else if (e.key === "ArrowDown" && recordadas.length) {
      posicion = Math.min(recordadas.length, posicion + 1);
      entrada.value = recordadas[posicion] || "";
      e.preventDefault();
    } else if (e.key === "Enter") {
      const expresion = entrada.value.trim();
      if (!expresion) return;
      if (!estado.listo) {
        resultado.textContent = "preparando…";
        cuandoListo(() => entrada.dispatchEvent(
          new KeyboardEvent("keydown", { key: "Enter" })));
        return;
      }
      const r = llamar("calcular", expresion, estado.modo);
      if (!r.ok) {
        resultado.innerHTML = '<span class="error">' + r.error + "</span>";
        return;
      }
      recordadas.push(expresion);
      posicion = recordadas.length;
      // Lo calculado pertenece al apartado en el que se está trabajando.
      anotar(apartadoActivo(), expresion + " = " + r.datos.texto, expresion);
      entrada.value = "";
      resultado.textContent = "= " + r.datos.texto;
      refrescarVariables();
    }
  };

  $("#btn-variables").onclick = () => {
    const r = llamar("listar_variables");
    const lista = r.ok ? Object.entries(r.datos) : [];
    if (!lista.length) { alert("No hay ninguna variable definida."); return; }
    const texto = lista.map(([n, v]) => `${n} = ${v}`).join("\n");
    if (confirm(texto + "\n\n¿Borrarlas todas?")) {
      llamar("borrar_variables");
      refrescarVariables();
    }
  };
}

function refrescarVariables() {
  if (!estado.listo) return;
  const r = llamar("listar_variables");
  const cantidad = r.ok ? Object.keys(r.datos).length : 0;
  $("#btn-variables").textContent = cantidad ? `x= ${cantidad}` : "x=";
}

function apartadoActivo() {
  return [...estado.abiertos][estado.abiertos.size - 1] || "calculadora";
}

/* ------------------------------------------------------------ historial -- */

function montarHistorial(clave) {
  const caja = crear("div", "historial plegado");
  caja.id = "hist-" + clave;
  const titulo = crear("h3");
  titulo.append(crear("span", null, "Historial"), crear("span", "cuenta", ""));
  titulo.onclick = () => caja.classList.toggle("plegado");
  const lista = crear("ul");
  caja.append(titulo, lista);
  pintarHistorial(clave);
  return caja;
}

function leerHistorial(clave) {
  try {
    return JSON.parse(localStorage.getItem("axioma:" + clave) || "[]");
  } catch { return []; }
}

/** Guarda en el historial de ese apartado, que es propio y no se mezcla. */
function anotar(clave, texto, expresion) {
  const entradas = leerHistorial(clave);
  entradas.unshift({ texto, expresion, cuando: Date.now() });
  localStorage.setItem("axioma:" + clave, JSON.stringify(entradas.slice(0, 200)));
  pintarHistorial(clave);
}

function pintarHistorial(clave) {
  const caja = document.getElementById("hist-" + clave);
  if (!caja) return;
  const entradas = leerHistorial(clave);
  caja.querySelector(".cuenta").textContent = entradas.length || "";
  const lista = caja.querySelector("ul");
  lista.replaceChildren(...entradas.slice(0, 50).map((e) => {
    const elemento = crear("li", null, e.texto);
    if (e.expresion) {
      elemento.title = "Pulse para volver a cargarlo";
      elemento.onclick = () => {
        const destino = document.querySelector("#ap-" + clave + " input");
        if (destino) { destino.value = e.expresion; destino.dispatchEvent(new Event("input")); }
      };
    }
    return elemento;
  }));
}

/* ----------------------------------------------------------------- tema -- */

function prepararTema() {
  const guardado = localStorage.getItem("axioma:tema");
  if (guardado) document.documentElement.dataset.tema = guardado;
  $("#btn-tema").onclick = () => {
    const nuevo = document.documentElement.dataset.tema === "claro" ? "oscuro" : "claro";
    document.documentElement.dataset.tema = nuevo;
    localStorage.setItem("axioma:tema", nuevo);
  };
}

/* ------------------------------------------------------------ instalar -- */

/** Qué navegador es y qué sabe hacer con la instalación.
 *
 * No es adorno: cada uno la esconde en un sitio distinto, y unos cuantos ni
 * siquiera la implementan. Decirle a todo el mundo «abra el menú de los tres
 * puntos» hace que la mitad no encuentre nada.
 */
function navegador() {
  const ua = navigator.userAgent;
  const esIOS = /iphone|ipad|ipod/i.test(ua) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
  return {
    ios: esIOS,
    android: /android/i.test(ua),
    firefox: /firefox|fxios/i.test(ua),
    samsung: /samsungbrowser/i.test(ua),
    opera: /opr\//i.test(ua),
    safari: esIOS && !/crios|fxios|edgios/i.test(ua),
    escritorio: !esIOS && !/android|mobile/i.test(ua),
    windows: /windows/i.test(ua),
  };
}

/** Deja Axioma instalado como una aplicación más.
 *
 * Hay tres caminos y se ofrece el que sirva en cada navegador:
 *
 * 1. Instalación de un toque, si el navegador la ofrece (Chrome, Edge, Opera,
 *    Samsung Internet y los de escritorio menos Firefox).
 * 2. El APK, que en Android funciona sea cual sea el navegador.
 * 3. La opción del menú, indicando la ruta exacta de *ese* navegador.
 */
function prepararInstalacion() {
  const boton = $("#btn-instalar");
  const dialogo = $("#dialogo-instalar");
  const cuerpo = $("#dialogo-cuerpo");

  // El aviso lo recoge un script del propio index.html, que corre antes que
  // nada: cuando esta función se ejecuta, el navegador hace rato que avisó.
  const peticion = () => window.__peticionInstalacion;
  document.addEventListener("axioma:instalable", () => { boton.hidden = false; });

  window.addEventListener("appinstalled", () => {
    boton.hidden = true;
    window.__peticionInstalacion = null;
  });

  const yaInstalada = window.matchMedia("(display-mode: standalone)").matches ||
                      window.navigator.standalone === true;
  boton.hidden = yaInstalada;

  $("#dialogo-cerrar").onclick = () => dialogo.close();
  boton.onclick = () => abrirDialogoDeInstalacion(dialogo, cuerpo, peticion);
}

function abrirDialogoDeInstalacion(dialogo, cuerpo, peticion) {
  const nav = navegador();
  cuerpo.replaceChildren();

  const opcion = (titulo, descripcion, alPulsar) => {
    const caja = crear("div", "opcion");
    const accion = crear("button", "accion", titulo);
    accion.onclick = alPulsar;
    caja.append(accion, crear("p", "pista", descripcion));
    cuerpo.append(caja);
  };

  const pasos = (titulo, lineas) => {
    cuerpo.append(crear("h3", null, titulo));
    const lista = crear("ol", "pasos");
    for (const linea of lineas) lista.append(crear("li", null, linea));
    cuerpo.append(lista);
  };

  // 1. Lo mejor, cuando el navegador lo permite: un toque y listo.
  if (peticion()) {
    opcion("Instalar ahora", "Queda con su icono, sin barra de direcciones y funciona sin conexión.",
      async () => {
        const guardada = peticion();
        guardada.prompt();
        const { outcome } = await guardada.userChoice;
        window.__peticionInstalacion = null;
        if (outcome === "accepted") $("#btn-instalar").hidden = true;
        dialogo.close();
      });
  }

  // 2. En Android el APK vale para cualquier navegador, Firefox incluido.
  if (nav.android) {
    opcion("Descargar la aplicación (APK)",
      "Se descarga un archivo; ábralo y se instala. Android pedirá permiso " +
      "porque no viene de Google Play.",
      () => { window.location.href = ENLACE_APK; });
  }

  // 3. Y la opción del menú, con la ruta de este navegador en concreto.
  if (nav.ios) {
    pasos(nav.safari ? "Desde Safari" : "Desde Safari (es el único que puede en iPhone)", [
      "Toque el botón Compartir: el cuadrado con la flecha hacia arriba.",
      "Baje hasta «Añadir a pantalla de inicio».",
      "Confirme con «Añadir».",
    ]);
    if (!nav.safari) {
      cuerpo.append(crear("p", "pista",
        "En el iPhone sólo Safari puede instalar aplicaciones web; los demás " +
        "navegadores usan su motor pero no ofrecen la opción."));
    }
  } else if (nav.firefox && nav.android) {
    pasos("Desde Firefox", [
      "Toque el menú: los tres puntos, arriba a la derecha.",
      "Elija «Instalar» o «Añadir a la pantalla de inicio».",
      "Confirme el nombre y pulse «Añadir».",
    ]);
  } else if (nav.firefox) {
    cuerpo.append(crear("p", "pista",
      "Firefox en el ordenador no instala aplicaciones web. Puede dejarla " +
      "como marcador, usar Chrome o Edge para instalarla, o descargar la " +
      "aplicación de Windows."));
    if (nav.windows) {
      opcion("Descargar la aplicación de Windows",
        "La versión de escritorio, con los dieciséis apartados.",
        () => { window.location.href = ENLACE_EXE; });
    }
  } else if (nav.samsung) {
    pasos("Desde Samsung Internet", [
      "Toque el menú de abajo a la derecha.",
      "Elija «Añadir página a» y luego «Pantalla de inicio».",
    ]);
  } else if (!peticion()) {
    pasos("Desde el menú del navegador", [
      "Abra el menú del navegador.",
      "Busque «Instalar aplicación» o «Añadir a la pantalla de inicio».",
    ]);
  }

  if (typeof dialogo.showModal === "function") dialogo.showModal();
  else dialogo.setAttribute("open", "");        // navegadores sin <dialog> modal
}

/* ------------------------------------------------------------ memoria -- */

/* Una aplicación no empieza de cero cada vez que se abre.
 *
 * Se guarda lo que se estaba haciendo —el apartado abierto, lo escrito en cada
 * campo y las variables— y se recupera al volver. Sin esto, cerrar la
 * aplicación es perder el problema a medias, que es la otra mitad de la
 * sensación de estar reinstalándola cada vez.
 */

const MEMORIA = "axioma:estado";

function camposDe(clave) {
  const seccion = document.getElementById("ap-" + clave);
  if (!seccion) return null;
  return {
    selects: [...seccion.querySelectorAll("select")],
    entradas: [...seccion.querySelectorAll("input")],
  };
}

function recordarEstado() {
  try {
    const datos = {
      abiertos: [...estado.abiertos],
      modo: estado.modo,
      apartados: {},
    };
    for (const ap of APARTADOS) {
      const campos = camposDe(ap.clave);
      if (!campos) continue;
      datos.apartados[ap.clave] = {
        selects: campos.selects.map((s) => s.value),
        entradas: campos.entradas.map((i) => i.value),
      };
    }
    if (estado.listo) {
      const r = llamar("listar_variables");
      if (r.ok) datos.variables = r.datos;
    }
    localStorage.setItem(MEMORIA, JSON.stringify(datos));
  } catch {
    /* sin espacio o en privado: no pasa nada, se abre de cero */
  }
}

function restaurarEstado() {
  let datos;
  try {
    datos = JSON.parse(localStorage.getItem(MEMORIA) || "null");
  } catch {
    return;
  }
  if (!datos) return;

  if (datos.modo) estado.modo = datos.modo;
  if (Array.isArray(datos.abiertos) && datos.abiertos.length) {
    const validos = datos.abiertos.filter(
      (c) => APARTADOS.some((a) => a.clave === c));
    if (validos.length) {
      estado.abiertos = new Set(estado.movil() ? [validos[0]] : validos);
      refrescarMenu();
    }
  }

  // Los campos, cuando el motor haya llenado los desplegables: en Geometría la
  // lista de figuras y sus datos no existen hasta entonces.
  cuandoListo(() => {
    for (const [clave, guardado] of Object.entries(datos.apartados || {})) {
      const campos = camposDe(clave);
      if (!campos) continue;

      // Primero los desplegables: al cambiarlos se reconstruyen los campos.
      if (campos.selects.length === guardado.selects?.length) {
        campos.selects.forEach((select, i) => {
          const valor = guardado.selects[i];
          if (valor && [...select.options].some((o) => o.value === valor)) {
            select.value = valor;
            select.dispatchEvent(new Event("change"));
          }
        });
      }

      // Y después lo escrito, que ya tiene dónde ponerse.
      const ahora = camposDe(clave);
      if (ahora && ahora.entradas.length === guardado.entradas?.length) {
        ahora.entradas.forEach((entrada, i) => {
          if (guardado.entradas[i]) entrada.value = guardado.entradas[i];
        });
      }
    }

    for (const [nombre, valor] of Object.entries(datos.variables || {})) {
      llamar("definir_variable", nombre, valor);
    }
    refrescarVariables();
  });
}

// `visibilitychange` y no `beforeunload`: en el móvil una aplicación rara vez
// se cierra, se manda al fondo, y ése es el único aviso que llega seguro.
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") recordarEstado();
});
window.addEventListener("pagehide", recordarEstado);

window.addEventListener("resize", refrescarMenu);

if ("serviceWorker" in navigator) {
  // Si ya había uno al abrir, un relevo significa versión nueva. Si no lo
  // había, el relevo es el de la primera instalación y no hay nada que
  // estrenar: recargar ahí le arranca la página de las manos a quien acaba de
  // llegar, y le borra lo que estuviera escribiendo.
  const yaHabiaControlador = !!navigator.serviceWorker.controller;

  window.addEventListener("load", async () => {
    const registro = await navigator.serviceWorker.register("sw.js");

    // Con una versión nueva se recarga una vez para entrar en ella. Sin esto
    // la pestaña se queda con la anterior hasta que se cierran todas, y desde
    // fuera parece que la aplicación no se actualiza.
    let recargando = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (!yaHabiaControlador || recargando) return;
      recargando = true;
      recordarEstado();          // que la actualización no cueste el trabajo
      location.reload();
    });

    // Y se comprueba al arrancar, no sólo cuando el navegador quiera.
    registro.update().catch(() => {});
  });
}
arrancar();
