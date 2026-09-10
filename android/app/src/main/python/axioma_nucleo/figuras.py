"""Catálogo de figuras geométricas planas y cuerpos en el espacio.

Cada figura declara:

* los **parámetros** que pide (con su símbolo, etiqueta y validación),
* una función de **cálculo** que devuelve la lista de resultados,
* las **fórmulas** que aplica, para mostrarlas junto al resultado,
* opcionalmente una función de **forma**, que describe cómo dibujarla en
  primitivas independientes de la biblioteca de gráficos.

Las unidades son genéricas (``u``, ``u²``, ``u³``): la figura no sabe si el
usuario está trabajando en metros o pulgadas, sólo mantiene la coherencia
dimensional.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

__all__ = [
    "ErrorFigura",
    "Parametro",
    "Resultado",
    "Figura",
    "FIGURAS",
    "GRUPOS",
    "figura",
    "calcular",
]

TAU = math.tau


class ErrorFigura(ValueError):
    """Los datos introducidos no describen una figura válida."""


# --------------------------------------------------------------------------- #
# Estructuras
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Parametro:
    simbolo: str
    etiqueta: str
    unidad: str = "u"
    minimo: float = 0.0
    maximo: float = math.inf
    entero: bool = False
    predeterminado: float = 0.0
    ayuda: str = ""

    def validar(self, valor: float) -> float:
        if self.entero:
            if abs(valor - round(valor)) > 1e-9:
                raise ErrorFigura(f"«{self.etiqueta}» debe ser un número entero")
            valor = float(round(valor))
        if valor <= self.minimo:
            raise ErrorFigura(f"«{self.etiqueta}» debe ser mayor que {_num(self.minimo)}")
        if valor > self.maximo:
            raise ErrorFigura(f"«{self.etiqueta}» debe ser como máximo {_num(self.maximo)}")
        return valor


@dataclass(frozen=True)
class Resultado:
    etiqueta: str
    valor: float
    unidad: str = ""


# Primitivas de dibujo: describen la figura sin depender de matplotlib.
@dataclass(frozen=True)
class Poligono:
    puntos: tuple[tuple[float, float], ...]
    relleno: bool = True


@dataclass(frozen=True)
class Circulo:
    centro: tuple[float, float]
    radio: float
    relleno: bool = True


@dataclass(frozen=True)
class Elipse:
    centro: tuple[float, float]
    semieje_a: float
    semieje_b: float
    relleno: bool = True


@dataclass(frozen=True)
class Sector:
    centro: tuple[float, float]
    radio: float
    desde: float          # grados
    hasta: float          # grados
    relleno: bool = True


@dataclass(frozen=True)
class Linea:
    puntos: tuple[tuple[float, float], ...]
    discontinua: bool = True


@dataclass(frozen=True)
class Solido:
    """Cuerpo en 3D; el visualizador sabe generar la malla a partir del tipo."""
    tipo: str
    parametros: dict


Primitiva = Poligono | Circulo | Elipse | Sector | Linea | Solido


@dataclass(frozen=True)
class Figura:
    nombre: str
    grupo: str
    parametros: tuple[Parametro, ...]
    calculo: Callable[[dict], list[Resultado]]
    formulas: tuple[str, ...] = ()
    forma: Callable[[dict], list] | None = None
    nota: str = ""
    _indice: dict = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_indice", {p.simbolo: p for p in self.parametros})

    def validar(self, valores: dict) -> dict:
        """Comprueba que están todos los parámetros y que son válidos."""
        limpios = {}
        for p in self.parametros:
            if p.simbolo not in valores or valores[p.simbolo] is None:
                raise ErrorFigura(f"Falta el valor de «{p.etiqueta}»")
            limpios[p.simbolo] = p.validar(float(valores[p.simbolo]))
        return limpios

    def calcular(self, valores: dict) -> list[Resultado]:
        return self.calculo(self.validar(valores))

    def primitivas(self, valores: dict) -> list:
        if self.forma is None:
            return []
        return self.forma(self.validar(valores))


def _num(valor: float) -> str:
    return str(int(valor)) if float(valor).is_integer() else f"{valor:g}"


def P(simbolo: str, etiqueta: str, **kwargs) -> Parametro:
    return Parametro(simbolo, etiqueta, **kwargs)


def R(etiqueta: str, valor: float, unidad: str = "") -> Resultado:
    return Resultado(etiqueta, valor, unidad)


# --------------------------------------------------------------------------- #
# Utilidades geométricas
# --------------------------------------------------------------------------- #


def _poligono_regular(n: int, radio: float, giro: float = 0.0) -> tuple[tuple[float, float], ...]:
    """Vértices de un polígono regular de ``n`` lados inscrito en ``radio``."""
    return tuple(
        (radio * math.cos(giro + TAU * i / n), radio * math.sin(giro + TAU * i / n))
        for i in range(n)
    )


def _datos_poligono_regular(n: int, lado: float) -> dict:
    apotema = lado / (2 * math.tan(math.pi / n))
    return {
        "apotema": apotema,
        "circunradio": lado / (2 * math.sin(math.pi / n)),
        "area": n * lado * apotema / 2,
        "perimetro": n * lado,
        "angulo_interior": (n - 2) * 180 / n,
        "angulo_central": 360 / n,
        "diagonales": n * (n - 3) // 2,
    }


def _resultados_poligono_regular(n: int, lado: float) -> list[Resultado]:
    d = _datos_poligono_regular(n, lado)
    return [
        R("Área", d["area"], "u²"),
        R("Perímetro", d["perimetro"], "u"),
        R("Apotema", d["apotema"], "u"),
        R("Radio circunscrito", d["circunradio"], "u"),
        R("Ángulo interior", d["angulo_interior"], "°"),
        R("Ángulo central", d["angulo_central"], "°"),
        R("Número de diagonales", d["diagonales"]),
    ]


def _forma_poligono_regular(n: int, lado: float) -> list:
    radio = lado / (2 * math.sin(math.pi / n))
    giro = math.pi / 2 if n % 2 else math.pi / n
    return [Poligono(_poligono_regular(n, radio, giro))]


def _figura_poligono_nombrado(nombre: str, n: int) -> Figura:
    """Crea la entrada del catálogo para un polígono regular concreto."""
    return Figura(
        nombre=nombre,
        grupo="Planas (2D)",
        parametros=(P("l", "Lado", predeterminado=1.0),),
        calculo=lambda p, n=n: _resultados_poligono_regular(n, p["l"]),
        formulas=(
            f"A = {n}·l² / (4·tan(π/{n}))",
            f"P = {n}·l",
            f"apotema = l / (2·tan(π/{n}))",
        ),
        forma=lambda p, n=n: _forma_poligono_regular(n, p["l"]),
    )


def _perimetro_elipse(a: float, b: float) -> float:
    """Aproximación de Ramanujan (error < 1e-5 % para excentricidades usuales)."""
    if a == b:
        return TAU * a
    h = ((a - b) / (a + b)) ** 2
    return math.pi * (a + b) * (1 + 3 * h / (10 + math.sqrt(4 - 3 * h)))


def _angulos_triangulo(a: float, b: float, c: float) -> tuple[float, float, float]:
    """Ángulos en grados opuestos a los lados a, b y c (ley de cosenos)."""
    def angulo(opuesto: float, x: float, y: float) -> float:
        cos = (x * x + y * y - opuesto * opuesto) / (2 * x * y)
        return math.degrees(math.acos(max(-1.0, min(1.0, cos))))

    return angulo(a, b, c), angulo(b, a, c), angulo(c, a, b)


def _vertices_triangulo(a: float, b: float, c: float) -> tuple[tuple[float, float], ...]:
    """Coloca el triángulo de lados a, b, c con el lado ``a`` sobre el eje X."""
    # A = (0,0), B = (a,0); C se obtiene por intersección de circunferencias.
    x = (a * a + c * c - b * b) / (2 * a)
    y = math.sqrt(max(0.0, c * c - x * x))
    return ((0.0, 0.0), (a, 0.0), (x, y))


def _comprobar_triangulo(a: float, b: float, c: float) -> None:
    if a + b <= c or a + c <= b or b + c <= a:
        raise ErrorFigura(
            "Esos tres lados no forman un triángulo: cada lado debe ser menor "
            "que la suma de los otros dos"
        )


def _heron(a: float, b: float, c: float) -> float:
    s = (a + b + c) / 2
    return math.sqrt(max(0.0, s * (s - a) * (s - b) * (s - c)))


# --------------------------------------------------------------------------- #
# Figuras planas
# --------------------------------------------------------------------------- #


def _calc_cuadrado(p):
    l = p["l"]
    return [
        R("Área", l * l, "u²"),
        R("Perímetro", 4 * l, "u"),
        R("Diagonal", l * math.sqrt(2), "u"),
        R("Radio inscrito", l / 2, "u"),
        R("Radio circunscrito", l * math.sqrt(2) / 2, "u"),
    ]


def _calc_rectangulo(p):
    b, h = p["b"], p["h"]
    return [
        R("Área", b * h, "u²"),
        R("Perímetro", 2 * (b + h), "u"),
        R("Diagonal", math.hypot(b, h), "u"),
        R("Relación de aspecto", b / h),
    ]


def _calc_paralelogramo(p):
    b, h, a = p["b"], p["h"], p["a"]
    if h > a:
        raise ErrorFigura("La altura no puede ser mayor que el lado oblicuo")
    return [
        R("Área", b * h, "u²"),
        R("Perímetro", 2 * (b + a), "u"),
        R("Ángulo agudo", math.degrees(math.asin(min(1.0, h / a))), "°"),
        R("Ángulo obtuso", 180 - math.degrees(math.asin(min(1.0, h / a))), "°"),
    ]


def _calc_rombo(p):
    D, d = p["D"], p["d"]
    lado = math.hypot(D / 2, d / 2)
    return [
        R("Área", D * d / 2, "u²"),
        R("Lado", lado, "u"),
        R("Perímetro", 4 * lado, "u"),
        R("Altura", D * d / (2 * lado), "u"),
        R("Ángulo menor", 2 * math.degrees(math.atan(d / D)), "°"),
        R("Ángulo mayor", 180 - 2 * math.degrees(math.atan(d / D)), "°"),
    ]


def _calc_trapecio_isosceles(p):
    B, b, h = p["B"], p["b"], p["h"]
    if B <= b:
        raise ErrorFigura("La base mayor debe ser mayor que la base menor")
    lado = math.hypot((B - b) / 2, h)
    return [
        R("Área", (B + b) * h / 2, "u²"),
        R("Perímetro", B + b + 2 * lado, "u"),
        R("Lado oblicuo", lado, "u"),
        R("Base media", (B + b) / 2, "u"),
        R("Ángulo en la base mayor", math.degrees(math.atan2(h, (B - b) / 2)), "°"),
        R("Diagonal", math.hypot((B + b) / 2, h), "u"),
    ]


def _calc_trapecio_rectangulo(p):
    B, b, h = p["B"], p["b"], p["h"]
    if B <= b:
        raise ErrorFigura("La base mayor debe ser mayor que la base menor")
    oblicuo = math.hypot(B - b, h)
    return [
        R("Área", (B + b) * h / 2, "u²"),
        R("Perímetro", B + b + h + oblicuo, "u"),
        R("Lado oblicuo", oblicuo, "u"),
        R("Base media", (B + b) / 2, "u"),
        R("Ángulo oblicuo", math.degrees(math.atan2(h, B - b)), "°"),
    ]


def _altura_trapecio(B, b, c, d):
    """Altura de un trapecio de bases B y b y lados c y d."""
    diferencia = B - b
    if diferencia == 0:
        raise ErrorFigura("Con las dos bases iguales la figura es un paralelogramo")
    x = (diferencia ** 2 + c * c - d * d) / (2 * diferencia)
    radicando = c * c - x * x
    if radicando <= 0:
        raise ErrorFigura("Esas bases y lados no cierran un trapecio válido")
    return math.sqrt(radicando), x


def _calc_trapecio_general(p):
    B, b, c, d = p["B"], p["b"], p["c"], p["d"]
    if B <= b:
        raise ErrorFigura("La base mayor debe ser mayor que la base menor")
    h, _ = _altura_trapecio(B, b, c, d)
    return [
        R("Área", (B + b) * h / 2, "u²"),
        R("Perímetro", B + b + c + d, "u"),
        R("Altura", h, "u"),
        R("Base media", (B + b) / 2, "u"),
    ]


def _forma_trapecio_general(p):
    B, b, c, d = p["B"], p["b"], p["c"], p["d"]
    h, x = _altura_trapecio(B, b, c, d)
    return [Poligono(((0, 0), (B, 0), (x + b, h), (x, h)))]


def _calc_triangulo_base_altura(p):
    b, h = p["b"], p["h"]
    return [R("Área", b * h / 2, "u²")]


def _calc_triangulo_lados(p):
    a, b, c = p["a"], p["b"], p["c"]
    _comprobar_triangulo(a, b, c)
    area = _heron(a, b, c)
    s = (a + b + c) / 2
    alfa, beta, gamma = _angulos_triangulo(a, b, c)
    return [
        R("Área", area, "u²"),
        R("Perímetro", a + b + c, "u"),
        R("Semiperímetro", s, "u"),
        R("Altura sobre a", 2 * area / a, "u"),
        R("Altura sobre b", 2 * area / b, "u"),
        R("Altura sobre c", 2 * area / c, "u"),
        R("Ángulo A (opuesto a a)", alfa, "°"),
        R("Ángulo B (opuesto a b)", beta, "°"),
        R("Ángulo C (opuesto a c)", gamma, "°"),
        R("Radio inscrito", area / s, "u"),
        R("Radio circunscrito", a * b * c / (4 * area), "u"),
    ]


def _calc_triangulo_rectangulo(p):
    a, b = p["a"], p["b"]
    hip = math.hypot(a, b)
    area = a * b / 2
    return [
        R("Hipotenusa", hip, "u"),
        R("Área", area, "u²"),
        R("Perímetro", a + b + hip, "u"),
        R("Ángulo opuesto al cateto a", math.degrees(math.atan2(a, b)), "°"),
        R("Ángulo opuesto al cateto b", math.degrees(math.atan2(b, a)), "°"),
        R("Altura sobre la hipotenusa", a * b / hip, "u"),
        R("Radio inscrito", (a + b - hip) / 2, "u"),
        R("Radio circunscrito", hip / 2, "u"),
    ]


def _calc_triangulo_equilatero(p):
    l = p["l"]
    return [
        R("Área", math.sqrt(3) / 4 * l * l, "u²"),
        R("Perímetro", 3 * l, "u"),
        R("Altura", math.sqrt(3) / 2 * l, "u"),
        R("Radio inscrito", l / (2 * math.sqrt(3)), "u"),
        R("Radio circunscrito", l / math.sqrt(3), "u"),
        R("Ángulos", 60.0, "°"),
    ]


def _calc_triangulo_isosceles(p):
    b, a = p["b"], p["a"]
    if a <= b / 2:
        raise ErrorFigura("Los lados iguales deben medir más de la mitad de la base")
    h = math.sqrt(a * a - b * b / 4)
    area = b * h / 2
    return [
        R("Área", area, "u²"),
        R("Perímetro", b + 2 * a, "u"),
        R("Altura", h, "u"),
        R("Ángulo del vértice", 2 * math.degrees(math.asin(min(1.0, b / (2 * a)))), "°"),
        R("Ángulos de la base", math.degrees(math.acos(min(1.0, b / (2 * a)))), "°"),
        R("Radio circunscrito", a * a * b / (4 * area), "u"),
    ]


def _calc_triangulo_lal(p):
    a, b, angulo = p["a"], p["b"], p["C"]
    theta = math.radians(angulo)
    c = math.sqrt(a * a + b * b - 2 * a * b * math.cos(theta))
    area = a * b * math.sin(theta) / 2
    alfa, beta, _ = _angulos_triangulo(a, b, c)
    return [
        R("Tercer lado c", c, "u"),
        R("Área", area, "u²"),
        R("Perímetro", a + b + c, "u"),
        R("Ángulo A (opuesto a a)", alfa, "°"),
        R("Ángulo B (opuesto a b)", beta, "°"),
        R("Ángulo C (dato)", angulo, "°"),
        R("Radio circunscrito", c / (2 * math.sin(theta)), "u"),
    ]


def _calc_triangulo_coordenadas(p):
    xs = (p["x1"], p["x2"], p["x3"])
    ys = (p["y1"], p["y2"], p["y3"])
    area = abs(
        xs[0] * (ys[1] - ys[2]) + xs[1] * (ys[2] - ys[0]) + xs[2] * (ys[0] - ys[1])
    ) / 2
    if area == 0:
        raise ErrorFigura("Los tres puntos están alineados: no forman un triángulo")
    a = math.dist((xs[1], ys[1]), (xs[2], ys[2]))
    b = math.dist((xs[0], ys[0]), (xs[2], ys[2]))
    c = math.dist((xs[0], ys[0]), (xs[1], ys[1]))
    alfa, beta, gamma = _angulos_triangulo(a, b, c)
    return [
        R("Área", area, "u²"),
        R("Perímetro", a + b + c, "u"),
        R("Lado a (P2-P3)", a, "u"),
        R("Lado b (P1-P3)", b, "u"),
        R("Lado c (P1-P2)", c, "u"),
        R("Ángulo en P1", alfa, "°"),
        R("Ángulo en P2", beta, "°"),
        R("Ángulo en P3", gamma, "°"),
        R("Centroide x", sum(xs) / 3),
        R("Centroide y", sum(ys) / 3),
    ]


def _calc_circulo(p):
    r = p["r"]
    return [
        R("Área", math.pi * r * r, "u²"),
        R("Circunferencia", TAU * r, "u"),
        R("Diámetro", 2 * r, "u"),
        R("Área del cuadrado inscrito", 2 * r * r, "u²"),
    ]


def _calc_semicirculo(p):
    r = p["r"]
    return [
        R("Área", math.pi * r * r / 2, "u²"),
        R("Perímetro", math.pi * r + 2 * r, "u"),
        R("Longitud del arco", math.pi * r, "u"),
        R("Diámetro (base)", 2 * r, "u"),
        R("Centroide (desde el diámetro)", 4 * r / (3 * math.pi), "u"),
    ]


def _calc_sector_circular(p):
    r, grados = p["r"], p["a"]
    theta = math.radians(grados)
    arco = r * theta
    return [
        R("Área", r * r * theta / 2, "u²"),
        R("Longitud del arco", arco, "u"),
        R("Perímetro", arco + 2 * r, "u"),
        R("Cuerda", 2 * r * math.sin(theta / 2), "u"),
        R("Fracción del círculo", grados / 360),
    ]


def _calc_segmento_circular(p):
    r, grados = p["r"], p["a"]
    theta = math.radians(grados)
    return [
        R("Área", r * r * (theta - math.sin(theta)) / 2, "u²"),
        R("Cuerda", 2 * r * math.sin(theta / 2), "u"),
        R("Longitud del arco", r * theta, "u"),
        R("Perímetro", r * theta + 2 * r * math.sin(theta / 2), "u"),
        R("Altura (sagita)", r * (1 - math.cos(theta / 2)), "u"),
    ]


def _calc_corona_circular(p):
    Rext, rint = p["R"], p["r"]
    if rint >= Rext:
        raise ErrorFigura("El radio interior debe ser menor que el exterior")
    return [
        R("Área", math.pi * (Rext * Rext - rint * rint), "u²"),
        R("Ancho de la corona", Rext - rint, "u"),
        R("Circunferencia exterior", TAU * Rext, "u"),
        R("Circunferencia interior", TAU * rint, "u"),
        R("Perímetro total", TAU * (Rext + rint), "u"),
    ]


def _calc_sector_corona(p):
    Rext, rint, grados = p["R"], p["r"], p["a"]
    if rint >= Rext:
        raise ErrorFigura("El radio interior debe ser menor que el exterior")
    theta = math.radians(grados)
    return [
        R("Área", theta * (Rext * Rext - rint * rint) / 2, "u²"),
        R("Arco exterior", Rext * theta, "u"),
        R("Arco interior", rint * theta, "u"),
        R("Perímetro", (Rext + rint) * theta + 2 * (Rext - rint), "u"),
    ]


def _calc_elipse(p):
    a, b = p["a"], p["b"]
    mayor, menor = max(a, b), min(a, b)
    c = math.sqrt(mayor * mayor - menor * menor)
    return [
        R("Área", math.pi * a * b, "u²"),
        R("Perímetro (Ramanujan)", _perimetro_elipse(a, b), "u"),
        R("Eje mayor", 2 * mayor, "u"),
        R("Eje menor", 2 * menor, "u"),
        R("Distancia focal", 2 * c, "u"),
        R("Excentricidad", c / mayor),
        R("Semilatus rectum", menor * menor / mayor, "u"),
    ]


def _calc_poligono_regular(p):
    n = int(p["n"])
    if n < 3:
        raise ErrorFigura("Un polígono necesita al menos 3 lados")
    return _resultados_poligono_regular(n, p["l"])


def _calc_cometa(p):
    a, b, D = p["a"], p["b"], p["D"]
    # Cometa con dos pares de lados iguales (a, a, b, b) y diagonal principal D.
    # La diagonal y un lado de cada par forman un triángulo: se aplica la
    # desigualdad triangular.
    if D >= a + b:
        raise ErrorFigura("La diagonal principal debe ser menor que la suma de los dos lados")
    if D <= abs(a - b):
        raise ErrorFigura("La diagonal principal debe ser mayor que la diferencia de los dos lados")
    # La diagonal menor es la cuerda común a las dos circunferencias de radios a y b.
    x = (D * D + a * a - b * b) / (2 * D)
    mitad_d = math.sqrt(max(0.0, a * a - x * x))
    d = 2 * mitad_d
    return [
        R("Área", D * d / 2, "u²"),
        R("Perímetro", 2 * (a + b), "u"),
        R("Diagonal menor", d, "u"),
        R("Diagonal mayor (dato)", D, "u"),
    ]


def _forma_cometa(p):
    a, b, D = p["a"], p["b"], p["D"]
    x = (D * D + a * a - b * b) / (2 * D)
    mitad = math.sqrt(max(0.0, a * a - x * x))
    return [Poligono(((0, 0), (mitad, x), (0, D), (-mitad, x)))]


def _calc_estrella(p):
    n = int(p["n"])
    Rext, rint = p["R"], p["r"]
    if n < 3:
        raise ErrorFigura("La estrella necesita al menos 3 puntas")
    if rint >= Rext:
        raise ErrorFigura("El radio interior debe ser menor que el exterior")
    lado = math.sqrt(Rext ** 2 + rint ** 2 - 2 * Rext * rint * math.cos(math.pi / n))
    return [
        R("Área", n * Rext * rint * math.sin(math.pi / n), "u²"),
        R("Perímetro", 2 * n * lado, "u"),
        R("Lado de la punta", lado, "u"),
        R("Ángulo de la punta", 2 * math.degrees(math.asin(
            min(1.0, rint * math.sin(math.pi / n) / lado))), "°"),
    ]


def _forma_estrella(p):
    n = int(p["n"])
    Rext, rint = p["R"], p["r"]
    puntos = []
    for i in range(n):
        angulo = math.pi / 2 + TAU * i / n
        puntos.append((Rext * math.cos(angulo), Rext * math.sin(angulo)))
        medio = angulo + math.pi / n
        puntos.append((rint * math.cos(medio), rint * math.sin(medio)))
    return [Poligono(tuple(puntos))]


def _calc_segmento_parabolico(p):
    b, h = p["b"], p["h"]
    # Longitud del arco de la parábola y = h(1 - (2x/b)²) entre -b/2 y b/2.
    a = 4 * h / (b * b)  # y = h - a x²
    t = 2 * a * (b / 2)
    arco = (math.asinh(t) / (2 * a)) + (b / 2) * math.sqrt(1 + t * t)
    return [
        R("Área", 2 * b * h / 3, "u²"),
        R("Longitud del arco", arco, "u"),
        R("Perímetro", arco + b, "u"),
        R("Centroide (desde la base)", 2 * h / 5, "u"),
    ]


def _forma_segmento_parabolico(p):
    b, h = p["b"], p["h"]
    puntos = []
    pasos = 60
    for i in range(pasos + 1):
        x = -b / 2 + b * i / pasos
        puntos.append((x, h * (1 - (2 * x / b) ** 2)))
    return [Poligono(tuple(puntos))]


def _calc_cuadrilatero_ciclico(p):
    lados = [p["a"], p["b"], p["c"], p["d"]]
    s = sum(lados) / 2
    for lado in lados:
        if lado >= s:
            raise ErrorFigura(
                "Cada lado debe ser menor que la suma de los otros tres"
            )
    area = math.sqrt((s - lados[0]) * (s - lados[1]) * (s - lados[2]) * (s - lados[3]))
    a, b, c, d = lados
    return [
        R("Área (Brahmagupta)", area, "u²"),
        R("Perímetro", sum(lados), "u"),
        R("Semiperímetro", s, "u"),
        R("Diagonal p", math.sqrt((a * c + b * d) * (a * d + b * c) / (a * b + c * d)), "u"),
        R("Diagonal q", math.sqrt((a * c + b * d) * (a * b + c * d) / (a * d + b * c)), "u"),
        R("Radio circunscrito",
          math.sqrt((a * b + c * d) * (a * c + b * d) * (a * d + b * c)) / (4 * area), "u"),
    ]


def _forma_cuadrilatero_ciclico(p):
    """Coloca el cuadrilátero inscrito en su circunferencia circunscrita."""
    a, b, c, d = p["a"], p["b"], p["c"], p["d"]
    s = (a + b + c + d) / 2
    area = math.sqrt((s - a) * (s - b) * (s - c) * (s - d))
    radio = math.sqrt((a * b + c * d) * (a * c + b * d) * (a * d + b * c)) / (4 * area)

    puntos = []
    angulo = 0.0
    for lado in (a, b, c, d):
        puntos.append((radio * math.cos(angulo), radio * math.sin(angulo)))
        angulo += 2 * math.asin(min(1.0, lado / (2 * radio)))
    return [Circulo((0, 0), radio, relleno=False), Poligono(tuple(puntos))]


def _calc_rectangulo_redondeado(p):
    b, h, r = p["b"], p["h"], p["r"]
    if 2 * r > min(b, h):
        raise ErrorFigura("El radio no puede superar la mitad del lado más corto")
    return [
        R("Área", b * h - (4 - math.pi) * r * r, "u²"),
        R("Perímetro", 2 * (b + h) - 8 * r + TAU * r, "u"),
        R("Área de las esquinas recortadas", (4 - math.pi) * r * r, "u²"),
    ]


def _forma_rectangulo_redondeado(p):
    b, h, r = p["b"], p["h"], p["r"]
    puntos = []
    esquinas = (
        (b - r, h - r, 0.0),
        (r, h - r, math.pi / 2),
        (r, r, math.pi),
        (b - r, r, 3 * math.pi / 2),
    )
    for cx, cy, inicio in esquinas:
        for i in range(16):
            angulo = inicio + (math.pi / 2) * i / 15
            puntos.append((cx + r * math.cos(angulo), cy + r * math.sin(angulo)))
    return [Poligono(tuple(puntos))]


# --------------------------------------------------------------------------- #
# Cuerpos en el espacio
# --------------------------------------------------------------------------- #


def _calc_cubo(p):
    a = p["a"]
    return [
        R("Volumen", a ** 3, "u³"),
        R("Área total", 6 * a * a, "u²"),
        R("Diagonal espacial", a * math.sqrt(3), "u"),
        R("Diagonal de una cara", a * math.sqrt(2), "u"),
        R("Suma de aristas", 12 * a, "u"),
        R("Radio de la esfera inscrita", a / 2, "u"),
        R("Radio de la esfera circunscrita", a * math.sqrt(3) / 2, "u"),
    ]


def _calc_ortoedro(p):
    a, b, c = p["a"], p["b"], p["c"]
    return [
        R("Volumen", a * b * c, "u³"),
        R("Área total", 2 * (a * b + b * c + a * c), "u²"),
        R("Diagonal espacial", math.sqrt(a * a + b * b + c * c), "u"),
        R("Suma de aristas", 4 * (a + b + c), "u"),
    ]


def _calc_prisma_regular(p):
    n, l, h = int(p["n"]), p["l"], p["h"]
    if n < 3:
        raise ErrorFigura("La base necesita al menos 3 lados")
    d = _datos_poligono_regular(n, l)
    return [
        R("Volumen", d["area"] * h, "u³"),
        R("Área de la base", d["area"], "u²"),
        R("Área lateral", d["perimetro"] * h, "u²"),
        R("Área total", 2 * d["area"] + d["perimetro"] * h, "u²"),
        R("Perímetro de la base", d["perimetro"], "u"),
    ]


def _calc_prisma_generico(p):
    area, perimetro, h = p["A"], p["P"], p["h"]
    return [
        R("Volumen", area * h, "u³"),
        R("Área lateral", perimetro * h, "u²"),
        R("Área total", 2 * area + perimetro * h, "u²"),
    ]


def _calc_cilindro(p):
    r, h = p["r"], p["h"]
    return [
        R("Volumen", math.pi * r * r * h, "u³"),
        R("Área lateral", TAU * r * h, "u²"),
        R("Área de una base", math.pi * r * r, "u²"),
        R("Área total", TAU * r * (r + h), "u²"),
        R("Diagonal del desarrollo", math.hypot(TAU * r, h), "u"),
    ]


def _calc_cilindro_hueco(p):
    Rext, rint, h = p["R"], p["r"], p["h"]
    if rint >= Rext:
        raise ErrorFigura("El radio interior debe ser menor que el exterior")
    corona = math.pi * (Rext * Rext - rint * rint)
    return [
        R("Volumen", corona * h, "u³"),
        R("Área lateral exterior", TAU * Rext * h, "u²"),
        R("Área lateral interior", TAU * rint * h, "u²"),
        R("Área total", TAU * (Rext + rint) * h + 2 * corona, "u²"),
        R("Espesor de pared", Rext - rint, "u"),
    ]


def _calc_cono(p):
    r, h = p["r"], p["h"]
    g = math.hypot(r, h)
    return [
        R("Volumen", math.pi * r * r * h / 3, "u³"),
        R("Generatriz", g, "u"),
        R("Área lateral", math.pi * r * g, "u²"),
        R("Área de la base", math.pi * r * r, "u²"),
        R("Área total", math.pi * r * (r + g), "u²"),
        R("Semiángulo en el vértice", math.degrees(math.atan2(r, h)), "°"),
    ]


def _calc_tronco_cono(p):
    Rext, rint, h = p["R"], p["r"], p["h"]
    if rint >= Rext:
        raise ErrorFigura("El radio menor debe ser menor que el mayor")
    g = math.hypot(Rext - rint, h)
    lateral = math.pi * (Rext + rint) * g
    return [
        R("Volumen", math.pi * h * (Rext ** 2 + Rext * rint + rint ** 2) / 3, "u³"),
        R("Generatriz", g, "u"),
        R("Área lateral", lateral, "u²"),
        R("Área total", lateral + math.pi * (Rext ** 2 + rint ** 2), "u²"),
    ]


def _calc_esfera(p):
    r = p["r"]
    return [
        R("Volumen", 4 / 3 * math.pi * r ** 3, "u³"),
        R("Área de la superficie", 4 * math.pi * r * r, "u²"),
        R("Diámetro", 2 * r, "u"),
        R("Circunferencia máxima", TAU * r, "u"),
        R("Arista del cubo inscrito", 2 * r / math.sqrt(3), "u"),
    ]


def _calc_semiesfera(p):
    r = p["r"]
    return [
        R("Volumen", 2 / 3 * math.pi * r ** 3, "u³"),
        R("Área curva", 2 * math.pi * r * r, "u²"),
        R("Área de la base", math.pi * r * r, "u²"),
        R("Área total", 3 * math.pi * r * r, "u²"),
        R("Centroide (desde la base)", 3 * r / 8, "u"),
    ]


def _calc_casquete_esferico(p):
    Rad, h = p["R"], p["h"]
    if h > 2 * Rad:
        raise ErrorFigura("La altura del casquete no puede pasar del diámetro")
    a = math.sqrt(max(0.0, h * (2 * Rad - h)))
    curva = TAU * Rad * h
    return [
        R("Volumen", math.pi * h * h * (3 * Rad - h) / 3, "u³"),
        R("Área curva", curva, "u²"),
        R("Radio de la base", a, "u"),
        R("Área de la base", math.pi * a * a, "u²"),
        R("Área total", curva + math.pi * a * a, "u²"),
    ]


def _calc_sector_esferico(p):
    Rad, h = p["R"], p["h"]
    if h > 2 * Rad:
        raise ErrorFigura("La altura no puede pasar del diámetro")
    a = math.sqrt(max(0.0, h * (2 * Rad - h)))
    return [
        R("Volumen", TAU * Rad * Rad * h / 3, "u³"),
        R("Área de la zona esférica", TAU * Rad * h, "u²"),
        R("Área total (con el cono)", TAU * Rad * h + math.pi * Rad * a, "u²"),
        R("Radio de la base del casquete", a, "u"),
    ]


def _calc_zona_esferica(p):
    Rad, h = p["R"], p["h"]
    if h > 2 * Rad:
        raise ErrorFigura("La altura de la zona no puede pasar del diámetro")
    return [
        R("Área de la zona (lateral)", TAU * Rad * h, "u²"),
        R("Fracción del área de la esfera", h / (2 * Rad)),
        R("Área de la esfera completa", 4 * math.pi * Rad * Rad, "u²"),
    ]


def _calc_cuna_esferica(p):
    Rad, grados = p["R"], p["a"]
    theta = math.radians(grados)
    return [
        R("Volumen", 2 / 3 * Rad ** 3 * theta, "u³"),
        R("Área del huso esférico", 2 * Rad * Rad * theta, "u²"),
        R("Área total (con las dos semicaras)", 2 * Rad * Rad * theta + math.pi * Rad * Rad, "u²"),
        R("Fracción de la esfera", grados / 360),
    ]


def _calc_piramide_generica(p):
    area, h = p["A"], p["h"]
    return [R("Volumen", area * h / 3, "u³")]


def _calc_piramide_regular(p):
    n, l, h = int(p["n"]), p["l"], p["h"]
    if n < 3:
        raise ErrorFigura("La base necesita al menos 3 lados")
    d = _datos_poligono_regular(n, l)
    apotema_lateral = math.hypot(h, d["apotema"])
    lateral = n * l * apotema_lateral / 2
    return [
        R("Volumen", d["area"] * h / 3, "u³"),
        R("Área de la base", d["area"], "u²"),
        R("Apotema de la base", d["apotema"], "u"),
        R("Apotema lateral", apotema_lateral, "u"),
        R("Arista lateral", math.hypot(h, d["circunradio"]), "u"),
        R("Área lateral", lateral, "u²"),
        R("Área total", d["area"] + lateral, "u²"),
    ]


def _calc_piramide_cuadrangular(p):
    l, h = p["l"], p["h"]
    apotema_lateral = math.hypot(h, l / 2)
    lateral = 2 * l * apotema_lateral
    return [
        R("Volumen", l * l * h / 3, "u³"),
        R("Apotema lateral", apotema_lateral, "u"),
        R("Arista lateral", math.sqrt(h * h + l * l / 2), "u"),
        R("Área lateral", lateral, "u²"),
        R("Área de la base", l * l, "u²"),
        R("Área total", l * l + lateral, "u²"),
    ]


def _calc_tronco_piramide(p):
    L, l, h = p["L"], p["l"], p["h"]
    if l >= L:
        raise ErrorFigura("La base menor debe ser menor que la base mayor")
    apotema_lateral = math.hypot(h, (L - l) / 2)
    lateral = 2 * (L + l) * apotema_lateral
    return [
        R("Volumen", h * (L * L + L * l + l * l) / 3, "u³"),
        R("Apotema lateral", apotema_lateral, "u"),
        R("Área lateral", lateral, "u²"),
        R("Área total", lateral + L * L + l * l, "u²"),
        R("Arista lateral", math.sqrt(h * h + 2 * ((L - l) / 2) ** 2), "u"),
    ]


def _calc_tetraedro(p):
    a = p["a"]
    return [
        R("Volumen", a ** 3 / (6 * math.sqrt(2)), "u³"),
        R("Área total", math.sqrt(3) * a * a, "u²"),
        R("Altura", a * math.sqrt(2 / 3), "u"),
        R("Radio de la esfera inscrita", a / (2 * math.sqrt(6)), "u"),
        R("Radio de la esfera circunscrita", a * math.sqrt(6) / 4, "u"),
        R("Ángulo diedro", math.degrees(math.acos(1 / 3)), "°"),
    ]


def _calc_octaedro(p):
    a = p["a"]
    return [
        R("Volumen", math.sqrt(2) / 3 * a ** 3, "u³"),
        R("Área total", 2 * math.sqrt(3) * a * a, "u²"),
        R("Diagonal", a * math.sqrt(2), "u"),
        R("Radio de la esfera inscrita", a / math.sqrt(6), "u"),
        R("Radio de la esfera circunscrita", a / math.sqrt(2), "u"),
    ]


def _calc_dodecaedro(p):
    a = p["a"]
    return [
        R("Volumen", (15 + 7 * math.sqrt(5)) / 4 * a ** 3, "u³"),
        R("Área total", 3 * math.sqrt(25 + 10 * math.sqrt(5)) * a * a, "u²"),
        R("Radio de la esfera inscrita", a / 2 * math.sqrt(5 / 2 + 11 / (2 * math.sqrt(5))), "u"),
        R("Radio de la esfera circunscrita", a * math.sqrt(3) * (1 + math.sqrt(5)) / 4, "u"),
    ]


def _calc_icosaedro(p):
    a = p["a"]
    return [
        R("Volumen", 5 * (3 + math.sqrt(5)) / 12 * a ** 3, "u³"),
        R("Área total", 5 * math.sqrt(3) * a * a, "u²"),
        R("Radio de la esfera inscrita", a * math.sqrt(3) * (3 + math.sqrt(5)) / 12, "u"),
        R("Radio de la esfera circunscrita", a / 4 * math.sqrt(10 + 2 * math.sqrt(5)), "u"),
    ]


def _calc_elipsoide(p):
    a, b, c = p["a"], p["b"], p["c"]
    exp = 1.6075  # aproximación de Knud Thomsen, error < 1,1 %
    area = 4 * math.pi * (
        ((a * b) ** exp + (a * c) ** exp + (b * c) ** exp) / 3
    ) ** (1 / exp)
    return [
        R("Volumen", 4 / 3 * math.pi * a * b * c, "u³"),
        R("Área aproximada", area, "u²"),
        R("Eje mayor", 2 * max(a, b, c), "u"),
        R("Eje menor", 2 * min(a, b, c), "u"),
    ]


def _calc_toro(p):
    Rmayor, rmenor = p["R"], p["r"]
    if rmenor >= Rmayor:
        raise ErrorFigura("El radio del tubo debe ser menor que el radio mayor")
    return [
        R("Volumen", 2 * math.pi ** 2 * Rmayor * rmenor ** 2, "u³"),
        R("Área de la superficie", 4 * math.pi ** 2 * Rmayor * rmenor, "u²"),
        R("Diámetro exterior", 2 * (Rmayor + rmenor), "u"),
        R("Diámetro interior", 2 * (Rmayor - rmenor), "u"),
    ]


def _calc_paraboloide(p):
    r, h = p["r"], p["h"]
    lateral = (math.pi * r / (6 * h * h)) * ((r * r + 4 * h * h) ** 1.5 - r ** 3)
    return [
        R("Volumen", math.pi * r * r * h / 2, "u³"),
        R("Área lateral", lateral, "u²"),
        R("Área de la base", math.pi * r * r, "u²"),
        R("Área total", lateral + math.pi * r * r, "u²"),
    ]


# --------------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------------- #

_PLANAS = "Planas (2D)"
_CUERPOS = "Cuerpos (3D)"

_CATALOGO: list[Figura] = [
    # --------------------------- Cuadriláteros ---------------------------- #
    Figura("Cuadrado", _PLANAS,
           (P("l", "Lado", predeterminado=4.0),),
           _calc_cuadrado,
           ("A = l²", "P = 4·l", "d = l·√2"),
           lambda p: [Poligono(((0, 0), (p["l"], 0), (p["l"], p["l"]), (0, p["l"]))),
                      Linea(((0, 0), (p["l"], p["l"])))]),

    Figura("Rectángulo", _PLANAS,
           (P("b", "Base", predeterminado=6.0), P("h", "Altura", predeterminado=3.0)),
           _calc_rectangulo,
           ("A = b·h", "P = 2·(b + h)", "d = √(b² + h²)"),
           lambda p: [Poligono(((0, 0), (p["b"], 0), (p["b"], p["h"]), (0, p["h"]))),
                      Linea(((0, 0), (p["b"], p["h"])))]),

    Figura("Paralelogramo", _PLANAS,
           (P("b", "Base", predeterminado=6.0),
            P("h", "Altura", predeterminado=3.0),
            P("a", "Lado oblicuo", predeterminado=4.0)),
           _calc_paralelogramo,
           ("A = b·h", "P = 2·(b + a)", "sen α = h / a"),
           lambda p: [Poligono((
               (0, 0), (p["b"], 0),
               (p["b"] + math.sqrt(max(0.0, p["a"] ** 2 - p["h"] ** 2)), p["h"]),
               (math.sqrt(max(0.0, p["a"] ** 2 - p["h"] ** 2)), p["h"])))]),

    Figura("Rombo", _PLANAS,
           (P("D", "Diagonal mayor", predeterminado=8.0),
            P("d", "Diagonal menor", predeterminado=5.0)),
           _calc_rombo,
           ("A = D·d / 2", "lado = √((D/2)² + (d/2)²)", "P = 4·lado"),
           lambda p: [Poligono(((0, -p["D"] / 2), (p["d"] / 2, 0), (0, p["D"] / 2), (-p["d"] / 2, 0))),
                      Linea(((0, -p["D"] / 2), (0, p["D"] / 2))),
                      Linea(((-p["d"] / 2, 0), (p["d"] / 2, 0)))]),

    Figura("Trapecio isósceles", _PLANAS,
           (P("B", "Base mayor", predeterminado=8.0),
            P("b", "Base menor", predeterminado=4.0),
            P("h", "Altura", predeterminado=3.0)),
           _calc_trapecio_isosceles,
           ("A = (B + b)·h / 2", "lado = √(((B−b)/2)² + h²)", "P = B + b + 2·lado"),
           lambda p: [Poligono((
               (0, 0), (p["B"], 0),
               ((p["B"] + p["b"]) / 2, p["h"]), ((p["B"] - p["b"]) / 2, p["h"])))]),

    Figura("Trapecio rectángulo", _PLANAS,
           (P("B", "Base mayor", predeterminado=8.0),
            P("b", "Base menor", predeterminado=5.0),
            P("h", "Altura", predeterminado=3.0)),
           _calc_trapecio_rectangulo,
           ("A = (B + b)·h / 2", "oblicuo = √((B−b)² + h²)"),
           lambda p: [Poligono(((0, 0), (p["B"], 0), (p["b"], p["h"]), (0, p["h"])))]),

    Figura("Trapecio (4 lados)", _PLANAS,
           (P("B", "Base mayor", predeterminado=8.0),
            P("b", "Base menor", predeterminado=4.0),
            P("c", "Lado izquierdo", predeterminado=3.0),
            P("d", "Lado derecho", predeterminado=3.5)),
           _calc_trapecio_general,
           ("x = ((B−b)² + c² − d²) / (2·(B−b))", "h = √(c² − x²)", "A = (B + b)·h / 2"),
           _forma_trapecio_general,
           nota="Se calcula la altura a partir de las dos bases y los dos lados."),

    Figura("Cometa (deltoide)", _PLANAS,
           (P("a", "Lado corto", predeterminado=3.0),
            P("b", "Lado largo", predeterminado=5.0),
            P("D", "Diagonal principal", predeterminado=6.0)),
           _calc_cometa,
           ("A = D·d / 2", "P = 2·(a + b)"),
           _forma_cometa),

    Figura("Cuadrilátero cíclico", _PLANAS,
           (P("a", "Lado a", predeterminado=4.0), P("b", "Lado b", predeterminado=5.0),
            P("c", "Lado c", predeterminado=6.0), P("d", "Lado d", predeterminado=3.0)),
           _calc_cuadrilatero_ciclico,
           ("s = (a + b + c + d) / 2",
            "A = √((s−a)(s−b)(s−c)(s−d))"),
           _forma_cuadrilatero_ciclico,
           nota="Fórmula de Brahmagupta: válida para cuadriláteros inscritos en una circunferencia."),

    Figura("Rectángulo redondeado", _PLANAS,
           (P("b", "Base", predeterminado=8.0), P("h", "Altura", predeterminado=5.0),
            P("r", "Radio de las esquinas", predeterminado=1.0)),
           _calc_rectangulo_redondeado,
           ("A = b·h − (4 − π)·r²", "P = 2·(b + h) − 8·r + 2·π·r"),
           _forma_rectangulo_redondeado),

    # ----------------------------- Triángulos ----------------------------- #
    Figura("Triángulo (base y altura)", _PLANAS,
           (P("b", "Base", predeterminado=6.0), P("h", "Altura", predeterminado=4.0)),
           _calc_triangulo_base_altura,
           ("A = b·h / 2",),
           lambda p: [Poligono(((0, 0), (p["b"], 0), (p["b"] / 2, p["h"])))],
           nota="Con la base y la altura sólo se puede determinar el área."),

    Figura("Triángulo (3 lados)", _PLANAS,
           (P("a", "Lado a", predeterminado=3.0), P("b", "Lado b", predeterminado=4.0),
            P("c", "Lado c", predeterminado=5.0)),
           _calc_triangulo_lados,
           ("s = (a + b + c) / 2", "A = √(s(s−a)(s−b)(s−c))",
            "cos A = (b² + c² − a²) / (2·b·c)", "r = A / s", "R = a·b·c / (4·A)"),
           lambda p: [Poligono(_vertices_triangulo(p["a"], p["b"], p["c"]))]),

    Figura("Triángulo rectángulo", _PLANAS,
           (P("a", "Cateto a", predeterminado=3.0), P("b", "Cateto b", predeterminado=4.0)),
           _calc_triangulo_rectangulo,
           ("h² = a² + b²", "A = a·b / 2", "altura sobre h = a·b / h"),
           lambda p: [Poligono(((0, 0), (p["b"], 0), (0, p["a"])))]),

    Figura("Triángulo equilátero", _PLANAS,
           (P("l", "Lado", predeterminado=5.0),),
           _calc_triangulo_equilatero,
           ("A = (√3 / 4)·l²", "h = (√3 / 2)·l", "P = 3·l"),
           lambda p: [Poligono(((0, 0), (p["l"], 0), (p["l"] / 2, math.sqrt(3) / 2 * p["l"])))]),

    Figura("Triángulo isósceles", _PLANAS,
           (P("b", "Base", predeterminado=6.0), P("a", "Lados iguales", predeterminado=5.0)),
           _calc_triangulo_isosceles,
           ("h = √(a² − b²/4)", "A = b·h / 2", "P = b + 2·a"),
           lambda p: [Poligono(((0, 0), (p["b"], 0),
                                (p["b"] / 2, math.sqrt(max(0.0, p["a"] ** 2 - p["b"] ** 2 / 4)))))]),

    Figura("Triángulo (2 lados y el ángulo)", _PLANAS,
           (P("a", "Lado a", predeterminado=5.0), P("b", "Lado b", predeterminado=7.0),
            P("C", "Ángulo entre ellos", unidad="°", maximo=179.999, predeterminado=60.0)),
           _calc_triangulo_lal,
           ("A = a·b·sen C / 2", "c² = a² + b² − 2·a·b·cos C"),
           lambda p: [Poligono((
               (0, 0), (p["b"], 0),
               (p["a"] * math.cos(math.radians(p["C"])), p["a"] * math.sin(math.radians(p["C"])))))]),

    Figura("Triángulo por coordenadas", _PLANAS,
           (P("x1", "x₁", minimo=-math.inf, predeterminado=0.0),
            P("y1", "y₁", minimo=-math.inf, predeterminado=0.0),
            P("x2", "x₂", minimo=-math.inf, predeterminado=6.0),
            P("y2", "y₂", minimo=-math.inf, predeterminado=0.0),
            P("x3", "x₃", minimo=-math.inf, predeterminado=2.0),
            P("y3", "y₃", minimo=-math.inf, predeterminado=5.0)),
           _calc_triangulo_coordenadas,
           ("A = |x₁(y₂−y₃) + x₂(y₃−y₁) + x₃(y₁−y₂)| / 2",),
           lambda p: [Poligono(((p["x1"], p["y1"]), (p["x2"], p["y2"]), (p["x3"], p["y3"])))],
           nota="Fórmula del área de Gauss (del cordón de zapato). Admite coordenadas negativas."),

    # ----------------------------- Circulares ----------------------------- #
    Figura("Círculo", _PLANAS,
           (P("r", "Radio", predeterminado=5.0),),
           _calc_circulo,
           ("A = π·r²", "C = 2·π·r"),
           lambda p: [Circulo((0, 0), p["r"]), Linea(((0, 0), (p["r"], 0)))]),

    Figura("Semicírculo", _PLANAS,
           (P("r", "Radio", predeterminado=5.0),),
           _calc_semicirculo,
           ("A = π·r² / 2", "P = π·r + 2·r"),
           lambda p: [Sector((0, 0), p["r"], 0, 180)]),

    Figura("Sector circular", _PLANAS,
           (P("r", "Radio", predeterminado=5.0),
            P("a", "Ángulo", unidad="°", maximo=360.0, predeterminado=60.0)),
           _calc_sector_circular,
           ("A = r²·θ / 2", "arco = r·θ", "θ en radianes"),
           lambda p: [Sector((0, 0), p["r"], 0, p["a"])]),

    Figura("Segmento circular", _PLANAS,
           (P("r", "Radio", predeterminado=5.0),
            P("a", "Ángulo central", unidad="°", maximo=360.0, predeterminado=90.0)),
           _calc_segmento_circular,
           ("A = r²·(θ − sen θ) / 2", "cuerda = 2·r·sen(θ/2)",
            "sagita = r·(1 − cos(θ/2))"),
           lambda p: [Circulo((0, 0), p["r"], relleno=False),
                      Sector((0, 0), p["r"], 0, p["a"]),
                      Linea(((p["r"], 0),
                             (p["r"] * math.cos(math.radians(p["a"])),
                              p["r"] * math.sin(math.radians(p["a"])))))]),

    Figura("Corona circular (anillo)", _PLANAS,
           (P("R", "Radio exterior", predeterminado=6.0),
            P("r", "Radio interior", predeterminado=4.0)),
           _calc_corona_circular,
           ("A = π·(R² − r²)", "ancho = R − r"),
           lambda p: [Circulo((0, 0), p["R"]), Circulo((0, 0), p["r"], relleno=False)]),

    Figura("Sector de corona circular", _PLANAS,
           (P("R", "Radio exterior", predeterminado=6.0),
            P("r", "Radio interior", predeterminado=4.0),
            P("a", "Ángulo", unidad="°", maximo=360.0, predeterminado=90.0)),
           _calc_sector_corona,
           ("A = θ·(R² − r²) / 2",),
           lambda p: [Sector((0, 0), p["R"], 0, p["a"]),
                      Sector((0, 0), p["r"], 0, p["a"], relleno=False)]),

    Figura("Elipse", _PLANAS,
           (P("a", "Semieje a", predeterminado=6.0), P("b", "Semieje b", predeterminado=4.0)),
           _calc_elipse,
           ("A = π·a·b",
            "P ≈ π·(a+b)·(1 + 3h/(10 + √(4−3h))),  h = ((a−b)/(a+b))²",
            "e = √(a² − b²) / a"),
           lambda p: [Elipse((0, 0), p["a"], p["b"])]),

    Figura("Segmento parabólico", _PLANAS,
           (P("b", "Base (cuerda)", predeterminado=8.0), P("h", "Altura (flecha)", predeterminado=4.0)),
           _calc_segmento_parabolico,
           ("A = 2·b·h / 3",),
           _forma_segmento_parabolico),

    # ------------------------- Polígonos regulares ------------------------- #
    Figura("Polígono regular (n lados)", _PLANAS,
           (P("n", "Número de lados", unidad="", minimo=2.0, maximo=1000.0, entero=True,
              predeterminado=6.0),
            P("l", "Lado", predeterminado=3.0)),
           _calc_poligono_regular,
           ("A = n·l² / (4·tan(π/n))", "P = n·l",
            "apotema = l / (2·tan(π/n))", "R = l / (2·sen(π/n))"),
           lambda p: _forma_poligono_regular(int(p["n"]), p["l"])),

    _figura_poligono_nombrado("Pentágono regular", 5),
    _figura_poligono_nombrado("Hexágono regular", 6),
    _figura_poligono_nombrado("Heptágono regular", 7),
    _figura_poligono_nombrado("Octágono regular", 8),
    _figura_poligono_nombrado("Eneágono regular", 9),
    _figura_poligono_nombrado("Decágono regular", 10),
    _figura_poligono_nombrado("Endecágono regular", 11),
    _figura_poligono_nombrado("Dodecágono regular", 12),
    _figura_poligono_nombrado("Icoságono regular", 20),

    Figura("Estrella regular", _PLANAS,
           (P("n", "Número de puntas", unidad="", minimo=2.0, maximo=200.0, entero=True,
              predeterminado=5.0),
            P("R", "Radio exterior", predeterminado=6.0),
            P("r", "Radio interior", predeterminado=2.5)),
           _calc_estrella,
           ("A = n·R·r·sen(π/n)",),
           _forma_estrella),

    # ------------------------------- Cuerpos ------------------------------- #
    Figura("Cubo", _CUERPOS,
           (P("a", "Arista", predeterminado=4.0),),
           _calc_cubo,
           ("V = a³", "A = 6·a²", "diagonal = a·√3"),
           lambda p: [Solido("cubo", {"a": p["a"]})]),

    Figura("Ortoedro (prisma rectangular)", _CUERPOS,
           (P("a", "Largo", predeterminado=6.0), P("b", "Ancho", predeterminado=4.0),
            P("c", "Alto", predeterminado=3.0)),
           _calc_ortoedro,
           ("V = a·b·c", "A = 2·(a·b + b·c + a·c)", "d = √(a² + b² + c²)"),
           lambda p: [Solido("ortoedro", {"a": p["a"], "b": p["b"], "c": p["c"]})]),

    Figura("Prisma regular (n lados)", _CUERPOS,
           (P("n", "Lados de la base", unidad="", minimo=2.0, maximo=200.0, entero=True,
              predeterminado=6.0),
            P("l", "Lado de la base", predeterminado=3.0),
            P("h", "Altura", predeterminado=8.0)),
           _calc_prisma_regular,
           ("V = A_base · h", "A_lateral = P_base · h",
            "A_total = 2·A_base + A_lateral"),
           lambda p: [Solido("prisma", {"n": int(p["n"]), "l": p["l"], "h": p["h"]})]),

    Figura("Prisma recto (base cualquiera)", _CUERPOS,
           (P("A", "Área de la base", unidad="u²", predeterminado=12.0),
            P("P", "Perímetro de la base", predeterminado=14.0),
            P("h", "Altura", predeterminado=8.0)),
           _calc_prisma_generico,
           ("V = A_base · h", "A_lateral = P_base · h"),
           nota="Para bases irregulares: introduzca el área y el perímetro ya calculados."),

    Figura("Cilindro", _CUERPOS,
           (P("r", "Radio", predeterminado=3.0), P("h", "Altura", predeterminado=8.0)),
           _calc_cilindro,
           ("V = π·r²·h", "A_lateral = 2·π·r·h", "A_total = 2·π·r·(r + h)"),
           lambda p: [Solido("cilindro", {"r": p["r"], "h": p["h"]})]),

    Figura("Cilindro hueco (tubo)", _CUERPOS,
           (P("R", "Radio exterior", predeterminado=4.0),
            P("r", "Radio interior", predeterminado=3.0),
            P("h", "Altura", predeterminado=10.0)),
           _calc_cilindro_hueco,
           ("V = π·(R² − r²)·h",),
           lambda p: [Solido("cilindro_hueco", {"R": p["R"], "r": p["r"], "h": p["h"]})]),

    Figura("Cono", _CUERPOS,
           (P("r", "Radio de la base", predeterminado=3.0), P("h", "Altura", predeterminado=6.0)),
           _calc_cono,
           ("g = √(r² + h²)", "V = π·r²·h / 3", "A_total = π·r·(r + g)"),
           lambda p: [Solido("cono", {"r": p["r"], "h": p["h"]})]),

    Figura("Tronco de cono", _CUERPOS,
           (P("R", "Radio mayor", predeterminado=5.0), P("r", "Radio menor", predeterminado=3.0),
            P("h", "Altura", predeterminado=6.0)),
           _calc_tronco_cono,
           ("g = √((R − r)² + h²)", "V = π·h·(R² + R·r + r²) / 3",
            "A_lateral = π·(R + r)·g"),
           lambda p: [Solido("tronco_cono", {"R": p["R"], "r": p["r"], "h": p["h"]})]),

    Figura("Esfera", _CUERPOS,
           (P("r", "Radio", predeterminado=5.0),),
           _calc_esfera,
           ("V = 4·π·r³ / 3", "A = 4·π·r²"),
           lambda p: [Solido("esfera", {"r": p["r"]})]),

    Figura("Semiesfera", _CUERPOS,
           (P("r", "Radio", predeterminado=5.0),),
           _calc_semiesfera,
           ("V = 2·π·r³ / 3", "A_total = 3·π·r²"),
           lambda p: [Solido("semiesfera", {"r": p["r"]})]),

    Figura("Casquete esférico", _CUERPOS,
           (P("R", "Radio de la esfera", predeterminado=5.0),
            P("h", "Altura del casquete", predeterminado=2.0)),
           _calc_casquete_esferico,
           ("V = π·h²·(3·R − h) / 3", "A_curva = 2·π·R·h",
            "a = √(h·(2·R − h))"),
           lambda p: [Solido("casquete", {"R": p["R"], "h": p["h"]})]),

    Figura("Sector esférico", _CUERPOS,
           (P("R", "Radio de la esfera", predeterminado=5.0),
            P("h", "Altura de la zona", predeterminado=2.0)),
           _calc_sector_esferico,
           ("V = 2·π·R²·h / 3", "A_zona = 2·π·R·h"),
           lambda p: [Solido("sector_esferico", {"R": p["R"], "h": p["h"]})]),

    Figura("Zona esférica", _CUERPOS,
           (P("R", "Radio de la esfera", predeterminado=5.0),
            P("h", "Altura de la zona", predeterminado=3.0)),
           _calc_zona_esferica,
           ("A = 2·π·R·h",),
           lambda p: [Solido("zona_esferica", {"R": p["R"], "h": p["h"]})],
           nota="El área de una zona esférica sólo depende de su altura (teorema de Arquímedes)."),

    Figura("Cuña esférica", _CUERPOS,
           (P("R", "Radio de la esfera", predeterminado=5.0),
            P("a", "Ángulo diedro", unidad="°", maximo=360.0, predeterminado=90.0)),
           _calc_cuna_esferica,
           ("V = 2·R³·θ / 3", "A_huso = 2·R²·θ"),
           lambda p: [Solido("cuna_esferica", {"R": p["R"], "a": p["a"]})]),

    Figura("Pirámide (base cualquiera)", _CUERPOS,
           (P("A", "Área de la base", unidad="u²", predeterminado=16.0),
            P("h", "Altura", predeterminado=9.0)),
           _calc_piramide_generica,
           ("V = A_base · h / 3",),
           nota="Para bases irregulares: introduzca el área ya calculada."),

    Figura("Pirámide cuadrangular", _CUERPOS,
           (P("l", "Lado de la base", predeterminado=6.0), P("h", "Altura", predeterminado=8.0)),
           _calc_piramide_cuadrangular,
           ("V = l²·h / 3", "apotema lateral = √(h² + (l/2)²)",
            "A_lateral = 2·l·apotema"),
           lambda p: [Solido("piramide", {"n": 4, "l": p["l"], "h": p["h"]})]),

    Figura("Pirámide regular (n lados)", _CUERPOS,
           (P("n", "Lados de la base", unidad="", minimo=2.0, maximo=200.0, entero=True,
              predeterminado=6.0),
            P("l", "Lado de la base", predeterminado=3.0),
            P("h", "Altura", predeterminado=8.0)),
           _calc_piramide_regular,
           ("V = A_base · h / 3", "apotema lateral = √(h² + apotema_base²)"),
           lambda p: [Solido("piramide", {"n": int(p["n"]), "l": p["l"], "h": p["h"]})]),

    Figura("Tronco de pirámide cuadrangular", _CUERPOS,
           (P("L", "Lado de la base mayor", predeterminado=8.0),
            P("l", "Lado de la base menor", predeterminado=4.0),
            P("h", "Altura", predeterminado=6.0)),
           _calc_tronco_piramide,
           ("V = h·(L² + L·l + l²) / 3",
            "apotema lateral = √(h² + ((L − l)/2)²)"),
           lambda p: [Solido("tronco_piramide", {"L": p["L"], "l": p["l"], "h": p["h"]})]),

    Figura("Tetraedro regular", _CUERPOS,
           (P("a", "Arista", predeterminado=5.0),),
           _calc_tetraedro,
           ("V = a³ / (6·√2)", "A = √3·a²", "h = a·√(2/3)"),
           lambda p: [Solido("tetraedro", {"a": p["a"]})]),

    Figura("Octaedro regular", _CUERPOS,
           (P("a", "Arista", predeterminado=5.0),),
           _calc_octaedro,
           ("V = (√2 / 3)·a³", "A = 2·√3·a²"),
           lambda p: [Solido("octaedro", {"a": p["a"]})]),

    Figura("Dodecaedro regular", _CUERPOS,
           (P("a", "Arista", predeterminado=3.0),),
           _calc_dodecaedro,
           ("V = (15 + 7·√5)·a³ / 4", "A = 3·√(25 + 10·√5)·a²"),
           lambda p: [Solido("dodecaedro", {"a": p["a"]})]),

    Figura("Icosaedro regular", _CUERPOS,
           (P("a", "Arista", predeterminado=3.0),),
           _calc_icosaedro,
           ("V = 5·(3 + √5)·a³ / 12", "A = 5·√3·a²"),
           lambda p: [Solido("icosaedro", {"a": p["a"]})]),

    Figura("Elipsoide", _CUERPOS,
           (P("a", "Semieje a", predeterminado=5.0), P("b", "Semieje b", predeterminado=3.0),
            P("c", "Semieje c", predeterminado=2.0)),
           _calc_elipsoide,
           ("V = 4·π·a·b·c / 3",
            "A ≈ 4·π·(((ab)^p + (ac)^p + (bc)^p)/3)^(1/p),  p = 1,6075"),
           lambda p: [Solido("elipsoide", {"a": p["a"], "b": p["b"], "c": p["c"]})],
           nota="El área de un elipsoide no tiene forma cerrada elemental; se usa la aproximación de Knud Thomsen (error < 1,1 %)."),

    Figura("Toro (donut)", _CUERPOS,
           (P("R", "Radio mayor", predeterminado=6.0,
              ayuda="Distancia del centro del toro al centro del tubo"),
            P("r", "Radio del tubo", predeterminado=2.0,
              ayuda="Radio de la sección circular del tubo")),
           _calc_toro,
           ("V = 2·π²·R·r²", "A = 4·π²·R·r"),
           lambda p: [Solido("toro", {"R": p["R"], "r": p["r"]})]),

    Figura("Paraboloide de revolución", _CUERPOS,
           (P("r", "Radio de la base", predeterminado=3.0), P("h", "Altura", predeterminado=6.0)),
           _calc_paraboloide,
           ("V = π·r²·h / 2",
            "A_lateral = (π·r / (6·h²))·((r² + 4·h²)^(3/2) − r³)"),
           lambda p: [Solido("paraboloide", {"r": p["r"], "h": p["h"]})]),
]

#: Figuras indexadas por nombre, en el orden en que se muestran.
FIGURAS: dict[str, Figura] = {f.nombre: f for f in _CATALOGO}

#: Grupo -> nombres de figura, para la navegación de la interfaz.
GRUPOS: dict[str, list[str]] = {}
for _f in _CATALOGO:
    GRUPOS.setdefault(_f.grupo, []).append(_f.nombre)


def figura(nombre: str) -> Figura:
    try:
        return FIGURAS[nombre]
    except KeyError:
        raise ErrorFigura(f"Figura desconocida: {nombre!r}") from None


def calcular(nombre: str, valores: dict) -> list[Resultado]:
    return figura(nombre).calcular(valores)


# --------------------------------------------------------------------------- #
# Cálculo inverso
# --------------------------------------------------------------------------- #

#: Tolerancia relativa con la que se da por bueno el valor hallado.
_TOLERANCIA = 1e-10
#: Iteraciones máximas de la bisección. Con 200 se agota la precisión de un
#: float mucho antes, así que sirve sólo de tope de seguridad.
_MAX_ITERACIONES = 200


def resolver_inverso(nombre: str, objetivo_etiqueta: str, objetivo_valor: float,
                     incognita: str, conocidos: dict) -> float:
    """Halla el parámetro ``incognita`` que produce el resultado pedido.

    Responde a la pregunta que la gente hace de verdad: «sé que el área vale 50,
    ¿cuánto mide el lado?».

    Se resuelve numéricamente por bisección en lugar de despejar cada fórmula a
    mano: hay 61 figuras con varios resultados cada una, y casi todas las
    magnitudes (área, perímetro, volumen…) crecen de forma monótona con sus
    dimensiones, que es la única condición que la bisección necesita.

    Args:
        nombre: figura del catálogo.
        objetivo_etiqueta: qué resultado se conoce, p. ej. ``"Área"``.
        objetivo_valor: cuánto vale ese resultado.
        incognita: símbolo del parámetro que se busca.
        conocidos: valores del resto de parámetros.

    Raises:
        ErrorFigura: si los datos no permiten hallar una solución.
    """
    fig = figura(nombre)

    parametro = next((p for p in fig.parametros if p.simbolo == incognita), None)
    if parametro is None:
        raise ErrorFigura(f"«{incognita}» no es un dato de {nombre}")
    if parametro.entero:
        raise ErrorFigura(
            f"«{parametro.etiqueta}» sólo admite números enteros: no se puede "
            f"hallar por aproximación."
        )
    if objetivo_valor <= 0:
        raise ErrorFigura("El valor buscado debe ser mayor que 0")

    def evaluar(x: float) -> float | None:
        """Valor del resultado objetivo cuando la incógnita vale ``x``."""
        intento = dict(conocidos)
        intento[incognita] = x
        try:
            resultados = fig.calcular(intento)
        except (ErrorFigura, ValueError, ArithmeticError):
            return None
        for resultado in resultados:
            if resultado.etiqueta == objetivo_etiqueta:
                valor = float(resultado.valor)
                return valor if math.isfinite(valor) else None
        return None

    inferior, superior = _acotar(evaluar, objetivo_valor, parametro)

    # Bisección: en cada paso se descarta la mitad del intervalo.
    for _ in range(_MAX_ITERACIONES):
        medio = (inferior + superior) / 2
        valor = evaluar(medio)
        if valor is None:
            raise ErrorFigura(
                "No se pudo resolver: con esos datos la figura deja de ser válida "
                "a mitad de la búsqueda."
            )
        if abs(valor - objetivo_valor) <= _TOLERANCIA * max(1.0, abs(objetivo_valor)):
            return medio
        if superior - inferior <= _TOLERANCIA * max(1.0, medio):
            return medio
        if valor < objetivo_valor:
            inferior = medio
        else:
            superior = medio

    return (inferior + superior) / 2


def _acotar(evaluar, objetivo: float, parametro: Parametro) -> tuple[float, float]:
    """Busca un intervalo donde el resultado pase por el valor objetivo."""
    minimo = max(parametro.minimo, 0.0)
    inferior = minimo + 1e-9

    valor_inferior = evaluar(inferior)
    if valor_inferior is None:
        raise ErrorFigura(
            "No se pudo resolver: faltan datos o los que hay no describen una "
            "figura válida."
        )
    if valor_inferior > objetivo:
        raise ErrorFigura(
            f"No hay solución: incluso con «{parametro.etiqueta}» casi nulo, el "
            f"resultado ya supera el valor buscado."
        )

    # Se duplica el extremo superior hasta rebasar el objetivo.
    superior = max(1.0, inferior * 2)
    for _ in range(200):
        if superior > parametro.maximo:
            superior = parametro.maximo
        valor = evaluar(superior)
        if valor is not None and valor >= objetivo:
            return inferior, superior
        if valor is not None:
            inferior = superior
        if superior >= parametro.maximo:
            break
        superior *= 2

    raise ErrorFigura(
        f"No se encontró ningún valor de «{parametro.etiqueta}» que dé ese "
        f"resultado. Compruebe que el dato conocido es correcto."
    )


def resultados_invertibles(nombre: str) -> list[str]:
    """Etiquetas de resultado que sirven como dato conocido en el modo inverso.

    Se excluyen los adimensionales (ángulos fijos, recuentos, fracciones), que no
    dependen del tamaño de la figura y por tanto no permiten deducirlo.
    """
    fig = figura(nombre)
    valores = {p.simbolo: p.predeterminado for p in fig.parametros}
    try:
        base = fig.calcular(valores)
    except (ErrorFigura, ValueError, ArithmeticError):
        return []

    # Se recalcula con la figura ampliada: lo que no cambia, no sirve de pista.
    escalados = {}
    for p in fig.parametros:
        escalados[p.simbolo] = valores[p.simbolo] * (1.0 if p.entero else 1.3)
    try:
        ampliada = fig.calcular(escalados)
    except (ErrorFigura, ValueError, ArithmeticError):
        return []

    etiquetas = []
    for antes, despues in zip(base, ampliada):
        if antes.etiqueta != despues.etiqueta or antes.unidad not in ("u", "u²", "u³"):
            continue
        if abs(float(despues.valor) - float(antes.valor)) > 1e-9:
            etiquetas.append(antes.etiqueta)
    return etiquetas


def resumen() -> str:
    planas = len(GRUPOS.get(_PLANAS, []))
    cuerpos = len(GRUPOS.get(_CUERPOS, []))
    return f"{planas} figuras planas y {cuerpos} cuerpos en el espacio"
