"""Matrices y álgebra lineal.

Las matrices se escriben como texto plano, una fila por línea y los elementos
separados por espacios o comas. Se admiten fracciones y expresiones
(``1/2``, ``sqrt(2)``, ``pi``), así que los resultados pueden darse en forma
exacta además de decimal.
"""

from __future__ import annotations

import sympy as sp

from .simbolico import ErrorSimbolico, analizar, texto

__all__ = [
    "ErrorMatriz",
    "analizar_matriz",
    "matriz_a_texto",
    "propiedades",
    "operar",
    "resolver_sistema",
    "OPERACIONES_UNARIAS",
    "OPERACIONES_BINARIAS",
]

#: Cota de tamaño: más allá, las operaciones simbólicas tardan demasiado.
MAX_DIMENSION = 12


class ErrorMatriz(ValueError):
    """La matriz o la operación no son válidas."""


def analizar_matriz(texto_matriz: str, nombre: str = "la matriz") -> sp.Matrix:
    """Convierte texto en una matriz de sympy.

    >>> analizar_matriz("1 2\\n3 4")
    Matrix([[1, 2], [3, 4]])
    """
    lineas = [l.strip() for l in texto_matriz.strip().splitlines()]
    lineas = [l for l in lineas if l]
    if not lineas:
        raise ErrorMatriz(f"Escriba los valores de {nombre}")

    filas: list[list[sp.Expr]] = []
    for numero, linea in enumerate(lineas, 1):
        # Se admiten separadores por comas, punto y coma o espacios, y corchetes.
        limpia = linea.strip().lstrip("[").rstrip("],").replace(";", " ").replace(",", " ")
        celdas = limpia.split()
        if not celdas:
            continue
        try:
            filas.append([analizar(c) for c in celdas])
        except ErrorSimbolico as e:
            raise ErrorMatriz(f"Fila {numero} de {nombre}: {e}") from None

    if not filas:
        raise ErrorMatriz(f"Escriba los valores de {nombre}")

    anchos = {len(f) for f in filas}
    if len(anchos) > 1:
        raise ErrorMatriz(
            f"Todas las filas de {nombre} deben tener el mismo número de elementos "
            f"(se encontraron filas de {sorted(anchos)})"
        )
    if len(filas) > MAX_DIMENSION or len(filas[0]) > MAX_DIMENSION:
        raise ErrorMatriz(f"El tamaño máximo admitido es {MAX_DIMENSION}×{MAX_DIMENSION}")

    return sp.Matrix(filas)


def matriz_a_texto(matriz: sp.Matrix, decimales: int = 0) -> str:
    """Formatea una matriz alineando las columnas."""
    if matriz.rows == 0 or matriz.cols == 0:
        return "(matriz vacía)"

    def celda(valor) -> str:
        if decimales:
            try:
                return texto(sp.N(valor, decimales))
            except (TypeError, ValueError):
                return texto(valor)
        return texto(valor)

    tabla = [[celda(matriz[i, j]) for j in range(matriz.cols)] for i in range(matriz.rows)]
    anchos = [max(len(fila[j]) for fila in tabla) for j in range(matriz.cols)]
    return "\n".join(
        "[ " + "  ".join(v.rjust(anchos[j]) for j, v in enumerate(fila)) + " ]"
        for fila in tabla
    )


def _exigir_cuadrada(matriz: sp.Matrix, operacion: str) -> None:
    if matriz.rows != matriz.cols:
        raise ErrorMatriz(
            f"{operacion} sólo está definida para matrices cuadradas "
            f"(esta es {matriz.rows}×{matriz.cols})"
        )


def propiedades(matriz: sp.Matrix) -> list[tuple[str, str]]:
    """Ficha completa de una matriz."""
    filas: list[tuple[str, str]] = [
        ("Dimensión", f"{matriz.rows} × {matriz.cols}"),
        ("Rango", str(matriz.rank())),
    ]

    if matriz.rows == matriz.cols:
        determinante = sp.simplify(matriz.det())
        filas.append(("Determinante", texto(determinante)))
        filas.append(("Traza", texto(sp.simplify(matriz.trace()))))
        filas.append((
            "Invertible",
            "no (determinante nulo: matriz singular)" if determinante == 0 else "sí",
        ))

        if matriz.is_symmetric():
            filas.append(("Simétrica", "sí"))
        if matriz.is_diagonal():
            filas.append(("Diagonal", "sí"))
        if matriz == sp.eye(matriz.rows):
            filas.append(("Identidad", "sí"))
    else:
        filas.append((
            "Determinante",
            "no está definido para matrices no cuadradas",
        ))

    nulidad = matriz.cols - matriz.rank()
    filas.append(("Nulidad (dim. del núcleo)", str(nulidad)))
    return filas


# --------------------------------------------------------------------------- #
# Operaciones con una sola matriz
# --------------------------------------------------------------------------- #


def _op_transpuesta(m: sp.Matrix, _p) -> list[tuple[str, str]]:
    return [("Transpuesta", matriz_a_texto(m.T))]


def _op_determinante(m: sp.Matrix, _p) -> list[tuple[str, str]]:
    _exigir_cuadrada(m, "El determinante")
    valor = sp.simplify(m.det())
    filas = [("Determinante", texto(valor))]
    try:
        filas.append(("Valor aproximado", texto(sp.N(valor, 10))))
    except (TypeError, ValueError):
        pass
    if m.rows <= 3:
        filas.append(("Interpretación",
                      "área (2×2) o volumen (3×3) con signo del paralelepípedo "
                      "que forman los vectores fila"))
    return filas


def _op_inversa(m: sp.Matrix, _p) -> list[tuple[str, str]]:
    _exigir_cuadrada(m, "La inversa")
    if sp.simplify(m.det()) == 0:
        raise ErrorMatriz(
            "La matriz es singular (determinante nulo): no tiene inversa. "
            "Puede calcular en su lugar la pseudoinversa."
        )
    inversa = sp.simplify(m.inv())
    return [
        ("Inversa (exacta)", matriz_a_texto(inversa)),
        ("Inversa (decimal)", matriz_a_texto(inversa, decimales=6)),
        ("Comprobación A·A⁻¹", matriz_a_texto(sp.simplify(m * inversa))),
    ]


def _op_pseudoinversa(m: sp.Matrix, _p) -> list[tuple[str, str]]:
    return [("Pseudoinversa de Moore-Penrose", matriz_a_texto(sp.simplify(m.pinv()), 6))]


def _op_rref(m: sp.Matrix, _p) -> list[tuple[str, str]]:
    reducida, pivotes = m.rref()
    return [
        ("Forma escalonada reducida", matriz_a_texto(sp.simplify(reducida))),
        ("Columnas pivote", ", ".join(str(p + 1) for p in pivotes) or "ninguna"),
        ("Rango", str(len(pivotes))),
    ]


def _op_potencia(m: sp.Matrix, parametros) -> list[tuple[str, str]]:
    _exigir_cuadrada(m, "La potencia")
    exponente = int(parametros.get("exponente", 2))
    if not -20 <= exponente <= 20:
        raise ErrorMatriz("El exponente debe estar entre −20 y 20")
    if exponente < 0 and sp.simplify(m.det()) == 0:
        raise ErrorMatriz("No se puede elevar a un exponente negativo una matriz singular")
    return [(f"A^{exponente}", matriz_a_texto(sp.simplify(m ** exponente)))]


def _op_autovalores(m: sp.Matrix, _p) -> list[tuple[str, str]]:
    _exigir_cuadrada(m, "El cálculo de autovalores")
    filas: list[tuple[str, str]] = [
        ("Polinomio característico", texto(sp.factor(m.charpoly().as_expr()))),
    ]

    try:
        autovalores = m.eigenvals()
    except (NotImplementedError, sp.MatrixError) as e:
        raise ErrorMatriz(f"No se pudieron calcular los autovalores: {e}") from None

    for valor, multiplicidad in autovalores.items():
        simplificado = sp.simplify(valor)
        sufijo = f"  (multiplicidad {multiplicidad})" if multiplicidad > 1 else ""
        aproximado = ""
        try:
            numerico = sp.N(simplificado, 8)
            if texto(numerico) != texto(simplificado):
                aproximado = f"   ≈ {texto(numerico)}"
        except (TypeError, ValueError):
            pass
        filas.append(("Autovalor λ", f"{texto(simplificado)}{aproximado}{sufijo}"))

    try:
        for valor, multiplicidad, vectores in m.eigenvects():
            for vector in vectores:
                filas.append((
                    f"Autovector de λ = {texto(sp.simplify(valor))}",
                    matriz_a_texto(sp.simplify(vector.T)),
                ))
    except (NotImplementedError, sp.MatrixError):
        filas.append(("Autovectores", "no se pudieron calcular"))

    try:
        if m.is_diagonalizable():
            P, D = m.diagonalize()
            filas.append(("Diagonalizable", "sí,  A = P·D·P⁻¹"))
            filas.append(("P (autovectores en columnas)", matriz_a_texto(sp.simplify(P))))
            filas.append(("D (diagonal de autovalores)", matriz_a_texto(sp.simplify(D))))
        else:
            filas.append(("Diagonalizable", "no"))
    except (NotImplementedError, sp.MatrixError):
        pass

    return filas


def _op_nucleo(m: sp.Matrix, _p) -> list[tuple[str, str]]:
    base = m.nullspace()
    if not base:
        return [("Núcleo", "sólo el vector cero (la matriz tiene rango completo por columnas)")]
    filas = [("Dimensión del núcleo", str(len(base)))]
    for i, vector in enumerate(base, 1):
        filas.append((f"Vector {i} de la base", matriz_a_texto(sp.simplify(vector.T))))
    return filas


def _op_imagen(m: sp.Matrix, _p) -> list[tuple[str, str]]:
    base = m.columnspace()
    filas = [("Dimensión de la imagen (rango)", str(len(base)))]
    for i, vector in enumerate(base, 1):
        filas.append((f"Vector {i} de la base", matriz_a_texto(sp.simplify(vector.T))))
    return filas


def _op_lu(m: sp.Matrix, _p) -> list[tuple[str, str]]:
    _exigir_cuadrada(m, "La descomposición LU")
    try:
        L, U, permutaciones = m.LUdecomposition()
    except (NotImplementedError, sp.MatrixError) as e:
        raise ErrorMatriz(f"No se pudo descomponer: {e}") from None
    return [
        ("L (triangular inferior)", matriz_a_texto(sp.simplify(L))),
        ("U (triangular superior)", matriz_a_texto(sp.simplify(U))),
        ("Permutaciones de filas", str(permutaciones) if permutaciones else "ninguna"),
    ]


# --------------------------------------------------------------------------- #
# Operaciones con dos matrices
# --------------------------------------------------------------------------- #


def _op_sumar(a: sp.Matrix, b: sp.Matrix) -> list[tuple[str, str]]:
    if a.shape != b.shape:
        raise ErrorMatriz(
            f"Para sumar, las dos matrices deben tener la misma dimensión "
            f"(A es {a.rows}×{a.cols} y B es {b.rows}×{b.cols})"
        )
    return [("A + B", matriz_a_texto(sp.simplify(a + b)))]


def _op_restar(a: sp.Matrix, b: sp.Matrix) -> list[tuple[str, str]]:
    if a.shape != b.shape:
        raise ErrorMatriz(
            f"Para restar, las dos matrices deben tener la misma dimensión "
            f"(A es {a.rows}×{a.cols} y B es {b.rows}×{b.cols})"
        )
    return [("A − B", matriz_a_texto(sp.simplify(a - b)))]


def _op_multiplicar(a: sp.Matrix, b: sp.Matrix) -> list[tuple[str, str]]:
    if a.cols != b.rows:
        raise ErrorMatriz(
            f"Para multiplicar A·B, las columnas de A ({a.cols}) deben coincidir "
            f"con las filas de B ({b.rows})"
        )
    producto = sp.simplify(a * b)
    filas = [("A · B", matriz_a_texto(producto))]
    if b.cols == a.rows:
        filas.append(("B · A", matriz_a_texto(sp.simplify(b * a))))
        filas.append((
            "¿Conmutan?",
            "sí" if sp.simplify(a * b - b * a) == sp.zeros(a.rows, b.cols) else
            "no (el producto de matrices no es conmutativo)",
        ))
    return filas


def _op_producto_elemento(a: sp.Matrix, b: sp.Matrix) -> list[tuple[str, str]]:
    if a.shape != b.shape:
        raise ErrorMatriz("El producto elemento a elemento exige la misma dimensión")
    return [("A ∘ B (Hadamard)", matriz_a_texto(sp.simplify(a.multiply_elementwise(b))))]


def resolver_sistema(coeficientes: sp.Matrix, terminos: sp.Matrix) -> list[tuple[str, str]]:
    """Resuelve A·x = b y clasifica el sistema."""
    if coeficientes.rows != terminos.rows:
        raise ErrorMatriz(
            f"A tiene {coeficientes.rows} filas y b tiene {terminos.rows}: deben coincidir"
        )
    if terminos.cols != 1:
        terminos = terminos.reshape(terminos.rows * terminos.cols, 1)

    ampliada = coeficientes.row_join(terminos)
    rango = coeficientes.rank()
    rango_ampliada = ampliada.rank()
    incognitas = coeficientes.cols

    filas = [
        ("Matriz ampliada", matriz_a_texto(ampliada)),
        ("Rango de A", str(rango)),
        ("Rango de (A|b)", str(rango_ampliada)),
        ("Número de incógnitas", str(incognitas)),
    ]

    if rango < rango_ampliada:
        filas.append(("Clasificación", "SISTEMA INCOMPATIBLE: no tiene solución"))
        return filas

    simbolos = sp.symbols(f"x1:{incognitas + 1}")
    solucion = sp.linsolve((coeficientes, terminos), simbolos)
    if not solucion:
        filas.append(("Clasificación", "sin solución"))
        return filas

    tupla = next(iter(solucion))
    libres = sorted({str(s) for expresion in tupla for s in expresion.free_symbols})

    if rango == incognitas and not libres:
        filas.append(("Clasificación", "COMPATIBLE DETERMINADO: solución única"))
        for simbolo, valor in zip(simbolos, tupla):
            exacto = texto(sp.simplify(valor))
            aproximado = texto(sp.N(valor, 8))
            filas.append((
                str(simbolo),
                exacto if exacto == aproximado else f"{aproximado}   (exacto: {exacto})",
            ))
    else:
        grados = incognitas - rango
        filas.append((
            "Clasificación",
            f"COMPATIBLE INDETERMINADO: infinitas soluciones ({grados} "
            f"grado{'s' if grados != 1 else ''} de libertad)",
        ))
        for simbolo, valor in zip(simbolos, tupla):
            filas.append((str(simbolo), texto(sp.simplify(valor))))
        if libres:
            filas.append(("Parámetros libres", ", ".join(libres)))

    return filas


#: (clave, título, ¿necesita parámetro extra?)
OPERACIONES_UNARIAS = [
    ("propiedades", "Propiedades generales", None),
    ("transpuesta", "Transpuesta", None),
    ("determinante", "Determinante", None),
    ("inversa", "Inversa", None),
    ("pseudoinversa", "Pseudoinversa", None),
    ("rref", "Forma escalonada reducida (Gauss-Jordan)", None),
    ("potencia", "Potencia Aⁿ", "exponente"),
    ("autovalores", "Autovalores y autovectores", None),
    ("nucleo", "Núcleo (kernel)", None),
    ("imagen", "Imagen (espacio columna)", None),
    ("lu", "Descomposición LU", None),
]

OPERACIONES_BINARIAS = [
    ("sumar", "A + B"),
    ("restar", "A − B"),
    ("multiplicar", "A · B"),
    ("hadamard", "A ∘ B (elemento a elemento)"),
    ("sistema", "Resolver A·x = b"),
]

_UNARIAS = {
    "propiedades": lambda m, p: propiedades(m),
    "transpuesta": _op_transpuesta,
    "determinante": _op_determinante,
    "inversa": _op_inversa,
    "pseudoinversa": _op_pseudoinversa,
    "rref": _op_rref,
    "potencia": _op_potencia,
    "autovalores": _op_autovalores,
    "nucleo": _op_nucleo,
    "imagen": _op_imagen,
    "lu": _op_lu,
}

_BINARIAS = {
    "sumar": _op_sumar,
    "restar": _op_restar,
    "multiplicar": _op_multiplicar,
    "hadamard": _op_producto_elemento,
    "sistema": resolver_sistema,
}


def operar(clave: str, a: sp.Matrix, b: sp.Matrix | None = None,
           parametros: dict | None = None) -> list[tuple[str, str]]:
    """Aplica la operación indicada y devuelve las filas de resultado."""
    parametros = parametros or {}

    if clave in _UNARIAS:
        return _UNARIAS[clave](a, parametros)

    if clave in _BINARIAS:
        if b is None:
            raise ErrorMatriz("Esta operación necesita una segunda matriz")
        return _BINARIAS[clave](a, b)

    raise ErrorMatriz(f"Operación desconocida: {clave!r}")
