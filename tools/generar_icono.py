"""Genera el icono de Axioma.

Se guarda como script en lugar de subir sólo el binario para que el icono sea
reproducible: si algún día cambian los colores del tema, basta con volver a
ejecutarlo.

    python tools/generar_icono.py

Produce ``assets/axioma.ico`` (con los tamaños que pide Windows) y
``assets/axioma.png`` (256 px, para el README o la web).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

# Colores del tema oscuro de la aplicación (src/ui/tema.py).
FONDO = (26, 32, 48)        # #1a2030
ACENTO = (76, 141, 255)     # #4c8dff
CLARO = (143, 184, 255)     # #8fb8ff

#: Se dibuja en grande y se reduce, para que los bordes salgan suavizados.
LIENZO = 1024

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "assets"

#: Tamaños que Windows espera dentro de un .ico.
TAMANOS = [16, 24, 32, 48, 64, 128, 256]


def _rectangulo_redondeado(dibujo: ImageDraw.ImageDraw, radio: int) -> None:
    margen = int(LIENZO * 0.04)
    dibujo.rounded_rectangle(
        [margen, margen, LIENZO - margen, LIENZO - margen],
        radius=radio, fill=FONDO,
    )


def _triangulo_axioma(dibujo: ImageDraw.ImageDraw) -> None:
    """Una «A» construida como un triángulo, que evoca a la vez letra y figura.

    Es el mismo motivo que usa el icono del módulo de geometría (△), así que la
    marca queda coherente con la aplicación.
    """
    centro_x = LIENZO / 2
    alto = LIENZO * 0.50
    base = LIENZO * 0.46
    cima_y = LIENZO * 0.25
    base_y = cima_y + alto
    grosor = int(LIENZO * 0.075)

    izquierda = (centro_x - base / 2, base_y)
    derecha = (centro_x + base / 2, base_y)
    cima = (centro_x, cima_y)

    # Los dos lados de la «A», con degradado del acento al tono claro.
    dibujo.line([izquierda, cima], fill=ACENTO, width=grosor, joint="curve")
    dibujo.line([cima, derecha], fill=CLARO, width=grosor, joint="curve")

    # El travesaño, a la altura donde lo pondría una A tipográfica.
    proporcion = 0.62
    travesano_y = cima_y + alto * proporcion
    mitad = (base / 2) * proporcion
    dibujo.line(
        [(centro_x - mitad, travesano_y), (centro_x + mitad, travesano_y)],
        fill=ACENTO, width=int(grosor * 0.8),
    )

    # Remate redondeado en los vértices: sin esto las puntas quedan cortadas.
    for punto in (izquierda, derecha, cima):
        radio = grosor / 2
        dibujo.ellipse(
            [punto[0] - radio, punto[1] - radio, punto[0] + radio, punto[1] + radio],
            fill=CLARO if punto is cima else ACENTO,
        )


def _puntos_therefore(dibujo: ImageDraw.ImageDraw) -> None:
    """Los tres puntos de «∴» (luego), el símbolo de la deducción y el axioma."""
    radio = LIENZO * 0.030
    centro_x = LIENZO / 2
    fila_y = LIENZO * 0.845
    separacion = LIENZO * 0.105

    for desplazamiento in (-separacion, 0, separacion):
        x = centro_x + desplazamiento
        dibujo.ellipse(
            [x - radio, fila_y - radio, x + radio, fila_y + radio],
            fill=CLARO,
        )


def construir() -> Image.Image:
    imagen = Image.new("RGBA", (LIENZO, LIENZO), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)

    _rectangulo_redondeado(dibujo, radio=int(LIENZO * 0.20))
    _triangulo_axioma(dibujo)
    _puntos_therefore(dibujo)
    return imagen


def main() -> None:
    DESTINO.mkdir(parents=True, exist_ok=True)
    imagen = construir()

    png = DESTINO / "axioma.png"
    imagen.resize((256, 256), Image.LANCZOS).save(png)

    ico = DESTINO / "axioma.ico"
    imagen.save(ico, format="ICO", sizes=[(t, t) for t in TAMANOS])

    print(f"escrito {png.relative_to(RAIZ)}")
    print(f"escrito {ico.relative_to(RAIZ)}  ({len(TAMANOS)} tamaños)")


if __name__ == "__main__":
    main()
