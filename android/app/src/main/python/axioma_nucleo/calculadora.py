"""La calculadora entera: lo que se escribe, el resultado y Ans.

Axioma tiene tres caras —escritorio, navegador y Android— y las tres enseñan la
misma calculadora. Aquí está escrita una sola vez. Cada interfaz le pasa las
teclas con :meth:`Calculadora.tecla` y dibuja lo que devuelve
:meth:`Calculadora.estado`: la expresión con sus fracciones, el resultado exacto
o el decimal, la vista previa y el error si lo hay. Así un «=», un «Ans» o la
tecla S⇔D se comportan igual en todas, sin tres copias que se desincronicen.

Cómo se comporta, como una calculadora escolar
----------------------------------------------
* Tras «=», la expresión se queda arriba y el resultado debajo.
* Si lo siguiente es un operador (+, ×, ^, la fracción…), la cuenta sigue desde
  el resultado: «Ans + …». Si es una cifra o una función, empieza otra nueva.
* Las flechas o el borrado tras «=» vuelven a la expresión para corregirla.
* S⇔D alterna entre el resultado exacto (√2/2, 3/4) y el decimal.
"""

from __future__ import annotations

from . import exacto, magnitudes, variables
from .editor import Editor, ErrorEditor
from .evaluador import ErrorExpresion, evaluar, parentesis_pendientes
from .formato import formatear

__all__ = ["Calculadora", "paso_a_dict"]

#: Si lo primero que se teclea tras «=» empieza por uno de estos, la cuenta
#: sigue con el resultado delante: «+ 3» es «Ans + 3».
_SIGUEN_DESDE_ANS = ("+", "-", "−", "*", "×", "÷", "/", "^", "!", "²", "³", "%")

_ESCRIBEN = {"insertar", "escribir", "fraccion"}
_MUEVEN = {"izquierda", "derecha", "arriba", "abajo", "inicio", "fin", "borrar"}

#: Errores que son culpa de lo escrito, no del programa: se enseñan tal cual.
_ERRORES_DE_CUENTA = (ErrorExpresion, ErrorEditor, magnitudes.ErrorMagnitud,
                      variables.ErrorVariable, ValueError, ArithmeticError)


def separar_asignacion(expresion: str) -> tuple[str, str] | None:
    """«r = 5» → ("r", "5"). No confunde ``==``, ``<=`` ni ``>=`` con una."""
    if expresion.count("=") != 1:
        return None
    izquierda, _, derecha = expresion.partition("=")
    if izquierda.rstrip()[-1:] in "<>!":
        return None
    nombre = izquierda.strip()
    if not nombre.isidentifier() or not derecha.strip():
        return None
    return nombre, derecha.strip()


def _legible(texto: str) -> str:
    """«x**2 - 5*x» como se escribe a mano: «x^2 - 5·x»."""
    return texto.replace("**", "^").replace("*", "·")


def paso_a_dict(paso) -> dict:
    """Un paso del desarrollo, listo para mandarlo como JSON."""
    return {"titulo": paso.titulo, "detalle": _legible(paso.detalle),
            "expresion": _legible(paso.expresion), "nivel": paso.nivel}


class Calculadora:
    """Una calculadora con su pantalla: la de cualquiera de las tres versiones."""

    def __init__(self, modo: str = "DEG", decimales: int = 6) -> None:
        self.editor = Editor()
        self.modo = modo
        self.decimales = decimales
        #: El último resultado, en decimal y (si lo hay) exacto, para «Ans».
        self.ans = 0.0
        self.ans_exacto: str | None = None
        #: La memoria (MR, M+, M−). Sólo la usa el escritorio, pero es un valor
        #: más para las cuentas y vive aquí con Ans.
        self.memoria = 0.0

        self.resultado: dict | None = None
        #: La pantalla muestra una cuenta terminada, con su resultado.
        self.calculado = False
        #: S⇔D: ver el decimal aunque haya forma exacta.
        self.en_decimal = False
        self.error: str | None = None
        #: Lo necesario para rehacer la última cuenta: el texto calculado y las
        #: variables tal como estaban (Ans ya ha cambiado desde entonces).
        self._ultima: tuple[str, dict] | None = None
        #: La cuenta recién hecha, para que la interfaz la apunte en su historial.
        self._anotar: dict | None = None

    # ------------------------------------------------------------ teclas -- #

    def tecla(self, orden: str, argumento: str = "") -> dict:
        """Atiende una tecla y devuelve cómo queda la pantalla."""
        self.error = None
        self._anotar = None
        try:
            self._atender(orden, argumento)
        except _ERRORES_DE_CUENTA as e:
            self.error = str(e)
        return self.estado()

    def _atender(self, orden: str, argumento: str) -> None:
        if orden == "estado":
            pass                          # sólo cómo está la pantalla
        elif orden == "calcular":
            self.calcular()
        elif orden == "sd":
            if self.resultado and self.resultado["exacto"]:
                self.en_decimal = not self.en_decimal
        elif orden == "limpiar":
            self.limpiar()
        elif orden == "cargar":
            self.editor.cargar(argumento)
            self._editar()
        elif orden == "negativo":
            # La tecla (−) de las calculadoras: tras «=» empieza una cuenta
            # nueva en negativo en lugar de restar del resultado.
            if self.calculado:
                self.editor.limpiar()
                self._editar()
            self.editor.insertar("−")
        elif orden == "modo":
            self.modo = argumento or "DEG"
        elif orden == "decimales":
            self.decimales = int(argumento)
        elif orden in _ESCRIBEN:
            if self.calculado:
                self._empezar_tras_resultado(orden, argumento)
            self.editor.accion(orden, argumento)
        elif orden in _MUEVEN:
            if self.calculado:
                self._volver_a_la_expresion(orden)
            else:
                self.editor.accion(orden, argumento)
        else:
            raise ErrorEditor(f"Tecla desconocida: {orden}")

    def _editar(self) -> None:
        self.calculado = False
        self.resultado = None
        self.en_decimal = False

    def _empezar_tras_resultado(self, orden: str, argumento: str) -> None:
        sigue = orden == "fraccion" or argumento.startswith(_SIGUEN_DESDE_ANS)
        self.editor.limpiar()
        self._editar()
        if sigue:
            self.editor.insertar("Ans")

    def _volver_a_la_expresion(self, orden: str) -> None:
        """Tras «=», las flechas y el borrado vuelven a lo escrito."""
        self._editar()
        if orden == "derecha":
            self.editor.inicio()
        else:
            self.editor.fin()
            if orden == "borrar":
                self.editor.borrar()

    def limpiar(self) -> None:
        self.editor.limpiar()
        self._editar()

    # ------------------------------------------------------------ cuentas -- #

    def _entorno_decimal(self) -> dict:
        entorno = {"ans": self.ans, "Ans": self.ans, "mem": self.memoria}
        entorno.update(variables.valores())
        return entorno

    def _entorno_exacto(self) -> dict:
        entorno = self._entorno_decimal()
        if self.ans_exacto is not None:
            entorno["ans"] = entorno["Ans"] = self.ans_exacto
        return entorno

    def calcular(self) -> None:
        """La tecla «=». Se puede repetir: «Ans × 2», «=», «=» va doblando."""
        texto = self.editor.lineal().strip()
        if not texto:
            return
        asignacion = separar_asignacion(texto)
        cuerpo = asignacion[1] if asignacion else texto
        entorno = self._entorno_exacto()

        resultado = self._resolver(cuerpo, entorno)
        if asignacion:
            if resultado["unidad"]:
                raise ValueError(
                    f"Las variables guardan números sin unidad. Convierta antes: "
                    f"«{asignacion[0]} = {cuerpo} a {resultado['unidad']}»."
                )
            variables.definir(asignacion[0], resultado["valor"])
            resultado["variable"] = asignacion[0]

        self.resultado = resultado
        self.ans = resultado["valor"]
        self.ans_exacto = resultado["simbolico"]
        self.calculado = True
        self.en_decimal = False
        self._ultima = (cuerpo, entorno)

        escrito = self.editor.texto()
        self._anotar = {"expresion": escrito,
                        "resultado": resultado["decimal"],
                        "texto": f"{escrito} = {self._texto_del_resultado()}"}

    def _resolver(self, texto: str, entorno: dict) -> dict:
        resultado = {"valor": 0.0, "decimal": "", "exacto": None, "arbol": None,
                     "simbolico": None, "unidad": None, "variable": None}

        if magnitudes.contiene_unidades(texto):
            cantidad = magnitudes.evaluar(texto)
            resultado.update(valor=cantidad.valor,
                             decimal=cantidad.texto(self.decimales),
                             unidad=cantidad.unidad.simbolo if cantidad.unidad else None)
            return resultado

        r = exacto.calcular(texto, self.modo, entorno, self.decimales)
        resultado.update(valor=r.valor, decimal=r.decimal, simbolico=r.simbolico)
        if r.tiene_exacto:
            resultado.update(exacto=r.exacto, arbol=r.arbol)
        return resultado

    # ------------------------------------------------------------ pantalla -- #

    def _texto_del_resultado(self) -> str:
        r = self.resultado
        if r is None:
            return ""
        texto = r["exacto"] if r["exacto"] and not self.en_decimal else r["decimal"]
        if r["exacto"] and not self.en_decimal:
            texto += f" ≈ {r['decimal']}"
        return texto

    def _resultado_visible(self) -> dict | None:
        r = self.resultado
        if not self.calculado or r is None:
            return None
        exacto = bool(r["exacto"]) and not self.en_decimal
        arbol = list(r["arbol"]) if exacto else [{"t": "txt", "v": r["decimal"]}]
        if r["variable"]:
            arbol.insert(0, {"t": "txt", "v": f"{r['variable']} = "})
        return {
            "arbol": arbol,
            "texto": r["exacto"] if exacto else r["decimal"],
            "decimal": r["decimal"],
            "exacto": r["exacto"],
            "tiene_exacto": bool(r["exacto"]),
            "en_decimal": self.en_decimal,
            "valor": r["valor"],
            "variable": r["variable"],
        }

    def _previa(self) -> str:
        """El resultado aproximado mientras se escribe, si ya tiene sentido."""
        if self.calculado or self.editor.vacio:
            return ""
        try:
            texto = self.editor.lineal().strip()
        except ErrorEditor:
            return ""
        asignacion = separar_asignacion(texto)
        cuerpo = asignacion[1] if asignacion else texto
        if "=" in cuerpo:
            return ""
        # Se cierran los paréntesis pendientes: «sin(30» ya dice algo.
        cuerpo += ")" * parentesis_pendientes(cuerpo)
        prefijo = f"{asignacion[0]} = " if asignacion else "= "
        try:
            if magnitudes.contiene_unidades(cuerpo):
                return prefijo + magnitudes.evaluar(cuerpo).texto(self.decimales)
            return prefijo + formatear(evaluar(cuerpo, self.modo, self._entorno_decimal()),
                                       self.decimales)
        except _ERRORES_DE_CUENTA:
            return ""

    def texto(self) -> str:
        """Lo escrito, en una línea legible, o vacío si tiene huecos sin rellenar."""
        try:
            return self.editor.texto()
        except ErrorEditor:
            return ""

    def estado(self) -> dict:
        """Todo lo que la interfaz necesita para dibujar la pantalla."""
        return {
            "entrada": self.editor.arbol(con_cursor=not self.calculado),
            "vacia": self.editor.vacio,
            "texto": self.texto(),
            "calculado": self.calculado,
            "resultado": self._resultado_visible(),
            "previa": self._previa(),
            "error": self.error,
            "anotar": self._anotar,
        }

    # --------------------------------------------------------------- pasos -- #

    def cuenta_a_desarrollar(self):
        """(texto, variables) de la cuenta en pantalla, o los pasos si no la hay.

        La hecha, si se acaba de pulsar «=»; si no, la que se está escribiendo.
        Va separado de :meth:`pasos` porque en el navegador el desarrollo se
        hace en otro hilo, que necesita recibir la cuenta tal cual.
        """
        from .paso import Paso

        if self.calculado and self._ultima:
            cuerpo, entorno = self._ultima
        else:
            try:
                texto = self.editor.lineal().strip()
            except ErrorEditor as e:
                return [Paso("Falta algo por escribir", str(e))]
            if not texto:
                return [Paso("No hay nada que desarrollar", "Escriba una cuenta primero.")]
            asignacion = separar_asignacion(texto)
            cuerpo = asignacion[1] if asignacion else texto
            entorno = self._entorno_exacto()

        if magnitudes.contiene_unidades(cuerpo):
            return [Paso("Cuenta con unidades",
                         "El paso a paso está para las cuentas sin unidades; "
                         "las conversiones tienen el suyo en su apartado.")]
        return cuerpo, entorno

    def pasos(self) -> list:
        """El desarrollo de la cuenta en pantalla (la hecha o la que se escribe)."""
        from .pasos_cuentas import pasos_expresion

        cuenta = self.cuenta_a_desarrollar()
        if isinstance(cuenta, list):
            return cuenta
        cuerpo, entorno = cuenta
        return pasos_expresion(cuerpo, self.modo, entorno, self.decimales)
