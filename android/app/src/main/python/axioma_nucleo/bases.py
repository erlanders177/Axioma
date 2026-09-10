"""Conversión entre bases numéricas (2 a 36).

Mejoras respecto a la versión anterior, que usaba ``int(numero, base)``:

* Acepta **signo negativo** (antes ``-1010`` fallaba en la validación de dígitos).
* Acepta **parte fraccionaria** (``101.101`` en binario).
* Acepta separadores de agrupación (``_`` y espacios) y los prefijos habituales
  ``0x``, ``0b``, ``0o``.
* Da información extra útil: representación en las bases habituales, número de
  dígitos, y para los enteros el complemento a dos y el desglose posicional.
"""

from __future__ import annotations

DIGITOS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE_MINIMA = 2
BASE_MAXIMA = 36

#: Precisión máxima de la parte fraccionaria, en dígitos de la base destino.
MAX_DECIMALES = 30

PREFIJOS = {"0X": 16, "0B": 2, "0O": 8, "0D": 10}

NOMBRES_BASE = {
    2: "binario", 8: "octal", 10: "decimal", 16: "hexadecimal",
    3: "ternario", 4: "cuaternario", 5: "quinario", 12: "duodecimal",
    20: "vigesimal", 32: "base 32", 36: "base 36",
}


class ErrorBase(ValueError):
    """El número o la base indicados no son válidos."""


def nombre_base(base: int) -> str:
    nombre = NOMBRES_BASE.get(base)
    return f"base {base} ({nombre})" if nombre else f"base {base}"


def _validar_base(base: int, etiqueta: str) -> int:
    if not isinstance(base, int) or not (BASE_MINIMA <= base <= BASE_MAXIMA):
        raise ErrorBase(f"La {etiqueta} debe estar entre {BASE_MINIMA} y {BASE_MAXIMA}")
    return base


def limpiar(texto: str, base: int) -> tuple[int, str, str]:
    """Normaliza la entrada y la separa en (signo, parte entera, parte fraccionaria).

    Devuelve los dígitos en mayúsculas, sin separadores ni prefijo.
    """
    limpio = texto.strip().upper().replace("_", "").replace(" ", "")
    if not limpio:
        raise ErrorBase("Introduzca un número")

    signo = 1
    if limpio[0] in "+-":
        signo = -1 if limpio[0] == "-" else 1
        limpio = limpio[1:]

    # Prefijos: sólo se aceptan si coinciden con la base indicada.
    if len(limpio) > 2 and limpio[:2] in PREFIJOS:
        if PREFIJOS[limpio[:2]] != base:
            raise ErrorBase(
                f"El prefijo «{limpio[:2].lower()}» corresponde a "
                f"base {PREFIJOS[limpio[:2]]}, no a base {base}"
            )
        limpio = limpio[2:]

    limpio = limpio.replace(",", ".")
    if limpio.count(".") > 1:
        raise ErrorBase("El número tiene más de un separador decimal")

    entera, _, fraccionaria = limpio.partition(".")
    if not entera and not fraccionaria:
        raise ErrorBase("Introduzca un número")

    validos = DIGITOS[:base]
    for parte in (entera, fraccionaria):
        for digito in parte:
            if digito not in validos:
                permitidos = validos if base <= 16 else f"0-9 y A-{validos[-1]}"
                raise ErrorBase(
                    f"El dígito «{digito}» no existe en {nombre_base(base)}. "
                    f"Dígitos permitidos: {permitidos}"
                )

    return signo, entera or "0", fraccionaria


def a_decimal(texto: str, base: int) -> float | int:
    """Convierte ``texto`` (en ``base``) a un número decimal de Python.

    Devuelve ``int`` si no hay parte fraccionaria, para no perder precisión con
    números grandes.
    """
    _validar_base(base, "base de origen")
    signo, entera, fraccionaria = limpiar(texto, base)

    valor_entero = int(entera, base) if entera else 0
    if not fraccionaria:
        return signo * valor_entero

    valor_frac = 0.0
    for posicion, digito in enumerate(fraccionaria, start=1):
        valor_frac += DIGITOS.index(digito) / (base ** posicion)
    return signo * (valor_entero + valor_frac)


def desde_decimal(valor: float | int, base: int, decimales: int = 12) -> str:
    """Representa ``valor`` (decimal) en ``base``."""
    _validar_base(base, "base de destino")
    decimales = max(0, min(MAX_DECIMALES, int(decimales)))

    negativo = valor < 0
    valor = abs(valor)

    if isinstance(valor, int):
        entero, fraccion = valor, 0.0
    else:
        entero = int(valor)
        fraccion = valor - entero

    texto = _entero_a_base(entero, base)

    if fraccion > 0 and decimales > 0:
        digitos = []
        resto = fraccion
        for _ in range(decimales):
            resto *= base
            digito = int(resto)
            digitos.append(DIGITOS[digito])
            resto -= digito
            if resto <= 0:
                break
        # Redondeo del último dígito si queda resto significativo.
        if resto >= 0.5 and digitos:
            digitos = _redondear_fraccion(digitos, base)
        texto += "." + "".join(digitos).rstrip("0")
        texto = texto.rstrip(".")

    return ("-" if negativo else "") + texto


def _entero_a_base(entero: int, base: int) -> str:
    if entero == 0:
        return "0"
    digitos: list[str] = []
    while entero > 0:
        entero, resto = divmod(entero, base)
        digitos.append(DIGITOS[resto])
    return "".join(reversed(digitos))


def _redondear_fraccion(digitos: list[str], base: int) -> list[str]:
    """Suma 1 al último dígito propagando el acarreo."""
    resultado = list(digitos)
    i = len(resultado) - 1
    while i >= 0:
        indice = DIGITOS.index(resultado[i]) + 1
        if indice < base:
            resultado[i] = DIGITOS[indice]
            return resultado
        resultado[i] = "0"
        i -= 1
    return resultado


def convertir(texto: str, base_origen: int, base_destino: int, decimales: int = 12) -> str:
    """Convierte ``texto`` de ``base_origen`` a ``base_destino``."""
    _validar_base(base_origen, "base de origen")
    _validar_base(base_destino, "base de destino")
    return desde_decimal(a_decimal(texto, base_origen), base_destino, decimales)


def tabla_bases(texto: str, base_origen: int, decimales: int = 12) -> list[tuple[int, str]]:
    """Representación del número en las bases de uso habitual."""
    valor = a_decimal(texto, base_origen)
    return [(base, desde_decimal(valor, base, decimales)) for base in (2, 8, 10, 16)]


def desglose_posicional(texto: str, base: int, max_terminos: int = 24) -> str:
    """Explica el valor como suma de potencias, p. ej. ``1·2³ + 0·2² + 1·2¹``."""
    signo, entera, fraccionaria = limpiar(texto, base)
    terminos: list[str] = []

    for i, digito in enumerate(entera):
        exponente = len(entera) - 1 - i
        terminos.append(f"{DIGITOS.index(digito)}·{base}^{exponente}")
    for i, digito in enumerate(fraccionaria, start=1):
        terminos.append(f"{DIGITOS.index(digito)}·{base}^-{i}")

    if len(terminos) > max_terminos:
        terminos = terminos[:max_terminos] + ["…"]

    prefijo = "-(" if signo < 0 else ""
    sufijo = ")" if signo < 0 else ""
    return prefijo + " + ".join(terminos) + sufijo


#: Operaciones bit a bit disponibles. El segundo operando de NOT se ignora.
OPERACIONES_BITS = ["AND", "OR", "XOR", "NOT", "<<", ">>"]

#: Anchos de palabra para mostrar el resultado en binario.
ANCHOS = (8, 16, 32, 64)

MAX_DESPLAZAMIENTO = 512


def operacion_bits(operacion: str, a: int, b: int = 0,
                   ancho: int | None = None) -> list[tuple[str, str]]:
    """Aplica una operación bit a bit y muestra el resultado en varias bases.

    ``ancho`` fija los bits de la palabra; si es ``None`` se elige el menor de
    8/16/32/64 que quepa. Con NOT hace falta un ancho, porque ``~x`` sobre
    enteros de precisión arbitraria daría infinitos unos a la izquierda.
    """
    if operacion not in OPERACIONES_BITS:
        raise ErrorBase(f"Operación desconocida: {operacion!r}")
    if a < 0 or b < 0:
        raise ErrorBase("Las operaciones bit a bit sólo admiten enteros no negativos")

    if ancho is None:
        necesarios = max(a.bit_length(), b.bit_length() if operacion in ("AND", "OR", "XOR") else 0, 1)
        if operacion == "<<":
            necesarios += b
        ancho = next((w for w in ANCHOS if necesarios <= w), None)
        if ancho is None:
            raise ErrorBase("Los operandos no caben en una palabra de 64 bits")

    mascara = (1 << ancho) - 1

    if operacion in ("<<", ">>"):
        if b > MAX_DESPLAZAMIENTO:
            raise ErrorBase(f"El desplazamiento máximo es {MAX_DESPLAZAMIENTO}")
        resultado = (a << b) & mascara if operacion == "<<" else (a >> b)
    elif operacion == "AND":
        resultado = a & b
    elif operacion == "OR":
        resultado = a | b
    elif operacion == "XOR":
        resultado = a ^ b
    else:  # NOT
        resultado = (~a) & mascara

    def binario(valor: int) -> str:
        return _agrupar_bits(format(valor & mascara, f"0{ancho}b"))

    filas: list[tuple[str, str]] = [("Palabra", f"{ancho} bits")]

    if operacion == "NOT":
        filas.append(("A  (binario)", binario(a)))
        filas.append(("NOT A", binario(resultado)))
    elif operacion in ("<<", ">>"):
        filas.append(("A  (binario)", binario(a)))
        filas.append((f"A {operacion} {b}", binario(resultado)))
    else:
        filas.append(("A  (binario)", binario(a)))
        filas.append(("B  (binario)", binario(b)))
        filas.append((f"A {operacion} B", binario(resultado)))

    filas.append(("", ""))
    filas.append(("Resultado (decimal)", str(resultado)))
    filas.append(("Resultado (hexadecimal)", format(resultado & mascara, f"0{max(1, ancho // 4)}X")))
    filas.append(("Resultado (octal)", _entero_a_base(resultado, 8)))
    filas.append(("Bits a 1", str(bin(resultado & mascara).count("1"))))
    return filas


def _agrupar_bits(binario: str, tamano: int = 4) -> str:
    """Agrupa los bits de cuatro en cuatro para poder leerlos."""
    resto = len(binario) % tamano
    grupos = ([binario[:resto]] if resto else []) + [
        binario[i:i + tamano] for i in range(resto, len(binario), tamano)
    ]
    return " ".join(g for g in grupos if g)


def info_entero(valor: int) -> list[tuple[str, str]]:
    """Datos de interés para un entero: bits necesarios, complemento a dos, etc."""
    datos: list[tuple[str, str]] = []
    magnitud = abs(valor)
    necesarios = magnitud.bit_length() or 1
    datos.append(("Bits necesarios (magnitud)", str(necesarios)))

    if valor >= 0:
        datos.append(("Binario", _entero_a_base(magnitud, 2)))
    else:
        datos.append(("Binario (magnitud)", _entero_a_base(magnitud, 2)))

    for ancho in (8, 16, 32, 64):
        if necesarios + (1 if valor < 0 else 0) <= ancho:
            complemento = valor & ((1 << ancho) - 1)
            datos.append((
                f"Complemento a dos ({ancho} bits)",
                format(complemento, f"0{ancho}b"),
            ))
            datos.append((f"Hexadecimal ({ancho} bits)", format(complemento, f"0{ancho // 4}X")))
            break
    else:
        datos.append(("Complemento a dos", "el número excede los 64 bits"))

    if valor >= 0:
        datos.append(("Bits a 1 (población)", str(bin(magnitud).count("1"))))
    return datos
