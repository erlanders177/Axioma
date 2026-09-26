"""Puente entre el núcleo de Axioma y la interfaz web.

Se ejecuta dentro del navegador, sobre Pyodide, e importa **el mismo**
``src/core`` que usa la aplicación de escritorio. Todo lo que devuelve es JSON,
que es lo único que cruza limpiamente hacia JavaScript.

Regla de la casa: aquí no se calcula nada. Si algo hay que resolver, lo resuelve
el núcleo; este archivo sólo traduce entradas y da formato a las salidas.
"""

from __future__ import annotations

import json
import math
import traceback

from axioma_nucleo import bases
from axioma_nucleo import figuras as geo
from axioma_nucleo import magnitudes
from axioma_nucleo import unidades as uni
from axioma_nucleo import variables
from axioma_nucleo.calculadora import Calculadora, paso_a_dict
from axioma_nucleo.evaluador import ErrorExpresion, evaluar
from axioma_nucleo.formato import formatear


def _responder(funcion, *args, **kwargs) -> str:
    """Ejecuta algo del núcleo y devuelve siempre JSON, error incluido.

    Una excepción que cruce hacia JavaScript se convierte en un mensaje
    ilegible; así el navegador siempre recibe la misma forma de respuesta.
    """
    try:
        return json.dumps({"ok": True, "datos": funcion(*args, **kwargs)},
                          ensure_ascii=False, default=str)
    except Exception as e:                                     # noqa: BLE001
        return json.dumps({
            "ok": False,
            "error": str(e) or type(e).__name__,
            "tipo": type(e).__name__,
            "detalle": traceback.format_exc(limit=3),
        }, ensure_ascii=False)


# --------------------------------------------------------------- calculadora -- #

def _entorno() -> dict:
    return dict(variables.valores())


def _calcular(expresion: str, modo: str = "DEG", decimales: int = 6) -> dict:
    expresion = (expresion or "").strip()
    if not expresion:
        raise ValueError("No hay nada que calcular")

    asignacion = None
    if expresion.count("=") == 1:
        izquierda, _, derecha = expresion.partition("=")
        nombre = izquierda.strip()
        if nombre.isidentifier() and derecha.strip():
            asignacion, expresion = nombre, derecha.strip()

    if magnitudes.contiene_unidades(expresion):
        cantidad = magnitudes.evaluar(expresion)
        if asignacion and cantidad.unidad is not None:
            raise ValueError(
                f"Las variables guardan números sin unidad. Convierta antes: "
                f"«{asignacion} = {expresion} a {cantidad.unidad.simbolo}»."
            )
        valor, texto = cantidad.valor, cantidad.texto(decimales)
    else:
        valor = evaluar(expresion, modo, _entorno())
        texto = formatear(valor, decimales)

    if asignacion:
        variables.definir(asignacion, valor)
    return {"texto": texto, "valor": valor, "variable": asignacion,
            "variables": _entorno()}


def calcular(expresion: str, modo: str = "DEG", decimales: int = 6) -> str:
    return _responder(_calcular, expresion, modo, decimales)


#: La calculadora de la pantalla principal, con su editor de fracciones, Ans y
#: el resultado exacto. Es la misma clase que usa el escritorio.
_calculadora = Calculadora()


def teclear(orden: str, argumento: str = "", modo: str = "DEG",
            decimales: int = 6) -> str:
    """Una tecla de la calculadora. Devuelve la pantalla entera para dibujarla."""
    def hacer() -> dict:
        _calculadora.modo = modo
        _calculadora.decimales = int(decimales)
        estado = _calculadora.tecla(orden, argumento)
        if estado["anotar"]:
            estado["variables"] = _entorno()
        return estado

    return _responder(hacer)


def _lista_de_pasos(pasos: list) -> list:
    return [paso_a_dict(paso) for paso in pasos]


def pasos_calculadora() -> str:
    """El paso a paso de la cuenta en pantalla, aquí mismo (necesita sympy)."""
    return _responder(lambda: _lista_de_pasos(_calculadora.pasos()))


def cuenta_calculadora() -> str:
    """La cuenta que hay que desarrollar, para mandarla al hilo de lo pesado.

    En el navegador, sympy vive en otro hilo, que no ve esta calculadora: se
    le manda el texto de la cuenta con las variables y Ans de ese momento.
    """
    def hacer() -> dict:
        cuenta = _calculadora.cuenta_a_desarrollar()
        if isinstance(cuenta, list):
            return {"pasos": _lista_de_pasos(cuenta)}
        texto, entorno = cuenta
        return {"texto": texto, "modo": _calculadora.modo,
                "entorno": entorno, "decimales": _calculadora.decimales}

    return _responder(hacer)


def pasos_de_cuenta(texto: str, modo: str, entorno_json: str, decimales: int = 6) -> str:
    def hacer() -> list:
        from axioma_nucleo.pasos_cuentas import pasos_expresion

        return _lista_de_pasos(pasos_expresion(texto, modo, json.loads(entorno_json),
                                               int(decimales)))

    return _responder(hacer)


# ------------------------------------------------------- el hilo de lo pesado -- #

def poner_variables(variables_json: str) -> None:
    """Las variables del usuario, tal como están en la pantalla.

    Este puente también corre en el hilo de las cuentas pesadas, que es otro
    Python con sus propias variables: las de la pantalla le llegan con cada
    petición.
    """
    variables.borrar_todas()
    for nombre, valor in json.loads(variables_json or "{}").items():
        try:
            variables.definir(nombre, float(valor))
        except (variables.ErrorVariable, TypeError, ValueError):
            continue


def preparar_pesado(carpeta_compilados: str | None = None) -> bool:
    """Importa sympy y lo que lo usa. Devuelve si hubo que compilarlo ahora.

    Con `carpeta_compilados`, la primera vez se compila sympy entero y se deja
    allí, y las siguientes se lee de allí en lugar de compilar otra vez. Se
    guarda sin comprobar fechas: los archivos de un paquete de Pyodide no
    cambian sin cambiar de versión, y la versión va en el nombre de la carpeta.
    """
    import importlib
    import importlib.util
    import os
    import sys

    recien = False
    if carpeta_compilados:
        sys.pycache_prefix = carpeta_compilados
        marca = os.path.join(carpeta_compilados, "completo")
        if not os.path.exists(marca):
            import compileall
            import py_compile

            for paquete in ("mpmath", "sympy"):
                origen = importlib.util.find_spec(paquete)
                if origen and origen.origin:
                    compileall.compile_dir(
                        os.path.dirname(origen.origin), quiet=1,
                        invalidation_mode=py_compile.PycInvalidationMode.UNCHECKED_HASH)
            os.makedirs(carpeta_compilados, exist_ok=True)
            with open(marca, "w", encoding="utf-8") as archivo:
                archivo.write("ok")
            recien = True

    for modulo in ("sympy", "axioma_nucleo.simbolico", "axioma_nucleo.pasos",
                   "axioma_nucleo.pasos_cuentas", "axioma_nucleo.calculo"):
        importlib.import_module(modulo)
    return recien


def vista_previa(expresion: str, modo: str = "DEG", decimales: int = 6) -> str:
    """Como calcular, pero sin definir variables ni protestar si va a medias."""
    def hacer() -> dict:
        texto = (expresion or "").strip()
        if not texto or "=" in texto:
            return {"texto": ""}
        try:
            if magnitudes.contiene_unidades(texto):
                return {"texto": magnitudes.evaluar(texto).texto(decimales)}
            return {"texto": formatear(evaluar(texto, modo, _entorno()), decimales)}
        except (ErrorExpresion, magnitudes.ErrorMagnitud, ValueError, ArithmeticError):
            return {"texto": ""}

    return _responder(hacer)


# ----------------------------------------------------------------- variables -- #

def listar_variables() -> str:
    return _responder(lambda: _entorno())


def borrar_variables() -> str:
    def hacer() -> dict:
        variables.borrar_todas()
        return {}

    return _responder(hacer)


def definir_variable(nombre: str, valor: float) -> str:
    def hacer() -> dict:
        variables.definir(nombre, float(valor))
        return {"variables": _entorno()}

    return _responder(hacer)


# --------------------------------------------------------------- conversiones -- #

def categorias() -> str:
    def hacer() -> list:
        return [{"grupo": grupo, "nombres": list(nombres)}
                for grupo, nombres in uni.GRUPOS.items()]

    return _responder(hacer)


def unidades_de(categoria: str) -> str:
    def hacer() -> dict:
        cat = uni.categoria(categoria)
        return {
            "predeterminada": cat.predeterminada,
            "nota": cat.nota,
            "unidades": [{"simbolo": u.simbolo, "etiqueta": u.etiqueta,
                          "nombre": u.nombre}
                         for u in cat.unidades],
        }

    return _responder(hacer)


def convertir(valor: float, origen: str, destino: str, categoria: str,
              decimales: int = 6) -> str:
    def hacer() -> dict:
        resultado = uni.convertir(float(valor), origen, destino, categoria)
        tabla = [
            {"etiqueta": unidad.etiqueta, "valor": v, "texto": formatear(v, decimales)}
            for unidad, v in uni.tabla_completa(float(valor), origen, categoria)
        ]
        return {"valor": resultado, "texto": formatear(resultado, decimales),
                "tabla": tabla}

    return _responder(hacer)


def pasos_conversion(valor: float, origen: str, destino: str, categoria: str,
                     decimales: int = 6) -> str:
    def hacer() -> list:
        from axioma_nucleo import pasos_cuentas

        return _lista_de_pasos(pasos_cuentas.pasos_conversion(
            float(valor), origen, destino, categoria, int(decimales)))

    return _responder(hacer)


# ------------------------------------------------------------------ geometría -- #

def lista_figuras() -> str:
    def hacer() -> list:
        return [{"nombre": nombre, "grupo": figura.grupo}
                for nombre, figura in geo.FIGURAS.items()]

    return _responder(hacer)


def parametros_de(figura: str) -> str:
    def hacer() -> dict:
        f = geo.figura(figura)
        return {
            "nombre": f.nombre,
            "nota": f.nota,
            "formulas": list(f.formulas),
            "parametros": [
                {"simbolo": p.simbolo, "etiqueta": p.etiqueta, "unidad": p.unidad,
                 "entero": p.entero, "predeterminado": p.predeterminado,
                 "ayuda": p.ayuda}
                for p in f.parametros
            ],
        }

    return _responder(hacer)


def _datos_de_figura(f, valores_json: str):
    """Los datos de una figura ya en números, y la unidad de longitud común.

    Cada dato puede venir como «5 cm», «sqrt(16)» o «radio»: se resuelve igual
    que en el escritorio, y las longitudes se unifican a la primera unidad que
    aparezca.
    """
    crudos = json.loads(valores_json)
    longitudes = [p.simbolo for p in f.parametros if p.unidad in ("u", "u²", "u³")]
    cantidades: dict[str, magnitudes.Cantidad] = {}
    for simbolo, texto in crudos.items():
        cantidades[simbolo] = _cantidad(str(texto))

    referencia = None
    for simbolo in longitudes:
        cantidad = cantidades.get(simbolo)
        if cantidad is not None and cantidad.unidad is not None:
            if cantidad.categoria != "Longitud":
                raise ValueError(
                    f"«{cantidad.unidad.simbolo}» no es una unidad de longitud."
                )
            referencia = cantidad.unidad
            break

    valores = {}
    for simbolo, cantidad in cantidades.items():
        if referencia is not None and simbolo in longitudes and cantidad.unidad:
            cantidad = cantidad.convertida_a(referencia)
        valores[simbolo] = cantidad.valor
    return valores, referencia


def calcular_figura(figura: str, valores_json: str, decimales: int = 6) -> str:
    def hacer() -> dict:
        f = geo.figura(figura)
        valores, referencia = _datos_de_figura(f, valores_json)

        def con_unidad(sufijo: str) -> str:
            if referencia is None or sufijo not in ("u", "u²", "u³"):
                return sufijo
            return referencia.simbolo + sufijo[1:]

        resultados = f.calcular(valores)
        return {
            "formulas": list(f.formulas),
            "resultados": [
                {"etiqueta": r.etiqueta, "valor": r.valor,
                 "texto": formatear(r.valor, decimales, unidad=con_unidad(r.unidad))}
                for r in resultados
            ],
        }

    return _responder(hacer)


def pasos_figura(figura: str, valores_json: str, decimales: int = 6) -> str:
    def hacer() -> list:
        from axioma_nucleo import pasos_cuentas

        f = geo.figura(figura)
        valores, referencia = _datos_de_figura(f, valores_json)
        unidad = referencia.simbolo if referencia is not None else ""
        return _lista_de_pasos(pasos_cuentas.pasos_figura(f.nombre, valores, unidad,
                                                          int(decimales)))

    return _responder(hacer)


def _cantidad(texto: str) -> magnitudes.Cantidad:
    """Lee un dato del usuario: número, expresión, variable o magnitud."""
    texto = texto.strip()
    if not texto:
        raise ValueError("Faltan datos por rellenar")
    try:
        return magnitudes.Cantidad(float(texto.replace(",", ".")), None)
    except ValueError:
        pass
    if magnitudes.contiene_unidades(texto):
        return magnitudes.evaluar(texto)
    return magnitudes.Cantidad(float(evaluar(texto, "DEG", _entorno())), None)


# ------------------------------------------------------------------ ecuaciones -- #

def resolver_ecuacion(texto: str, decimales: int = 6) -> str:
    def hacer() -> dict:
        # sympy se importa aquí y no arriba: pesa unos segundos de descarga y
        # la calculadora, las conversiones y la geometría no lo necesitan. Así
        # la aplicación abre al momento y sólo paga quien resuelve ecuaciones.
        from axioma_nucleo import simbolico as sim

        izquierda, derecha = sim.analizar_igualdad(texto)
        libres = sim.incognitas(izquierda, derecha)
        if not libres:
            raise ValueError("La expresión no contiene ninguna incógnita")
        if len(libres) > 1:
            nombres = ", ".join(s.name for s in libres)
            raise ValueError(f"Hay varias incógnitas ({nombres}): despeje una sola")

        incognita = libres[0]
        expresion = sim.sp.simplify(izquierda - derecha)
        soluciones = sim.sp.solve(sim.sp.Eq(expresion, 0), incognita, dict=False)
        if not isinstance(soluciones, list):
            soluciones = [soluciones]

        salida = []
        for solucion in soluciones:
            try:
                aproximado = complex(sim.sp.N(solucion))
            except (TypeError, ValueError):
                salida.append({"exacto": str(solucion), "aproximado": None})
                continue
            if abs(aproximado.imag) < 1e-12:
                texto_aprox = formatear(aproximado.real, decimales)
                valor = aproximado.real
            else:
                texto_aprox = f"{aproximado.real:.{decimales}g} + {aproximado.imag:.{decimales}g}i"
                valor = None
            salida.append({"exacto": str(solucion), "aproximado": texto_aprox,
                           "valor": valor})

        return {"incognita": incognita.name,
                "normalizada": f"{sim.sp.expand(expresion)} = 0",
                "factorizada": str(sim.sp.factor(expresion)),
                "soluciones": salida}

    return _responder(hacer)


def pasos_ecuacion(texto: str) -> str:
    def hacer() -> list:
        from axioma_nucleo import pasos as pasos_core
        from axioma_nucleo import simbolico as sim

        izquierda, derecha = sim.analizar_igualdad(texto)
        libres = sim.incognitas(izquierda, derecha)
        if len(libres) != 1:
            raise ValueError("El paso a paso es para ecuaciones de una incógnita")
        expresion = sim.sp.simplify(izquierda - derecha)
        return _lista_de_pasos(pasos_core.pasos_ecuacion(expresion, libres[0]))

    return _responder(hacer)


# --------------------------------------------------------------------- bases -- #

def convertir_base(texto: str, origen: int, decimales: int = 8) -> str:
    def hacer() -> dict:
        return {
            "valor": bases.a_decimal(texto, int(origen)),
            "tabla": [{"base": base, "nombre": bases.nombre_base(base), "texto": salida}
                      for base, salida in bases.tabla_bases(texto, int(origen), decimales)],
        }

    return _responder(hacer)


# ------------------------------------------------------------- combinatoria -- #

def combinatoria(operacion: str, n: float, r: float = 0) -> str:
    def hacer() -> dict:
        n_entero, r_entero = int(n), int(r)
        tabla = {
            "factorial": lambda: math.factorial(n_entero),
            "combinaciones": lambda: math.comb(n_entero, r_entero),
            "permutaciones": lambda: math.perm(n_entero, r_entero),
            "variaciones_rep": lambda: n_entero ** r_entero,
            "combinaciones_rep": lambda: math.comb(n_entero + r_entero - 1, r_entero),
        }
        if operacion not in tabla:
            raise ValueError(f"Operación desconocida: {operacion}")
        return {"valor": str(tabla[operacion]())}

    return _responder(hacer)


# --------------------------------------------------------------------- cálculo -- #

def calculo(operacion: str, expresion: str, variable: str = "x",
            desde: str = "", hasta: str = "") -> str:
    """Derivadas, integrales y límites. Devuelve pares (etiqueta, valor)."""
    def hacer() -> dict:
        from axioma_nucleo import calculo as calc

        if operacion == "derivada":
            filas = calc.derivar(expresion, variable)
        elif operacion == "integral":
            filas = calc.integrar(expresion, variable)
        elif operacion == "integral_definida":
            filas = calc.integrar_definida(expresion, variable, desde, hasta)
        elif operacion == "limite":
            filas = calc.limite(expresion, variable, desde or "0")
        elif operacion == "analisis":
            filas = calc.analizar_funcion(expresion, variable)
        else:
            raise ValueError(f"Operación desconocida: {operacion}")
        return {"filas": [{"etiqueta": e, "valor": v} for e, v in filas]}

    return _responder(hacer)


def pasos_calculo(operacion: str, expresion: str, variable: str = "x") -> str:
    """El desarrollo de una derivada o una integral."""
    def hacer() -> list:
        from axioma_nucleo import calculo as calc
        from axioma_nucleo import pasos as pasos_core

        funcion, simbolo = calc._preparar(expresion, variable)
        if operacion == "derivada":
            return _lista_de_pasos(pasos_core.pasos_derivada(funcion, simbolo))
        if operacion in ("integral", "integral_definida"):
            pasos = _lista_de_pasos(pasos_core.pasos_integral(funcion, simbolo))
            if operacion == "integral_definida":
                pasos.append({"titulo": "Regla de Barrow",
                              "detalle": "Con la primitiva F, se evalúa entre los límites.",
                              "expresion": "∫[a,b] f dx = F(b) − F(a)", "nivel": 0})
            return pasos
        raise ValueError("Esta operación no tiene desarrollo paso a paso; "
                         "sí lo tienen las derivadas y las integrales.")

    return _responder(hacer)
