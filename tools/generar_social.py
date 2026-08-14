"""Genera la imagen que se ve al compartir el enlace de Axioma.

WhatsApp, Telegram, Twitter o Google muestran esta imagen junto al enlace. Sin
ella sale un recuadro gris, y un enlace sin cara se comparte mucho menos.

Mide 1200×630, que es lo que esperan todos.

    python tools/generar_social.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "web" / "social.png"

ANCHO, ALTO = 1200, 630
FONDO = (13, 17, 23)
PANEL = (22, 27, 38)
ACENTO = (74, 158, 255)
TEXTO = (230, 237, 243)
SUAVE = (139, 152, 172)


def _fuente(tamano: int, negrita: bool = False):
    """La fuente del sistema; si no aparece, la de reserva de Pillow."""
    for nombre in (("segoeuib.ttf", "arialbd.ttf") if negrita
                   else ("segoeui.ttf", "arial.ttf")):
        try:
            return ImageFont.truetype(nombre, tamano)
        except OSError:
            continue
    return ImageFont.load_default(tamano)


def construir() -> Image.Image:
    imagen = Image.new("RGB", (ANCHO, ALTO), FONDO)
    dibujo = ImageDraw.Draw(imagen)

    # Franja de acento a la izquierda, como el lateral de la aplicación.
    dibujo.rectangle([0, 0, 12, ALTO], fill=ACENTO)

    icono = Image.open(RAIZ / "web" / "icono-512.png").convert("RGBA")
    icono = icono.resize((180, 180), Image.LANCZOS)
    imagen.paste(icono, (80, 80), icono)

    dibujo.text((300, 96), "Axioma", font=_fuente(92, True), fill=TEXTO)
    dibujo.text((305, 205), "calculadora científica", font=_fuente(40), fill=ACENTO)

    lineas = [
        "Dieciséis apartados en una sola pantalla",
        "Geometría, ecuaciones paso a paso, unidades y cálculo",
        "En el móvil y en el ordenador · Sin conexión · Gratis",
    ]
    y = 330
    for linea in lineas:
        dibujo.text((80, y), linea, font=_fuente(34), fill=TEXTO if y == 330 else SUAVE)
        y += 58

    # Pie con la dirección, que es a donde se quiere llevar a quien la vea.
    dibujo.rectangle([0, ALTO - 78, ANCHO, ALTO], fill=PANEL)
    dibujo.text((80, ALTO - 56), "erlanders177.github.io/Axioma",
                font=_fuente(32), fill=ACENTO)
    return imagen


def main() -> None:
    construir().save(DESTINO, optimize=True)
    print(f"escrito {DESTINO.relative_to(RAIZ)}  ({ANCHO}×{ALTO})")


if __name__ == "__main__":
    main()
