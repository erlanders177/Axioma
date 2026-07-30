"""Dibujo de figuras geométricas sobre un lienzo de matplotlib embebido en Qt.

La versión anterior (``visualizador_figuras.py``) guardaba un PNG llamado
``figura_temp.png`` en el directorio de trabajo y nunca llegaba a usarse desde la
interfaz. Aquí el lienzo se integra directamente en el panel, no se toca el disco
y se dibujan tanto figuras planas como cuerpos en 3D.
"""

from __future__ import annotations

import math

import matplotlib
matplotlib.use("Qt5Agg")

import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Circle, Ellipse, Polygon, Wedge
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from ..core import figuras as fig
from .tema import Paleta

TAU = math.tau


class LienzoFigura(FigureCanvasQTAgg):
    """Lienzo que sabe dibujar las primitivas del catálogo de figuras."""

    def __init__(self, paleta: Paleta, padre=None) -> None:
        self.paleta = paleta
        self.figura_mpl = Figure(figsize=(4.2, 3.6), dpi=100, layout="constrained")
        super().__init__(self.figura_mpl)
        if padre is not None:
            self.setParent(padre)
        self.limpiar()

    # -- API pública ------------------------------------------------------- #

    def aplicar_paleta(self, paleta: Paleta) -> None:
        self.paleta = paleta
        self.limpiar()

    def limpiar(self, mensaje: str = "") -> None:
        self.figura_mpl.clear()
        self.figura_mpl.patch.set_facecolor(self.paleta.grafico_fondo)
        if mensaje:
            eje = self.figura_mpl.add_subplot(111)
            eje.set_facecolor(self.paleta.grafico_fondo)
            eje.axis("off")
            eje.text(0.5, 0.5, mensaje, ha="center", va="center", wrap=True,
                     color=self.paleta.texto_suave, fontsize=10)
        self.draw_idle()

    def dibujar(self, primitivas: list, titulo: str = "") -> None:
        """Dibuja la lista de primitivas devuelta por una figura del catálogo."""
        if not primitivas:
            self.limpiar("Esta figura no tiene\nvista previa disponible")
            return

        self.figura_mpl.clear()
        self.figura_mpl.patch.set_facecolor(self.paleta.grafico_fondo)

        solidos = [p for p in primitivas if isinstance(p, fig.Solido)]
        if solidos:
            self._dibujar_3d(solidos[0], titulo)
        else:
            self._dibujar_2d(primitivas, titulo)
        self.draw_idle()

    # -- 2D ---------------------------------------------------------------- #

    def _dibujar_2d(self, primitivas: list, titulo: str) -> None:
        eje = self.figura_mpl.add_subplot(111)
        eje.set_facecolor(self.paleta.grafico_fondo)
        relleno = self.paleta.grafico_relleno
        linea = self.paleta.grafico_linea

        for primitiva in primitivas:
            if isinstance(primitiva, fig.Poligono):
                eje.add_patch(Polygon(
                    np.array(primitiva.puntos), closed=True,
                    facecolor=relleno if primitiva.relleno else "none",
                    edgecolor=linea, linewidth=1.8,
                    alpha=0.45 if primitiva.relleno else 1.0,
                ))
            elif isinstance(primitiva, fig.Circulo):
                eje.add_patch(Circle(
                    primitiva.centro, primitiva.radio,
                    facecolor=relleno if primitiva.relleno else self.paleta.grafico_fondo,
                    edgecolor=linea, linewidth=1.8,
                    alpha=0.45 if primitiva.relleno else 1.0,
                ))
            elif isinstance(primitiva, fig.Elipse):
                eje.add_patch(Ellipse(
                    primitiva.centro, 2 * primitiva.semieje_a, 2 * primitiva.semieje_b,
                    facecolor=relleno if primitiva.relleno else "none",
                    edgecolor=linea, linewidth=1.8,
                    alpha=0.45 if primitiva.relleno else 1.0,
                ))
            elif isinstance(primitiva, fig.Sector):
                eje.add_patch(Wedge(
                    primitiva.centro, primitiva.radio, primitiva.desde, primitiva.hasta,
                    facecolor=relleno if primitiva.relleno else self.paleta.grafico_fondo,
                    edgecolor=linea, linewidth=1.8,
                    alpha=0.45 if primitiva.relleno else 1.0,
                ))
            elif isinstance(primitiva, fig.Linea):
                puntos = np.array(primitiva.puntos)
                eje.plot(puntos[:, 0], puntos[:, 1],
                         linestyle="--" if primitiva.discontinua else "-",
                         color=linea, linewidth=1.1, alpha=0.8)

        eje.set_aspect("equal", adjustable="datalim")
        eje.autoscale_view()
        eje.margins(0.12)
        self._decorar_2d(eje, titulo)

    def _decorar_2d(self, eje, titulo: str) -> None:
        eje.grid(True, color=self.paleta.grafico_rejilla, linewidth=0.5, alpha=0.6)
        eje.set_axisbelow(True)
        for lado in eje.spines.values():
            lado.set_color(self.paleta.grafico_rejilla)
        eje.tick_params(colors=self.paleta.texto_suave, labelsize=8)
        if titulo:
            eje.set_title(titulo, color=self.paleta.texto, fontsize=10, pad=6)

    # -- 3D ---------------------------------------------------------------- #

    def _dibujar_3d(self, solido: fig.Solido, titulo: str) -> None:
        eje = self.figura_mpl.add_subplot(111, projection="3d")
        eje.set_facecolor(self.paleta.grafico_fondo)

        constructor = _CONSTRUCTORES_3D.get(solido.tipo)
        if constructor is None:
            self.limpiar("Esta figura no tiene\nvista previa disponible")
            return

        resultado = constructor(solido.parametros)
        limite = 0.0

        if resultado["tipo"] == "superficie":
            x, y, z = resultado["datos"]
            eje.plot_surface(
                x, y, z, color=self.paleta.grafico_relleno, alpha=0.65,
                linewidth=0.25, edgecolor=self.paleta.grafico_linea,
                rstride=1, cstride=1, antialiased=True, shade=True,
            )
            limite = max(np.abs(x).max(), np.abs(y).max(), np.abs(z).max())
        else:  # caras
            caras = resultado["datos"]
            coleccion = Poly3DCollection(
                caras, facecolors=self.paleta.grafico_relleno, alpha=0.55,
                edgecolors=self.paleta.grafico_linea, linewidths=1.2,
            )
            eje.add_collection3d(coleccion)
            puntos = np.array([v for cara in caras for v in cara])
            limite = np.abs(puntos).max()

        limite = max(limite, 1e-6) * 1.05
        eje.set_xlim(-limite, limite)
        eje.set_ylim(-limite, limite)
        eje.set_zlim(-limite, limite)
        try:
            eje.set_box_aspect((1, 1, 1))
        except AttributeError:  # matplotlib antiguo
            pass
        eje.view_init(elev=22, azim=38)

        eje.xaxis.pane.fill = False
        eje.yaxis.pane.fill = False
        eje.zaxis.pane.fill = False
        for axis in (eje.xaxis, eje.yaxis, eje.zaxis):
            axis.pane.set_edgecolor(self.paleta.grafico_rejilla)
            axis._axinfo["grid"]["color"] = self.paleta.grafico_rejilla
        eje.tick_params(colors=self.paleta.texto_suave, labelsize=7)
        if titulo:
            eje.set_title(titulo, color=self.paleta.texto, fontsize=10, pad=2)


# --------------------------------------------------------------------------- #
# Generadores de malla para los cuerpos
# --------------------------------------------------------------------------- #

_N_ANG = 48
_N_ALT = 24


def _superficie(x, y, z) -> dict:
    return {"tipo": "superficie", "datos": (x, y, z)}


def _caras(lista) -> dict:
    return {"tipo": "caras", "datos": lista}


def _prisma_caras(vertices_base, altura: float) -> list:
    """Caras de un prisma recto a partir de los vértices de su base."""
    n = len(vertices_base)
    z0, z1 = -altura / 2, altura / 2
    inferior = [(x, y, z0) for x, y in vertices_base]
    superior = [(x, y, z1) for x, y in vertices_base]
    caras = [inferior, superior[::-1]]
    for i in range(n):
        j = (i + 1) % n
        caras.append([inferior[i], inferior[j], superior[j], superior[i]])
    return caras


def _cubo(p) -> dict:
    a = p["a"] / 2
    return _caras(_prisma_caras([(-a, -a), (a, -a), (a, a), (-a, a)], p["a"]))


def _ortoedro(p) -> dict:
    x, y = p["a"] / 2, p["b"] / 2
    return _caras(_prisma_caras([(-x, -y), (x, -y), (x, y), (-x, y)], p["c"]))


def _prisma(p) -> dict:
    n, lado = int(p["n"]), p["l"]
    radio = lado / (2 * math.sin(math.pi / n))
    base = [(radio * math.cos(TAU * i / n), radio * math.sin(TAU * i / n)) for i in range(n)]
    return _caras(_prisma_caras(base, p["h"]))


def _piramide(p) -> dict:
    n, lado, altura = int(p["n"]), p["l"], p["h"]
    radio = lado / (2 * math.sin(math.pi / n))
    z0, z1 = -altura / 2, altura / 2
    base = [(radio * math.cos(TAU * i / n), radio * math.sin(TAU * i / n), z0) for i in range(n)]
    cima = (0.0, 0.0, z1)
    caras = [base]
    for i in range(n):
        caras.append([base[i], base[(i + 1) % n], cima])
    return _caras(caras)


def _tronco_piramide(p) -> dict:
    L, l, h = p["L"] / 2, p["l"] / 2, p["h"]
    z0, z1 = -h / 2, h / 2
    inferior = [(-L, -L, z0), (L, -L, z0), (L, L, z0), (-L, L, z0)]
    superior = [(-l, -l, z1), (l, -l, z1), (l, l, z1), (-l, l, z1)]
    caras = [inferior, superior[::-1]]
    for i in range(4):
        j = (i + 1) % 4
        caras.append([inferior[i], inferior[j], superior[j], superior[i]])
    return _caras(caras)


def _cilindro(p) -> dict:
    theta = np.linspace(0, TAU, _N_ANG)
    z = np.linspace(-p["h"] / 2, p["h"] / 2, 2)
    theta, z = np.meshgrid(theta, z)
    return _superficie(p["r"] * np.cos(theta), p["r"] * np.sin(theta), z)


def _cilindro_hueco(p) -> dict:
    theta = np.linspace(0, TAU, _N_ANG)
    z = np.linspace(-p["h"] / 2, p["h"] / 2, 2)
    theta, z = np.meshgrid(theta, z)
    # Se dibuja sólo la pared exterior; el hueco se sugiere con el radio interior
    # en el título de la figura.
    return _superficie(p["R"] * np.cos(theta), p["R"] * np.sin(theta), z)


def _cono(p) -> dict:
    theta = np.linspace(0, TAU, _N_ANG)
    t = np.linspace(0, 1, _N_ALT)
    theta, t = np.meshgrid(theta, t)
    radio = p["r"] * (1 - t)
    z = -p["h"] / 2 + t * p["h"]
    return _superficie(radio * np.cos(theta), radio * np.sin(theta), z)


def _tronco_cono(p) -> dict:
    theta = np.linspace(0, TAU, _N_ANG)
    t = np.linspace(0, 1, _N_ALT)
    theta, t = np.meshgrid(theta, t)
    radio = p["R"] + (p["r"] - p["R"]) * t
    z = -p["h"] / 2 + t * p["h"]
    return _superficie(radio * np.cos(theta), radio * np.sin(theta), z)


def _esfera_parcial(radio: float, theta_max: float = math.pi) -> dict:
    u = np.linspace(0, TAU, _N_ANG)
    v = np.linspace(0, theta_max, _N_ALT)
    u, v = np.meshgrid(u, v)
    return _superficie(
        radio * np.sin(v) * np.cos(u),
        radio * np.sin(v) * np.sin(u),
        radio * np.cos(v),
    )


def _esfera(p) -> dict:
    return _esfera_parcial(p["r"])


def _semiesfera(p) -> dict:
    return _esfera_parcial(p["r"], math.pi / 2)


def _casquete(p) -> dict:
    radio, altura = p["R"], min(p["h"], 2 * p["R"])
    theta_max = math.acos(max(-1.0, min(1.0, 1 - altura / radio)))
    return _esfera_parcial(radio, theta_max)


def _zona_esferica(p) -> dict:
    radio, altura = p["R"], min(p["h"], 2 * p["R"])
    # Zona centrada en el ecuador.
    z0 = max(-radio, -altura / 2)
    z1 = min(radio, altura / 2)
    u = np.linspace(0, TAU, _N_ANG)
    z = np.linspace(z0, z1, _N_ALT)
    u, z = np.meshgrid(u, z)
    r_local = np.sqrt(np.maximum(0.0, radio ** 2 - z ** 2))
    return _superficie(r_local * np.cos(u), r_local * np.sin(u), z)


def _cuna_esferica(p) -> dict:
    radio = p["R"]
    angulo = math.radians(min(360.0, p["a"]))
    u = np.linspace(0, angulo, max(6, _N_ANG))
    v = np.linspace(0, math.pi, _N_ALT)
    u, v = np.meshgrid(u, v)
    return _superficie(
        radio * np.sin(v) * np.cos(u),
        radio * np.sin(v) * np.sin(u),
        radio * np.cos(v),
    )


def _toro(p) -> dict:
    Rmayor, rmenor = p["R"], p["r"]
    u = np.linspace(0, TAU, _N_ANG)
    v = np.linspace(0, TAU, _N_ANG)
    u, v = np.meshgrid(u, v)
    return _superficie(
        (Rmayor + rmenor * np.cos(v)) * np.cos(u),
        (Rmayor + rmenor * np.cos(v)) * np.sin(u),
        rmenor * np.sin(v),
    )


def _elipsoide(p) -> dict:
    u = np.linspace(0, TAU, _N_ANG)
    v = np.linspace(0, math.pi, _N_ALT)
    u, v = np.meshgrid(u, v)
    return _superficie(
        p["a"] * np.sin(v) * np.cos(u),
        p["b"] * np.sin(v) * np.sin(u),
        p["c"] * np.cos(v),
    )


def _paraboloide(p) -> dict:
    radio, altura = p["r"], p["h"]
    u = np.linspace(0, TAU, _N_ANG)
    t = np.linspace(0, 1, _N_ALT)
    u, t = np.meshgrid(u, t)
    r_local = radio * np.sqrt(t)
    return _superficie(
        r_local * np.cos(u), r_local * np.sin(u), -altura / 2 + t * altura
    )


def _tetraedro(p) -> dict:
    a = p["a"]
    # Vértices de un tetraedro regular inscrito en un cubo.
    escala = a / (2 * math.sqrt(2))
    v = [
        (escala, escala, escala), (escala, -escala, -escala),
        (-escala, escala, -escala), (-escala, -escala, escala),
    ]
    return _caras(_caras_triangulares(v))


def _octaedro(p) -> dict:
    d = p["a"] / math.sqrt(2)
    arriba, abajo = (0, 0, d), (0, 0, -d)
    ecuador = [(d, 0, 0), (0, d, 0), (-d, 0, 0), (0, -d, 0)]
    caras = []
    for i in range(4):
        j = (i + 1) % 4
        caras.append([arriba, ecuador[i], ecuador[j]])
        caras.append([abajo, ecuador[i], ecuador[j]])
    return _caras(caras)


def _icosaedro(p) -> dict:
    phi = (1 + math.sqrt(5)) / 2
    escala = p["a"] / 2
    base = []
    for signo_a in (1, -1):
        for signo_b in (1, -1):
            base.extend([
                (0, signo_a * 1, signo_b * phi),
                (signo_a * 1, signo_b * phi, 0),
                (signo_a * phi, 0, signo_b * 1),
            ])
    vertices = [tuple(escala * c for c in v) for v in dict.fromkeys(base)]
    return _caras(_caras_triangulares(vertices))


def _dodecaedro(p) -> dict:
    phi = (1 + math.sqrt(5)) / 2
    inv = 1 / phi
    # Con estos vértices la arista mide 2/phi.
    escala = p["a"] / (2 * inv)

    crudos: list[tuple[float, float, float]] = []
    for sx in (1, -1):
        for sy in (1, -1):
            for sz in (1, -1):
                crudos.append((sx * 1.0, sy * 1.0, sz * 1.0))
    for sa in (1, -1):
        for sb in (1, -1):
            crudos.append((0.0, sa * inv, sb * phi))
            crudos.append((sa * inv, sb * phi, 0.0))
            crudos.append((sa * phi, 0.0, sb * inv))
    vertices = [tuple(escala * c for c in v) for v in dict.fromkeys(crudos)]

    # Las caras del dodecaedro apuntan hacia los vértices del icosaedro dual.
    normales: list[tuple[float, float, float]] = []
    for sa in (1, -1):
        for sb in (1, -1):
            normales.append((0.0, sa * 1.0, sb * phi))
            normales.append((sa * 1.0, sb * phi, 0.0))
            normales.append((sa * phi, 0.0, sb * 1.0))

    return _caras(_caras_por_planos(vertices, normales))


def _caras_triangulares(vertices: list) -> list:
    """Caras de un poliedro de caras triangulares (tetraedro, octaedro, icosaedro).

    Todas las aristas miden lo mismo, así que basta con buscar los tríos de
    vértices mutuamente adyacentes.
    """
    puntos = np.array(vertices, dtype=float)
    n = len(puntos)
    distancias = np.linalg.norm(puntos[:, None, :] - puntos[None, :, :], axis=2)
    np.fill_diagonal(distancias, np.inf)
    tolerancia = distancias.min() * 1.15

    vecinos = {i: [j for j in range(n) if distancias[i, j] <= tolerancia] for i in range(n)}
    triangulos = set()
    for i in range(n):
        for j in vecinos[i]:
            for k in vecinos[j]:
                if k != i and distancias[i, k] <= tolerancia:
                    triangulos.add(tuple(sorted((i, j, k))))

    return [[tuple(puntos[i]) for i in tri] for tri in sorted(triangulos)]


def _caras_por_planos(vertices: list, normales: list) -> list:
    """Agrupa los vértices en caras planas, una por cada dirección normal dada.

    Para cada normal se toman los vértices con proyección máxima (los que están
    sobre esa cara) y se ordenan por su ángulo alrededor de la normal, para que el
    polígono resultante no salga cruzado.
    """
    puntos = np.array(vertices, dtype=float)
    caras = []

    for normal in normales:
        n = np.array(normal, dtype=float)
        n = n / np.linalg.norm(n)
        proyeccion = puntos @ n
        tolerancia = 1e-6 * max(1.0, float(np.abs(proyeccion).max()))
        indices = np.flatnonzero(proyeccion >= proyeccion.max() - tolerancia)
        if len(indices) < 3:
            continue

        centro = puntos[indices].mean(axis=0)
        u = puntos[indices[0]] - centro
        norma_u = np.linalg.norm(u)
        if norma_u == 0:
            continue
        u = u / norma_u
        v = np.cross(n, u)

        def angulo(indice: int) -> float:
            radio = puntos[indice] - centro
            return math.atan2(float(radio @ v), float(radio @ u))

        orden = sorted(indices.tolist(), key=angulo)
        caras.append([tuple(puntos[i]) for i in orden])

    return caras


_CONSTRUCTORES_3D = {
    "cubo": _cubo,
    "ortoedro": _ortoedro,
    "prisma": _prisma,
    "piramide": _piramide,
    "tronco_piramide": _tronco_piramide,
    "cilindro": _cilindro,
    "cilindro_hueco": _cilindro_hueco,
    "cono": _cono,
    "tronco_cono": _tronco_cono,
    "esfera": _esfera,
    "semiesfera": _semiesfera,
    "casquete": _casquete,
    "sector_esferico": _casquete,
    "zona_esferica": _zona_esferica,
    "cuna_esferica": _cuna_esferica,
    "toro": _toro,
    "elipsoide": _elipsoide,
    "paraboloide": _paraboloide,
    "tetraedro": _tetraedro,
    "octaedro": _octaedro,
    "icosaedro": _icosaedro,
    "dodecaedro": _dodecaedro,
}
