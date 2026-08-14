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

//: La aplicación de Android, adjunta a la última versión publicada. Es la
//: salida para los navegadores que no ofrecen instalación automática.
const ENLACE_APK =
  "https://github.com/erlanders177/Axioma/releases/latest/download/Axioma.apk";

const estado = {
  py: null,
  puente: null,
  sympyCargado: false,
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

async function arrancar() {
  const estadoCarga = $("#estado-carga");
  const progreso = $("#barra-progreso");
  const paso = (texto, porcentaje) => {
    estadoCarga.textContent = texto;
    progreso.style.width = porcentaje + "%";
  };

  // Un aviso si tarda: en una conexión lenta son varios megas y una pantalla
  // quieta se confunde con una que no funciona.
  const lento = setTimeout(() => {
    const nota = document.createElement("p");
    nota.className = "pista";
    nota.textContent = "Está tardando más de lo normal. Son unos 15 MB la " +
      "primera vez; con mala cobertura puede llevar un par de minutos.";
    $("#estado-carga").after(nota);
  }, 25000);

  try {
    if (typeof loadPyodide !== "function") {
      throw new Error(
        "no se pudo descargar el motor de Python. Compruebe la conexión, y " +
        "si está en una red con filtros (trabajo, universidad) pruebe con los " +
        "datos del móvil: se descarga de cdn.jsdelivr.net."
      );
    }
    paso("Descargando Python…", 20);
    estado.py = await loadPyodide();

    paso("Copiando el núcleo de Axioma…", 60);
    const nucleo = await (await fetch("nucleo.json")).json();
    const creados = new Set();
    for (const [ruta, codigo] of Object.entries(nucleo)) {
      const carpeta = ruta.includes("/") ? ruta.slice(0, ruta.lastIndexOf("/")) : "";
      if (carpeta && !creados.has(carpeta)) {
        estado.py.FS.mkdirTree("/home/pyodide/" + carpeta);
        creados.add(carpeta);
      }
      estado.py.FS.writeFile("/home/pyodide/" + ruta, codigo);
    }

    paso("Comprobando que todo responde…", 85);
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

    // Una cuenta de verdad antes de dar por buena la carga: si el núcleo no
    // funciona, es mejor saberlo aquí que a la primera tecla del usuario.
    const prueba = llamar("calcular", "2+2");
    if (!prueba.ok || prueba.datos.texto !== "4") {
      throw new Error("el núcleo no devuelve resultados correctos");
    }

    paso("Listo", 100);
    clearTimeout(lento);
    $("#cargando").classList.add("listo");
    montar();
  } catch (e) {
    clearTimeout(lento);
    estadoCarga.innerHTML =
      '<span class="error">No se pudo arrancar: ' + e.message + "</span>";
    progreso.style.width = "100%";
    const reintentar = document.createElement("button");
    reintentar.className = "accion";
    reintentar.textContent = "Reintentar";
    reintentar.onclick = () => location.reload();
    estadoCarga.after(reintentar);
  }
}

/** Llama a una función del puente y devuelve el objeto ya interpretado. */
function llamar(funcion, ...args) {
  try {
    return JSON.parse(estado.puente(funcion, ...args));
  } catch (e) {
    return { ok: false, error: String(e) };
  }
}

/** sympy pesa varios segundos: se descarga la primera vez que hace falta. */
async function asegurarSympy() {
  if (estado.sympyCargado) return;
  const aviso = crear("div", "pista", "Descargando sympy (sólo la primera vez)…");
  $("#ap-ecuaciones .salida")?.replaceChildren(aviso);
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
  $("#version").textContent = "calculadora científica · web";
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
  const grupos = llamar("categorias");
  if (grupos.ok) {
    for (const { grupo, nombres } of grupos.datos) {
      const bloque = crear("optgroup");
      bloque.label = grupo;
      for (const nombre of nombres) bloque.append(new Option(nombre, nombre));
      categoria.append(bloque);
    }
  }

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
  cargarUnidades();
}

/* ----------------------------------------------------------- geometría -- */

function montarGeometria(seccion) {
  const figura = crear("select");
  const lista = llamar("lista_figuras");
  if (lista.ok) {
    const porGrupo = {};
    for (const f of lista.datos) (porGrupo[f.grupo] ||= []).push(f.nombre);
    for (const [grupo, nombres] of Object.entries(porGrupo)) {
      const bloque = crear("optgroup");
      bloque.label = grupo;
      for (const nombre of nombres) bloque.append(new Option(nombre, nombre));
      figura.append(bloque);
    }
  }

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
  cargar();
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
  hacer();
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
  hacer();
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

/** Deja Axioma instalado como una aplicación más del teléfono o del escritorio.
 *
 * Android y el escritorio avisan con `beforeinstallprompt` cuando el sitio
 * cumple los requisitos, y entonces se puede instalar con un botón. Safari no
 * implementa nada de eso: allí lo único que cabe es explicar dónde está la
 * opción, porque el usuario no tiene por qué saberlo.
 */
function prepararInstalacion() {
  const boton = $("#btn-instalar");

  // El aviso lo recoge un script del propio index.html, que corre antes que
  // nada: cuando esta función se ejecuta ya se ha cargado el motor de cálculo
  // y el navegador hace rato que avisó. Aquí sólo se recupera.
  const peticion = () => window.__peticionInstalacion;
  document.addEventListener("axioma:instalable", () => { boton.hidden = false; });

  window.addEventListener("appinstalled", () => {
    boton.hidden = true;
    window.__peticionInstalacion = null;
  });

  const esIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
  const yaInstalada = window.matchMedia("(display-mode: standalone)").matches ||
                      window.navigator.standalone === true;

  // El botón se muestra siempre que no esté ya instalada, sin esperar a
  // `beforeinstallprompt`: ese evento no existe en Safari y varios navegadores
  // de Android lo retrasan o no lo mandan nunca. Si llega, el botón instala de
  // un toque; si no llega, explica dónde está la opción. Lo que no puede pasar
  // es que se pueda instalar y no haya manera de enterarse.
  boton.hidden = yaInstalada;

  boton.onclick = async () => {
    const guardada = peticion();
    if (guardada) {
      // Esto es lo que abre el cuadro del sistema: «¿Instalar Axioma?».
      guardada.prompt();
      const { outcome } = await guardada.userChoice;
      if (outcome === "accepted") boton.hidden = true;
      window.__peticionInstalacion = null;
      return;
    }

    // Sin aviso del navegador no hay instalación de un toque. Antes de mandar
    // al usuario a rebuscar por los menús, se le ofrece el APK, que es
    // justamente «pulsar y que se descargue».
    if (!esIOS && confirm(
        "Este navegador no ofrece la instalación automática.\n\n" +
        "¿Descargar la aplicación (APK) para instalarla directamente?\n\n" +
        "Si prefiere el otro camino, cancele y le indico dónde está la opción " +
        "en el menú del navegador.")) {
      window.location.href = ENLACE_APK;
      return;
    }
    alert(
      esIOS
        ? [
            "Para instalarla en el iPhone:",
            "",
            "1. Toque el botón Compartir (el cuadrado con la flecha hacia arriba).",
            "2. Elija «Añadir a pantalla de inicio».",
            "",
            "Quedará como una aplicación más, y funciona sin conexión.",
          ].join("\n")
        : [
            "Para instalarla:",
            "",
            "Abra el menú del navegador (los tres puntos) y elija",
            "«Instalar aplicación» o «Añadir a pantalla de inicio».",
            "",
            "Quedará como una aplicación más, y funciona sin conexión.",
          ].join("\n")
    );
  };
}

window.addEventListener("resize", refrescarMenu);
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => navigator.serviceWorker.register("sw.js"));
}
arrancar();
