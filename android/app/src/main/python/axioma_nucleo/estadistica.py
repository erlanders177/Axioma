"""Estadística descriptiva, regresión y distribuciones de probabilidad.

Los datos se escriben separados por comas, espacios o saltos de línea, así que
se puede pegar directamente una columna de una hoja de cálculo.
"""

from __future__ import annotations

import math
import statistics as est
from collections import Counter

__all__ = [
    "ErrorEstadistica",
    "analizar_datos",
    "descriptiva",
    "tabla_frecuencias",
    "regresion_lineal",
    "correlacion",
    "normal",
    "binomial",
    "poisson",
    "DISTRIBUCIONES",
]

MAX_DATOS = 100_000


class ErrorEstadistica(ValueError):
    """Los datos o los parámetros no son válidos."""


def analizar_datos(texto: str, nombre: str = "los datos") -> list[float]:
    """Convierte texto en una lista de números.

    Acepta comas, punto y coma, espacios y saltos de línea como separadores, y
    la coma decimal si no se usa como separador de elementos.
    """
    limpio = texto.strip()
    if not limpio:
        raise ErrorEstadistica(f"Introduzca {nombre}")

    # La coma es ambigua en castellano: puede separar elementos («1, 2, 3») o
    # ser el separador decimal («1,5»). Se decide así:
    normalizado = limpio.replace(";", " ").replace("\n", " ").replace("\t", " ")

    if "." in normalizado:
        # Hay puntos, así que los decimales usan punto y las comas separan.
        partes = [p for p in normalizado.replace(",", " ").split() if p]
    else:
        tokens = [t for t in normalizado.split() if t]
        decimal = bool(tokens) and all(
            t.count(",") == 1 and not t.startswith(",") and not t.endswith(",")
            for t in tokens
        )
        if decimal:
            # «1,5  2,5» — cada elemento lleva exactamente una coma interior.
            partes = [t.replace(",", ".") for t in tokens]
        else:
            partes = [p for p in normalizado.replace(",", " ").split() if p]

    valores: list[float] = []
    for parte in partes:
        try:
            valores.append(float(parte))
        except ValueError:
            raise ErrorEstadistica(f"«{parte}» no es un número válido") from None

    if not valores:
        raise ErrorEstadistica(f"Introduzca {nombre}")
    if len(valores) > MAX_DATOS:
        raise ErrorEstadistica(f"Demasiados datos (máximo {MAX_DATOS})")
    return valores


def _fmt(valor: float, decimales: int = 6) -> str:
    from .formato import formatear
    return formatear(valor, decimales)


def descriptiva(datos: list[float], decimales: int = 6) -> list[tuple[str, str]]:
    """Resumen estadístico completo de una muestra."""
    n = len(datos)
    ordenados = sorted(datos)
    suma = math.fsum(datos)
    media = suma / n

    filas: list[tuple[str, str]] = [
        ("Número de datos (n)", str(n)),
        ("Suma", _fmt(suma, decimales)),
        ("Mínimo", _fmt(ordenados[0], decimales)),
        ("Máximo", _fmt(ordenados[-1], decimales)),
        ("Rango", _fmt(ordenados[-1] - ordenados[0], decimales)),
        ("", ""),
        ("Media aritmética", _fmt(media, decimales)),
        ("Mediana", _fmt(est.median(ordenados), decimales)),
    ]

    conteo = Counter(datos)
    maximo = max(conteo.values())
    if maximo == 1:
        filas.append(("Moda", "no hay: ningún valor se repite"))
    else:
        modas = sorted(v for v, c in conteo.items() if c == maximo)
        etiqueta = "Moda" if len(modas) == 1 else f"Modas ({len(modas)})"
        filas.append((etiqueta, ", ".join(_fmt(m, decimales) for m in modas[:10])))

    if all(v > 0 for v in datos):
        filas.append(("Media geométrica", _fmt(math.exp(math.fsum(math.log(v) for v in datos) / n), decimales)))
        filas.append(("Media armónica", _fmt(n / math.fsum(1 / v for v in datos), decimales)))

    filas.append(("", ""))

    if n >= 2:
        varianza_muestral = est.variance(datos, media)
        desviacion_muestral = math.sqrt(varianza_muestral)
        filas.append(("Varianza muestral (n−1)", _fmt(varianza_muestral, decimales)))
        filas.append(("Desviación típica muestral", _fmt(desviacion_muestral, decimales)))
    else:
        desviacion_muestral = 0.0
        filas.append(("Varianza muestral", "hacen falta al menos 2 datos"))

    varianza_poblacional = est.pvariance(datos, media)
    desviacion_poblacional = math.sqrt(varianza_poblacional)
    filas.append(("Varianza poblacional (n)", _fmt(varianza_poblacional, decimales)))
    filas.append(("Desviación típica poblacional", _fmt(desviacion_poblacional, decimales)))

    if media != 0:
        filas.append(("Coeficiente de variación", _fmt(desviacion_poblacional / abs(media) * 100, 4) + " %"))
    if n >= 2:
        filas.append(("Error típico de la media", _fmt(desviacion_muestral / math.sqrt(n), decimales)))

    filas.append(("", ""))

    q1, q2, q3 = _cuartiles(ordenados)
    filas.append(("Primer cuartil Q1", _fmt(q1, decimales)))
    filas.append(("Segundo cuartil Q2 (mediana)", _fmt(q2, decimales)))
    filas.append(("Tercer cuartil Q3", _fmt(q3, decimales)))
    filas.append(("Rango intercuartílico (IQR)", _fmt(q3 - q1, decimales)))

    # Regla del bigote de Tukey: 1,5·IQR fuera de los cuartiles.
    iqr = q3 - q1
    bajo, alto = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    atipicos = [v for v in ordenados if v < bajo or v > alto]
    filas.append((
        "Valores atípicos (criterio 1,5·IQR)",
        ", ".join(_fmt(v, decimales) for v in atipicos[:12]) if atipicos else "ninguno",
    ))

    if desviacion_poblacional > 0 and n >= 3:
        filas.append(("", ""))
        asimetria = math.fsum(((v - media) / desviacion_poblacional) ** 3 for v in datos) / n
        curtosis = math.fsum(((v - media) / desviacion_poblacional) ** 4 for v in datos) / n - 3
        filas.append(("Asimetría (Fisher)", _fmt(asimetria, 6)))
        filas.append((
            "  interpretación",
            "simétrica" if abs(asimetria) < 0.5
            else ("cola hacia la derecha" if asimetria > 0 else "cola hacia la izquierda"),
        ))
        filas.append(("Curtosis (exceso)", _fmt(curtosis, 6)))
        filas.append((
            "  interpretación",
            "similar a la normal" if abs(curtosis) < 0.5
            else ("más apuntada que la normal" if curtosis > 0 else "más plana que la normal"),
        ))

    return filas


def _cuartiles(ordenados: list[float]) -> tuple[float, float, float]:
    """Cuartiles por interpolación lineal (el método más habitual)."""
    n = len(ordenados)
    if n == 1:
        valor = ordenados[0]
        return valor, valor, valor

    def percentil(p: float) -> float:
        posicion = p * (n - 1)
        inferior = math.floor(posicion)
        superior = math.ceil(posicion)
        if inferior == superior:
            return ordenados[int(posicion)]
        peso = posicion - inferior
        return ordenados[inferior] * (1 - peso) + ordenados[superior] * peso

    return percentil(0.25), percentil(0.5), percentil(0.75)


def tabla_frecuencias(datos: list[float], decimales: int = 6) -> list[tuple[str, str]]:
    """Frecuencias absolutas, relativas y acumuladas."""
    n = len(datos)
    conteo = Counter(datos)
    filas: list[tuple[str, str]] = [
        ("Valor", "fᵢ    ·   hᵢ (%)   ·   Fᵢ acumulada"),
    ]
    acumulada = 0
    for valor in sorted(conteo):
        frecuencia = conteo[valor]
        acumulada += frecuencia
        filas.append((
            _fmt(valor, decimales),
            f"{frecuencia}    ·   {frecuencia / n * 100:.2f} %   ·   {acumulada}",
        ))
    filas.append(("Total", f"{n}    ·   100,00 %"))
    return filas


def regresion_lineal(x: list[float], y: list[float], decimales: int = 6) -> list[tuple[str, str]]:
    """Ajuste por mínimos cuadrados y = a·x + b."""
    if len(x) != len(y):
        raise ErrorEstadistica(
            f"Las dos series deben tener el mismo número de datos "
            f"(X tiene {len(x)} e Y tiene {len(y)})"
        )
    n = len(x)
    if n < 2:
        raise ErrorEstadistica("Hacen falta al menos 2 pares de datos")

    media_x = math.fsum(x) / n
    media_y = math.fsum(y) / n
    sxx = math.fsum((v - media_x) ** 2 for v in x)
    syy = math.fsum((v - media_y) ** 2 for v in y)
    sxy = math.fsum((a - media_x) * (b - media_y) for a, b in zip(x, y))

    if sxx == 0:
        raise ErrorEstadistica(
            "Todos los valores de X son iguales: la recta de regresión sería vertical"
        )

    pendiente = sxy / sxx
    ordenada = media_y - pendiente * media_x
    r = sxy / math.sqrt(sxx * syy) if syy > 0 else 0.0

    signo = "+" if ordenada >= 0 else "−"
    filas = [
        ("Número de pares", str(n)),
        ("Recta de regresión", f"y = {_fmt(pendiente, decimales)}·x {signo} {_fmt(abs(ordenada), decimales)}"),
        ("Pendiente (a)", _fmt(pendiente, decimales)),
        ("Ordenada en el origen (b)", _fmt(ordenada, decimales)),
        ("", ""),
        ("Covarianza", _fmt(sxy / n, decimales)),
        ("Coeficiente de correlación r", _fmt(r, decimales)),
        ("Coeficiente de determinación r²", _fmt(r * r, decimales)),
        ("  interpretación", _interpretar_r(r)),
        ("", ""),
        ("Media de X", _fmt(media_x, decimales)),
        ("Media de Y", _fmt(media_y, decimales)),
    ]

    if n > 2 and syy > 0:
        residuos = math.fsum((b - (pendiente * a + ordenada)) ** 2 for a, b in zip(x, y))
        filas.append(("Error típico de la estimación", _fmt(math.sqrt(residuos / (n - 2)), decimales)))

    return filas


def _interpretar_r(r: float) -> str:
    magnitud = abs(r)
    if magnitud >= 0.9:
        fuerza = "muy fuerte"
    elif magnitud >= 0.7:
        fuerza = "fuerte"
    elif magnitud >= 0.4:
        fuerza = "moderada"
    elif magnitud >= 0.2:
        fuerza = "débil"
    else:
        return "prácticamente no hay relación lineal"
    sentido = "directa (crecen juntas)" if r > 0 else "inversa (una sube, la otra baja)"
    return f"correlación {fuerza} y {sentido}"


def correlacion(x: list[float], y: list[float], decimales: int = 6) -> list[tuple[str, str]]:
    """Sólo los coeficientes de correlación, sin la recta."""
    return [f for f in regresion_lineal(x, y, decimales)
            if f[0] in ("Covarianza", "Coeficiente de correlación r",
                        "Coeficiente de determinación r²", "  interpretación")]


# --------------------------------------------------------------------------- #
# Distribuciones de probabilidad
# --------------------------------------------------------------------------- #


def _fi_normal(z: float) -> float:
    """Función de distribución acumulada de la normal tipificada."""
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def normal(media: float, desviacion: float, valor: float,
           decimales: int = 6) -> list[tuple[str, str]]:
    """Probabilidades de una distribución normal N(μ, σ)."""
    if desviacion <= 0:
        raise ErrorEstadistica("La desviación típica debe ser positiva")

    z = (valor - media) / desviacion
    acumulada = _fi_normal(z)
    densidad = math.exp(-0.5 * z * z) / (desviacion * math.sqrt(2 * math.pi))

    return [
        ("Distribución", f"N(μ = {_fmt(media, decimales)}, σ = {_fmt(desviacion, decimales)})"),
        ("Valor x", _fmt(valor, decimales)),
        ("Puntuación típica z", _fmt(z, decimales)),
        ("", ""),
        ("Densidad f(x)", _fmt(densidad, decimales)),
        ("P(X ≤ x)", _fmt(acumulada, decimales)),
        ("P(X > x)", _fmt(1 - acumulada, decimales)),
        ("P(μ−|z|σ ≤ X ≤ μ+|z|σ)", _fmt(abs(2 * _fi_normal(abs(z)) - 1), decimales)),
        ("", ""),
        ("Varianza", _fmt(desviacion ** 2, decimales)),
        ("Percentil de x", _fmt(acumulada * 100, 4) + " %"),
    ]


def binomial(n: int, p: float, k: int, decimales: int = 6) -> list[tuple[str, str]]:
    """Probabilidades de una distribución binomial B(n, p)."""
    if n < 0 or n > 100_000:
        raise ErrorEstadistica("n debe estar entre 0 y 100 000")
    if not 0 <= p <= 1:
        raise ErrorEstadistica("La probabilidad p debe estar entre 0 y 1")
    if not 0 <= k <= n:
        raise ErrorEstadistica(f"k debe estar entre 0 y n ({n})")

    exacta = math.comb(n, k) * (p ** k) * ((1 - p) ** (n - k))
    acumulada = math.fsum(
        math.comb(n, i) * (p ** i) * ((1 - p) ** (n - i)) for i in range(k + 1)
    )

    return [
        ("Distribución", f"B(n = {n}, p = {_fmt(p, decimales)})"),
        ("", ""),
        ("P(X = k)", _fmt(exacta, decimales)),
        ("P(X ≤ k)", _fmt(acumulada, decimales)),
        ("P(X < k)", _fmt(acumulada - exacta, decimales)),
        ("P(X ≥ k)", _fmt(1 - acumulada + exacta, decimales)),
        ("P(X > k)", _fmt(1 - acumulada, decimales)),
        ("", ""),
        ("Media (n·p)", _fmt(n * p, decimales)),
        ("Varianza (n·p·q)", _fmt(n * p * (1 - p), decimales)),
        ("Desviación típica", _fmt(math.sqrt(n * p * (1 - p)), decimales)),
        ("Moda", str(math.floor((n + 1) * p))),
    ]


def poisson(lam: float, k: int, decimales: int = 6) -> list[tuple[str, str]]:
    """Probabilidades de una distribución de Poisson P(λ)."""
    if lam <= 0:
        raise ErrorEstadistica("λ debe ser positivo")
    if lam > 1000:
        raise ErrorEstadistica("λ demasiado grande (máximo 1000)")
    if k < 0 or k > 10_000:
        raise ErrorEstadistica("k debe estar entre 0 y 10 000")

    def probabilidad(i: int) -> float:
        # Se calcula con logaritmos para no desbordar con λ o k grandes.
        return math.exp(-lam + i * math.log(lam) - math.lgamma(i + 1))

    exacta = probabilidad(k)
    acumulada = math.fsum(probabilidad(i) for i in range(k + 1))

    return [
        ("Distribución", f"P(λ = {_fmt(lam, decimales)})"),
        ("", ""),
        ("P(X = k)", _fmt(exacta, decimales)),
        ("P(X ≤ k)", _fmt(min(1.0, acumulada), decimales)),
        ("P(X < k)", _fmt(max(0.0, acumulada - exacta), decimales)),
        ("P(X ≥ k)", _fmt(max(0.0, 1 - acumulada + exacta), decimales)),
        ("P(X > k)", _fmt(max(0.0, 1 - acumulada), decimales)),
        ("", ""),
        ("Media", _fmt(lam, decimales)),
        ("Varianza", _fmt(lam, decimales)),
        ("Desviación típica", _fmt(math.sqrt(lam), decimales)),
    ]


#: (clave, título, etiquetas de los campos)
DISTRIBUCIONES = [
    ("normal", "Normal N(μ, σ)", ["media (μ)", "desviación (σ)", "valor (x)"]),
    ("binomial", "Binomial B(n, p)", ["ensayos (n)", "probabilidad (p)", "éxitos (k)"]),
    ("poisson", "Poisson P(λ)", ["media (λ)", "sucesos (k)"]),
]
