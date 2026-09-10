"""Catálogo de unidades y motor de conversión.

Cada categoría define una unidad **base** y describe el resto en función de ella
mediante una relación afín o inversa:

* Normal:  ``base = valor * factor + desplazamiento``
* Inversa: ``base = factor / valor``   (consumo de combustible)

Con esas dos formas se cubren todas las unidades del catálogo, incluidas las
escalas de temperatura (que necesitan desplazamiento) y las escalas Delisle
(que además tienen factor negativo).

Nota sobre la versión anterior: ``convertir_universal`` multiplicaba por
``factor_destino / factor_origen``, que es la razón invertida. Convertir 1 km a
metros devolvía 0.001 en lugar de 1000, y lo mismo para todas las magnitudes.
Además la temperatura sólo funcionaba si uno de los dos extremos era kelvin, y
la unidad ``g/L`` de concentración era un diccionario que hacía fallar la
conversión siempre.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .formato import normalizar

__all__ = [
    "Unidad",
    "Categoria",
    "CATEGORIAS",
    "GRUPOS",
    "ErrorConversion",
    "convertir",
    "categoria",
    "buscar",
    "tabla_completa",
]


class ErrorConversion(ValueError):
    """No se pudo realizar la conversión solicitada."""


@dataclass(frozen=True)
class Unidad:
    simbolo: str
    nombre: str
    factor: float
    desplazamiento: float = 0.0
    inversa: bool = False

    @property
    def etiqueta(self) -> str:
        return f"{self.simbolo} — {self.nombre}"

    def a_base(self, valor: float) -> float:
        if self.inversa:
            if valor == 0:
                raise ErrorConversion(f"El valor 0 no es convertible en {self.simbolo}")
            return self.factor / valor
        return valor * self.factor + self.desplazamiento

    def desde_base(self, base: float) -> float:
        if self.inversa:
            if base == 0:
                raise ErrorConversion(f"El resultado no es representable en {self.simbolo}")
            return self.factor / base
        return (base - self.desplazamiento) / self.factor


@dataclass(frozen=True)
class Categoria:
    nombre: str
    grupo: str
    unidades: tuple[Unidad, ...]
    nota: str = ""
    _indice: dict = field(default_factory=dict, repr=False, compare=False)

    def __post_init__(self) -> None:
        indice = {u.simbolo: u for u in self.unidades}
        if len(indice) != len(self.unidades):
            raise ValueError(f"Símbolos duplicados en la categoría {self.nombre!r}")
        object.__setattr__(self, "_indice", indice)

    @property
    def predeterminada(self) -> Unidad:
        """Unidad que la interfaz muestra seleccionada al abrir la categoría."""
        return self.unidades[0]

    @property
    def unidad_base(self) -> Unidad:
        """Unidad de referencia interna (factor 1, sin desplazamiento)."""
        for unidad in self.unidades:
            if unidad.factor == 1.0 and unidad.desplazamiento == 0.0 and not unidad.inversa:
                return unidad
        return self.unidades[0]

    @property
    def simbolos(self) -> list[str]:
        return [u.simbolo for u in self.unidades]

    def unidad(self, simbolo: str) -> Unidad:
        try:
            return self._indice[simbolo]
        except KeyError:
            raise ErrorConversion(
                f"La unidad {simbolo!r} no pertenece a {self.nombre}"
            ) from None


def _u(simbolo: str, nombre: str, factor: float, desplazamiento: float = 0.0, inversa: bool = False) -> Unidad:
    return Unidad(simbolo, nombre, factor, desplazamiento, inversa)


# Constantes reutilizadas, con los valores exactos de las definiciones SI.
_PULGADA = 0.0254
_PIE = 0.3048
_MILLA = 1609.344
_LIBRA = 0.45359237
_GALON_US = 3.785411784e-3
_GALON_UK = 4.54609e-3
_G0 = 9.80665
_CAL = 4.184
_BTU = 1055.05585262
_EV = 1.602176634e-19
_AVOGADRO = 6.02214076e23


# --------------------------------------------------------------------------- #
# Catálogo
# --------------------------------------------------------------------------- #

_CATALOGO: list[Categoria] = [
    # ------------------------------- Básicas ------------------------------- #
    Categoria("Longitud", "Básicas", (
        _u("m", "metro", 1.0),
        _u("km", "kilómetro", 1000.0),
        _u("hm", "hectómetro", 100.0),
        _u("dam", "decámetro", 10.0),
        _u("dm", "decímetro", 0.1),
        _u("cm", "centímetro", 0.01),
        _u("mm", "milímetro", 1e-3),
        _u("µm", "micrómetro (micra)", 1e-6),
        _u("nm", "nanómetro", 1e-9),
        _u("pm", "picómetro", 1e-12),
        _u("fm", "femtómetro (fermi)", 1e-15),
        _u("Å", "ángstrom", 1e-10),
        _u("in", "pulgada", _PULGADA),
        _u("ft", "pie", _PIE),
        _u("yd", "yarda", 0.9144),
        _u("mi", "milla terrestre", _MILLA),
        _u("nmi", "milla náutica", 1852.0),
        _u("mil", "milésima de pulgada", _PULGADA / 1000),
        _u("braza", "braza (fathom)", 1.8288),
        _u("rod", "pértiga (rod)", 5.0292),
        _u("cadena", "cadena (chain)", 20.1168),
        _u("furlong", "furlong", 201.168),
        _u("legua", "legua terrestre", 4828.032),
        _u("vara", "vara castellana", 0.835905),
        _u("pt", "punto tipográfico", _PULGADA / 72),
        _u("pica", "pica", _PULGADA / 6),
        _u("ua", "unidad astronómica", 1.495978707e11),
        _u("ly", "año luz", 9.4607304725808e15),
        _u("pc", "pársec", 3.0856775814913673e16),
    )),

    Categoria("Área", "Básicas", (
        _u("m²", "metro cuadrado", 1.0),
        _u("km²", "kilómetro cuadrado", 1e6),
        _u("ha", "hectárea", 1e4),
        _u("a", "área", 100.0),
        _u("dm²", "decímetro cuadrado", 0.01),
        _u("cm²", "centímetro cuadrado", 1e-4),
        _u("mm²", "milímetro cuadrado", 1e-6),
        _u("µm²", "micrómetro cuadrado", 1e-12),
        _u("in²", "pulgada cuadrada", _PULGADA ** 2),
        _u("ft²", "pie cuadrado", _PIE ** 2),
        _u("yd²", "yarda cuadrada", 0.9144 ** 2),
        _u("mi²", "milla cuadrada", _MILLA ** 2),
        _u("acre", "acre", 4046.8564224),
        _u("barn", "barn", 1e-28),
    )),

    Categoria("Volumen", "Básicas", (
        _u("L", "litro", 1e-3),
        _u("m³", "metro cúbico", 1.0),
        _u("km³", "kilómetro cúbico", 1e9),
        _u("dm³", "decímetro cúbico", 1e-3),
        _u("cm³", "centímetro cúbico", 1e-6),
        _u("mm³", "milímetro cúbico", 1e-9),
        _u("hL", "hectolitro", 0.1),
        _u("daL", "decalitro", 0.01),
        _u("dL", "decilitro", 1e-4),
        _u("cL", "centilitro", 1e-5),
        _u("mL", "mililitro", 1e-6),
        _u("µL", "microlitro", 1e-9),
        _u("in³", "pulgada cúbica", _PULGADA ** 3),
        _u("ft³", "pie cúbico", _PIE ** 3),
        _u("yd³", "yarda cúbica", 0.9144 ** 3),
        _u("gal US", "galón estadounidense", _GALON_US),
        _u("gal UK", "galón imperial", _GALON_UK),
        _u("qt US", "cuarto estadounidense", _GALON_US / 4),
        _u("qt UK", "cuarto imperial", _GALON_UK / 4),
        _u("pt US", "pinta estadounidense", _GALON_US / 8),
        _u("pt UK", "pinta imperial", _GALON_UK / 8),
        _u("fl oz US", "onza líquida estadounidense", _GALON_US / 128),
        _u("fl oz UK", "onza líquida imperial", _GALON_UK / 160),
        _u("bbl", "barril de petróleo", 0.158987294928),
        _u("acre·ft", "acre-pie", 1233.4818375),
    )),

    Categoria("Masa", "Básicas", (
        _u("kg", "kilogramo", 1.0),
        _u("g", "gramo", 1e-3),
        _u("mg", "miligramo", 1e-6),
        _u("µg", "microgramo", 1e-9),
        _u("ng", "nanogramo", 1e-12),
        _u("t", "tonelada métrica", 1000.0),
        _u("q", "quintal métrico", 100.0),
        _u("lb", "libra", _LIBRA),
        _u("oz", "onza", _LIBRA / 16),
        _u("oz t", "onza troy", 0.0311034768),
        _u("gr", "grano", _LIBRA / 7000),
        _u("st", "stone", _LIBRA * 14),
        _u("ton US", "tonelada corta (EE. UU.)", _LIBRA * 2000),
        _u("ton UK", "tonelada larga (imperial)", _LIBRA * 2240),
        _u("cwt", "quintal estadounidense", _LIBRA * 100),
        _u("slug", "slug", 14.5939029372),
        _u("u", "unidad de masa atómica (dalton)", 1.66053906660e-27),
        _u("ct", "quilate métrico", 2e-4),
        _u("arroba", "arroba castellana", 11.502),
    )),

    Categoria("Tiempo", "Básicas", (
        _u("s", "segundo", 1.0),
        _u("ms", "milisegundo", 1e-3),
        _u("µs", "microsegundo", 1e-6),
        _u("ns", "nanosegundo", 1e-9),
        _u("ps", "picosegundo", 1e-12),
        _u("min", "minuto", 60.0),
        _u("h", "hora", 3600.0),
        _u("d", "día", 86400.0),
        _u("sem", "semana", 604800.0),
        _u("quincena", "quincena (14 días)", 1209600.0),
        _u("mes (30 d)", "mes de 30 días", 2592000.0),
        _u("mes medio", "mes medio (365,25/12 días)", 2629800.0),
        _u("año (365 d)", "año común", 31536000.0),
        _u("año juliano", "año juliano (365,25 días)", 31557600.0),
        _u("década", "década juliana", 315576000.0),
        _u("siglo", "siglo juliano", 3155760000.0),
        _u("milenio", "milenio juliano", 31557600000.0),
    ), nota="El «mes» y el «año» no tienen duración única; se indica la convención usada."),

    Categoria("Temperatura", "Básicas", (
        _u("K", "kelvin", 1.0, 0.0),
        _u("°C", "grado Celsius", 1.0, 273.15),
        _u("°F", "grado Fahrenheit", 5 / 9, 273.15 - 32 * 5 / 9),
        _u("°R", "grado Rankine", 5 / 9, 0.0),
        _u("°Ré", "grado Réaumur", 1.25, 273.15),
        _u("°De", "grado Delisle", -2 / 3, 373.15),
        _u("°N", "grado Newton", 100 / 33, 273.15),
        _u("°Rø", "grado Rømer", 40 / 21, 273.15 - 7.5 * 40 / 21),
    ), nota="Escalas absolutas y relativas; la conversión usa la relación afín completa."),

    Categoria("Ángulo", "Básicas", (
        _u("rad", "radián", 1.0),
        _u("°", "grado sexagesimal", math.pi / 180),
        _u("′", "minuto de arco", math.pi / 10800),
        _u("″", "segundo de arco", math.pi / 648000),
        _u("gon", "gradián (grado centesimal)", math.pi / 200),
        _u("mrad", "milirradián", 1e-3),
        _u("vuelta", "vuelta completa", 2 * math.pi),
        _u("cuadrante", "cuadrante (90°)", math.pi / 2),
        _u("sextante", "sextante (60°)", math.pi / 3),
        _u("mil", "milésima artillera (OTAN)", 2 * math.pi / 6400),
    )),

    Categoria("Velocidad", "Básicas", (
        _u("m/s", "metro por segundo", 1.0),
        _u("km/h", "kilómetro por hora", 1 / 3.6),
        _u("km/s", "kilómetro por segundo", 1000.0),
        _u("cm/s", "centímetro por segundo", 0.01),
        _u("mm/s", "milímetro por segundo", 1e-3),
        _u("m/min", "metro por minuto", 1 / 60),
        _u("mph", "milla por hora", _MILLA / 3600),
        _u("ft/s", "pie por segundo", _PIE),
        _u("ft/min", "pie por minuto", _PIE / 60),
        _u("in/s", "pulgada por segundo", _PULGADA),
        _u("kn", "nudo", 1852.0 / 3600),
        _u("Mach", "Mach (aire a nivel del mar, 15 °C)", 340.29),
        _u("c", "velocidad de la luz", 299792458.0),
    )),

    Categoria("Aceleración", "Básicas", (
        _u("m/s²", "metro por segundo al cuadrado", 1.0),
        _u("km/s²", "kilómetro por segundo al cuadrado", 1000.0),
        _u("cm/s²", "gal (centímetro por s²)", 0.01),
        _u("mm/s²", "milímetro por segundo al cuadrado", 1e-3),
        _u("g", "gravedad estándar", _G0),
        _u("ft/s²", "pie por segundo al cuadrado", _PIE),
        _u("in/s²", "pulgada por segundo al cuadrado", _PULGADA),
        _u("km/h/s", "kilómetro por hora y segundo", 1 / 3.6),
        _u("mph/s", "milla por hora y segundo", _MILLA / 3600),
    )),

    # ------------------------------ Mecánica ------------------------------- #
    Categoria("Fuerza", "Mecánica", (
        _u("N", "newton", 1.0),
        _u("kN", "kilonewton", 1000.0),
        _u("MN", "meganewton", 1e6),
        _u("mN", "milinewton", 1e-3),
        _u("µN", "micronewton", 1e-6),
        _u("dyn", "dina", 1e-5),
        _u("kgf", "kilogramo-fuerza", _G0),
        _u("gf", "gramo-fuerza", _G0 * 1e-3),
        _u("tf", "tonelada-fuerza", _G0 * 1000),
        _u("lbf", "libra-fuerza", _LIBRA * _G0),
        _u("ozf", "onza-fuerza", _LIBRA * _G0 / 16),
        _u("kip", "kip (1000 lbf)", _LIBRA * _G0 * 1000),
        _u("pdl", "poundal", 0.138254954376),
        _u("sn", "sthène", 1000.0),
    )),

    Categoria("Presión", "Mecánica", (
        _u("Pa", "pascal", 1.0),
        _u("hPa", "hectopascal", 100.0),
        _u("kPa", "kilopascal", 1000.0),
        _u("MPa", "megapascal", 1e6),
        _u("GPa", "gigapascal", 1e9),
        _u("mPa", "milipascal", 1e-3),
        _u("bar", "bar", 1e5),
        _u("mbar", "milibar", 100.0),
        _u("µbar", "microbar", 0.1),
        _u("atm", "atmósfera estándar", 101325.0),
        _u("at", "atmósfera técnica (kgf/cm²)", 98066.5),
        _u("Torr", "torr", 101325.0 / 760),
        _u("mmHg", "milímetro de mercurio", 133.322387415),
        _u("cmHg", "centímetro de mercurio", 1333.22387415),
        _u("inHg", "pulgada de mercurio", 3386.388640341),
        _u("mmH₂O", "milímetro de columna de agua", _G0),
        _u("cmH₂O", "centímetro de columna de agua", _G0 * 10),
        _u("mH₂O", "metro de columna de agua", _G0 * 1000),
        _u("inH₂O", "pulgada de columna de agua", 249.0889083),
        _u("psi", "libra por pulgada cuadrada", _LIBRA * _G0 / _PULGADA ** 2),
        _u("ksi", "kilolibra por pulgada cuadrada", _LIBRA * _G0 / _PULGADA ** 2 * 1000),
        _u("psf", "libra por pie cuadrado", _LIBRA * _G0 / _PIE ** 2),
        _u("baria", "baria (dyn/cm²)", 0.1),
    )),

    Categoria("Energía y trabajo", "Mecánica", (
        _u("J", "julio", 1.0),
        _u("mJ", "milijulio", 1e-3),
        _u("kJ", "kilojulio", 1000.0),
        _u("MJ", "megajulio", 1e6),
        _u("GJ", "gigajulio", 1e9),
        _u("TJ", "terajulio", 1e12),
        _u("cal", "caloría termoquímica", _CAL),
        _u("kcal", "kilocaloría (caloría alimentaria)", _CAL * 1000),
        _u("cal IT", "caloría internacional", 4.1868),
        _u("Wh", "vatio-hora", 3600.0),
        _u("kWh", "kilovatio-hora", 3.6e6),
        _u("MWh", "megavatio-hora", 3.6e9),
        _u("GWh", "gigavatio-hora", 3.6e12),
        _u("eV", "electronvoltio", _EV),
        _u("keV", "kiloelectronvoltio", _EV * 1e3),
        _u("MeV", "megaelectronvoltio", _EV * 1e6),
        _u("GeV", "gigaelectronvoltio", _EV * 1e9),
        _u("erg", "ergio", 1e-7),
        _u("BTU", "unidad térmica británica", _BTU),
        _u("therm", "therm (100 000 BTU)", _BTU * 1e5),
        _u("ft·lbf", "pie-libra fuerza", _PIE * _LIBRA * _G0),
        _u("in·lbf", "pulgada-libra fuerza", _PULGADA * _LIBRA * _G0),
        _u("kgf·m", "kilogramo fuerza-metro", _G0),
        _u("t TNT", "tonelada equivalente de TNT", 4.184e9),
        _u("kt TNT", "kilotón de TNT", 4.184e12),
        _u("Mt TNT", "megatón de TNT", 4.184e15),
        _u("Eh", "hartree", 4.3597447222071e-18),
    )),

    Categoria("Potencia", "Mecánica", (
        _u("W", "vatio", 1.0),
        _u("mW", "milivatio", 1e-3),
        _u("µW", "microvatio", 1e-6),
        _u("kW", "kilovatio", 1000.0),
        _u("MW", "megavatio", 1e6),
        _u("GW", "gigavatio", 1e9),
        _u("TW", "teravatio", 1e12),
        _u("CV", "caballo de vapor (métrico)", 735.49875),
        _u("hp", "horsepower mecánico", _PIE * _LIBRA * _G0 * 550),
        _u("hp el.", "horsepower eléctrico", 746.0),
        _u("BTU/h", "BTU por hora", _BTU / 3600),
        _u("BTU/s", "BTU por segundo", _BTU),
        _u("cal/s", "caloría por segundo", _CAL),
        _u("kcal/h", "kilocaloría por hora", _CAL * 1000 / 3600),
        _u("erg/s", "ergio por segundo", 1e-7),
        _u("ft·lbf/s", "pie-libra fuerza por segundo", _PIE * _LIBRA * _G0),
        _u("TR", "tonelada de refrigeración", 3516.8528420667),
    )),

    Categoria("Par (torque)", "Mecánica", (
        _u("N·m", "newton-metro", 1.0),
        _u("kN·m", "kilonewton-metro", 1000.0),
        _u("mN·m", "milinewton-metro", 1e-3),
        _u("N·cm", "newton-centímetro", 0.01),
        _u("N·mm", "newton-milímetro", 1e-3),
        _u("kgf·m", "kilogramo fuerza-metro", _G0),
        _u("kgf·cm", "kilogramo fuerza-centímetro", _G0 * 0.01),
        _u("gf·cm", "gramo fuerza-centímetro", _G0 * 1e-5),
        _u("lbf·ft", "libra fuerza-pie", _LIBRA * _G0 * _PIE),
        _u("lbf·in", "libra fuerza-pulgada", _LIBRA * _G0 * _PULGADA),
        _u("ozf·in", "onza fuerza-pulgada", _LIBRA * _G0 * _PULGADA / 16),
        _u("dyn·cm", "dina-centímetro", 1e-7),
    )),

    Categoria("Frecuencia", "Mecánica", (
        _u("Hz", "hercio", 1.0),
        _u("mHz", "milihercio", 1e-3),
        _u("kHz", "kilohercio", 1000.0),
        _u("MHz", "megahercio", 1e6),
        _u("GHz", "gigahercio", 1e9),
        _u("THz", "terahercio", 1e12),
        _u("rpm", "revolución por minuto", 1 / 60),
        _u("rps", "revolución por segundo", 1.0),
        _u("bpm", "pulsación por minuto", 1 / 60),
    )),

    Categoria("Velocidad angular", "Mecánica", (
        _u("rad/s", "radián por segundo", 1.0),
        _u("rad/min", "radián por minuto", 1 / 60),
        _u("°/s", "grado por segundo", math.pi / 180),
        _u("°/min", "grado por minuto", math.pi / 10800),
        _u("rpm", "revolución por minuto", 2 * math.pi / 60),
        _u("rps", "revolución por segundo", 2 * math.pi),
        _u("gon/s", "gradián por segundo", math.pi / 200),
    )),

    # ------------------------------- Térmica ------------------------------- #
    Categoria("Capacidad térmica específica", "Térmica", (
        _u("J/(kg·K)", "julio por kilogramo y kelvin", 1.0),
        _u("kJ/(kg·K)", "kilojulio por kilogramo y kelvin", 1000.0),
        _u("J/(g·°C)", "julio por gramo y grado Celsius", 1000.0),
        _u("cal/(g·°C)", "caloría por gramo y grado Celsius", _CAL * 1000),
        _u("kcal/(kg·°C)", "kilocaloría por kilogramo y grado Celsius", _CAL * 1000),
        _u("BTU/(lb·°F)", "BTU por libra y grado Fahrenheit", 4186.8),
    )),

    Categoria("Conductividad térmica", "Térmica", (
        _u("W/(m·K)", "vatio por metro y kelvin", 1.0),
        _u("kW/(m·K)", "kilovatio por metro y kelvin", 1000.0),
        _u("mW/(m·K)", "milivatio por metro y kelvin", 1e-3),
        _u("cal/(s·cm·°C)", "caloría por segundo, centímetro y grado Celsius", _CAL * 100),
        _u("kcal/(h·m·°C)", "kilocaloría por hora, metro y grado Celsius", _CAL * 1000 / 3600),
        _u("BTU/(h·ft·°F)", "BTU por hora, pie y grado Fahrenheit", 1.7307346664),
        _u("BTU·in/(h·ft²·°F)", "BTU-pulgada por hora, pie² y °F", 0.1442278889),
    )),

    # ------------------------------- Fluidos ------------------------------- #
    Categoria("Caudal volumétrico", "Fluidos", (
        _u("m³/s", "metro cúbico por segundo", 1.0),
        _u("m³/min", "metro cúbico por minuto", 1 / 60),
        _u("m³/h", "metro cúbico por hora", 1 / 3600),
        _u("m³/d", "metro cúbico por día", 1 / 86400),
        _u("L/s", "litro por segundo", 1e-3),
        _u("L/min", "litro por minuto", 1e-3 / 60),
        _u("L/h", "litro por hora", 1e-3 / 3600),
        _u("mL/s", "mililitro por segundo", 1e-6),
        _u("mL/min", "mililitro por minuto", 1e-6 / 60),
        _u("ft³/s", "pie cúbico por segundo (cfs)", _PIE ** 3),
        _u("ft³/min", "pie cúbico por minuto (cfm)", _PIE ** 3 / 60),
        _u("ft³/h", "pie cúbico por hora", _PIE ** 3 / 3600),
        _u("gal/min", "galón EE. UU. por minuto (gpm)", _GALON_US / 60),
        _u("gal/h", "galón EE. UU. por hora", _GALON_US / 3600),
        _u("gal/d", "galón EE. UU. por día", _GALON_US / 86400),
        _u("bbl/d", "barril de petróleo por día", 0.158987294928 / 86400),
    )),

    Categoria("Caudal másico", "Fluidos", (
        _u("kg/s", "kilogramo por segundo", 1.0),
        _u("kg/min", "kilogramo por minuto", 1 / 60),
        _u("kg/h", "kilogramo por hora", 1 / 3600),
        _u("g/s", "gramo por segundo", 1e-3),
        _u("g/min", "gramo por minuto", 1e-3 / 60),
        _u("t/h", "tonelada por hora", 1000 / 3600),
        _u("t/d", "tonelada por día", 1000 / 86400),
        _u("lb/s", "libra por segundo", _LIBRA),
        _u("lb/min", "libra por minuto", _LIBRA / 60),
        _u("lb/h", "libra por hora", _LIBRA / 3600),
        _u("oz/s", "onza por segundo", _LIBRA / 16),
    )),

    Categoria("Densidad", "Fluidos", (
        _u("kg/m³", "kilogramo por metro cúbico", 1.0),
        _u("g/cm³", "gramo por centímetro cúbico", 1000.0),
        _u("g/mL", "gramo por mililitro", 1000.0),
        _u("kg/L", "kilogramo por litro", 1000.0),
        _u("t/m³", "tonelada por metro cúbico", 1000.0),
        _u("g/L", "gramo por litro", 1.0),
        _u("mg/mL", "miligramo por mililitro", 1.0),
        _u("mg/L", "miligramo por litro", 1e-3),
        _u("lb/ft³", "libra por pie cúbico", _LIBRA / _PIE ** 3),
        _u("lb/in³", "libra por pulgada cúbica", _LIBRA / _PULGADA ** 3),
        _u("lb/gal", "libra por galón EE. UU.", _LIBRA / _GALON_US),
        _u("oz/in³", "onza por pulgada cúbica", _LIBRA / 16 / _PULGADA ** 3),
        _u("slug/ft³", "slug por pie cúbico", 14.5939029372 / _PIE ** 3),
    )),

    Categoria("Viscosidad dinámica", "Fluidos", (
        _u("Pa·s", "pascal-segundo", 1.0),
        _u("mPa·s", "milipascal-segundo", 1e-3),
        _u("P", "poise", 0.1),
        _u("cP", "centipoise", 1e-3),
        _u("µP", "micropoise", 1e-7),
        _u("kgf·s/m²", "kilogramo fuerza-segundo por metro cuadrado", _G0),
        _u("lbf·s/ft²", "libra fuerza-segundo por pie cuadrado", _LIBRA * _G0 / _PIE ** 2),
        _u("lb/(ft·s)", "libra por pie y segundo", _LIBRA / _PIE),
    )),

    Categoria("Viscosidad cinemática", "Fluidos", (
        _u("m²/s", "metro cuadrado por segundo", 1.0),
        _u("St", "stokes (cm²/s)", 1e-4),
        _u("cSt", "centistokes (mm²/s)", 1e-6),
        _u("mm²/s", "milímetro cuadrado por segundo", 1e-6),
        _u("ft²/s", "pie cuadrado por segundo", _PIE ** 2),
        _u("in²/s", "pulgada cuadrada por segundo", _PULGADA ** 2),
    )),

    # ------------------------ Electricidad y magnetismo -------------------- #
    Categoria("Corriente eléctrica", "Electricidad y magnetismo", (
        _u("A", "amperio", 1.0),
        _u("mA", "miliamperio", 1e-3),
        _u("µA", "microamperio", 1e-6),
        _u("nA", "nanoamperio", 1e-9),
        _u("kA", "kiloamperio", 1000.0),
        _u("MA", "megaamperio", 1e6),
        _u("abA", "abamperio (biot)", 10.0),
        _u("statA", "statamperio", 3.335641e-10),
    )),

    Categoria("Tensión eléctrica", "Electricidad y magnetismo", (
        _u("V", "voltio", 1.0),
        _u("mV", "milivoltio", 1e-3),
        _u("µV", "microvoltio", 1e-6),
        _u("nV", "nanovoltio", 1e-9),
        _u("kV", "kilovoltio", 1000.0),
        _u("MV", "megavoltio", 1e6),
        _u("abV", "abvoltio", 1e-8),
        _u("statV", "statvoltio", 299.792458),
    )),

    Categoria("Resistencia eléctrica", "Electricidad y magnetismo", (
        _u("Ω", "ohmio", 1.0),
        _u("mΩ", "miliohmio", 1e-3),
        _u("µΩ", "microohmio", 1e-6),
        _u("kΩ", "kiloohmio", 1000.0),
        _u("MΩ", "megaohmio", 1e6),
        _u("GΩ", "gigaohmio", 1e9),
    )),

    Categoria("Conductancia eléctrica", "Electricidad y magnetismo", (
        _u("S", "siemens", 1.0),
        _u("mS", "milisiemens", 1e-3),
        _u("µS", "microsiemens", 1e-6),
        _u("nS", "nanosiemens", 1e-9),
        _u("kS", "kilosiemens", 1000.0),
        _u("mho", "mho (= siemens)", 1.0),
    )),

    Categoria("Capacitancia", "Electricidad y magnetismo", (
        _u("F", "faradio", 1.0),
        _u("mF", "milifaradio", 1e-3),
        _u("µF", "microfaradio", 1e-6),
        _u("nF", "nanofaradio", 1e-9),
        _u("pF", "picofaradio", 1e-12),
        _u("kF", "kilofaradio", 1000.0),
    )),

    Categoria("Inductancia", "Electricidad y magnetismo", (
        _u("H", "henrio", 1.0),
        _u("mH", "milihenrio", 1e-3),
        _u("µH", "microhenrio", 1e-6),
        _u("nH", "nanohenrio", 1e-9),
        _u("pH", "picohenrio", 1e-12),
        _u("kH", "kilohenrio", 1000.0),
    )),

    Categoria("Carga eléctrica", "Electricidad y magnetismo", (
        _u("C", "culombio", 1.0),
        _u("mC", "milículombio", 1e-3),
        _u("µC", "microculombio", 1e-6),
        _u("nC", "nanoculombio", 1e-9),
        _u("pC", "picoculombio", 1e-12),
        _u("kC", "kiloculombio", 1000.0),
        _u("A·h", "amperio-hora", 3600.0),
        _u("mA·h", "miliamperio-hora", 3.6),
        _u("e", "carga elemental", _EV),
        _u("F (faraday)", "faraday", 96485.33212),
    )),

    Categoria("Densidad de flujo magnético", "Electricidad y magnetismo", (
        _u("T", "tesla", 1.0),
        _u("mT", "militesla", 1e-3),
        _u("µT", "microtesla", 1e-6),
        _u("nT", "nanotesla", 1e-9),
        _u("kT", "kilotesla", 1000.0),
        _u("G", "gauss", 1e-4),
        _u("mG", "miligauss", 1e-7),
        _u("kG", "kilogauss", 0.1),
    )),

    Categoria("Flujo magnético", "Electricidad y magnetismo", (
        _u("Wb", "weber", 1.0),
        _u("mWb", "miliweber", 1e-3),
        _u("µWb", "microweber", 1e-6),
        _u("kWb", "kiloweber", 1000.0),
        _u("Mx", "maxwell", 1e-8),
    )),

    Categoria("Intensidad de campo magnético", "Electricidad y magnetismo", (
        _u("A/m", "amperio por metro", 1.0),
        _u("kA/m", "kiloamperio por metro", 1000.0),
        _u("A/cm", "amperio por centímetro", 100.0),
        _u("Oe", "oersted", 1000.0 / (4 * math.pi)),
    )),

    # ------------------------- Luz y radiación ----------------------------- #
    Categoria("Intensidad luminosa", "Luz y radiación", (
        _u("cd", "candela", 1.0),
        _u("mcd", "milicandela", 1e-3),
        _u("kcd", "kilocandela", 1000.0),
        _u("cp", "candela internacional (bujía)", 1.019),
    )),

    Categoria("Flujo luminoso", "Luz y radiación", (
        _u("lm", "lumen", 1.0),
        _u("mlm", "mililumen", 1e-3),
        _u("klm", "kilolumen", 1000.0),
    )),

    Categoria("Iluminancia", "Luz y radiación", (
        _u("lx", "lux", 1.0),
        _u("mlx", "mililux", 1e-3),
        _u("klx", "kilolux", 1000.0),
        _u("fc", "bujía-pie (foot-candle)", 1 / _PIE ** 2),
        _u("ph", "phot", 1e4),
        _u("nox", "nox", 1e-3),
    )),

    Categoria("Luminancia", "Luz y radiación", (
        _u("cd/m²", "candela por metro cuadrado (nit)", 1.0),
        _u("kcd/m²", "kilocandela por metro cuadrado", 1000.0),
        _u("cd/cm²", "candela por centímetro cuadrado (stilb)", 1e4),
        _u("sb", "stilb", 1e4),
        _u("L", "lambert", 1e4 / math.pi),
        _u("fL", "foot-lambert", 1 / (math.pi * _PIE ** 2)),
        _u("asb", "apostilb", 1 / math.pi),
    )),

    Categoria("Actividad radioactiva", "Luz y radiación", (
        _u("Bq", "becquerel", 1.0),
        _u("kBq", "kilobecquerel", 1000.0),
        _u("MBq", "megabecquerel", 1e6),
        _u("GBq", "gigabecquerel", 1e9),
        _u("TBq", "terabecquerel", 1e12),
        _u("Ci", "curio", 3.7e10),
        _u("mCi", "milicurio", 3.7e7),
        _u("µCi", "microcurio", 3.7e4),
        _u("nCi", "nanocurio", 37.0),
        _u("Rd", "rutherford", 1e6),
    )),

    Categoria("Dosis absorbida", "Luz y radiación", (
        _u("Gy", "gray", 1.0),
        _u("mGy", "miligray", 1e-3),
        _u("µGy", "microgray", 1e-6),
        _u("kGy", "kilogray", 1000.0),
        _u("rad", "rad", 0.01),
        _u("mrad", "milirad", 1e-5),
        _u("erg/g", "ergio por gramo", 1e-4),
    )),

    Categoria("Dosis equivalente", "Luz y radiación", (
        _u("Sv", "sievert", 1.0),
        _u("mSv", "milisievert", 1e-3),
        _u("µSv", "microsievert", 1e-6),
        _u("rem", "rem", 0.01),
        _u("mrem", "milirem", 1e-5),
    )),

    Categoria("Exposición a radiación", "Luz y radiación", (
        _u("C/kg", "culombio por kilogramo", 1.0),
        _u("mC/kg", "milículombio por kilogramo", 1e-3),
        _u("R", "roentgen", 2.58e-4),
        _u("mR", "miliroentgen", 2.58e-7),
    )),

    # ------------------------------- Química ------------------------------- #
    Categoria("Cantidad de sustancia", "Química", (
        _u("mol", "mol", 1.0),
        _u("kmol", "kilomol", 1000.0),
        _u("mmol", "milimol", 1e-3),
        _u("µmol", "micromol", 1e-6),
        _u("nmol", "nanomol", 1e-9),
        _u("pmol", "picomol", 1e-12),
        _u("moléculas", "moléculas (partículas)", 1 / _AVOGADRO),
    )),

    Categoria("Concentración molar", "Química", (
        _u("mol/L", "mol por litro", 1.0),
        _u("M", "molar", 1.0),
        _u("mmol/L", "milimol por litro", 1e-3),
        _u("mM", "milimolar", 1e-3),
        _u("µmol/L", "micromol por litro", 1e-6),
        _u("µM", "micromolar", 1e-6),
        _u("nmol/L", "nanomol por litro", 1e-9),
        _u("nM", "nanomolar", 1e-9),
        _u("pM", "picomolar", 1e-12),
        _u("mol/m³", "mol por metro cúbico", 1e-3),
        _u("mmol/mL", "milimol por mililitro", 1.0),
    )),

    Categoria("Concentración en masa", "Química", (
        _u("g/L", "gramo por litro", 1.0),
        _u("mg/L", "miligramo por litro", 1e-3),
        _u("µg/L", "microgramo por litro", 1e-6),
        _u("ng/L", "nanogramo por litro", 1e-9),
        _u("kg/m³", "kilogramo por metro cúbico", 1.0),
        _u("mg/mL", "miligramo por mililitro", 1.0),
        _u("g/mL", "gramo por mililitro", 1000.0),
        _u("mg/dL", "miligramo por decilitro", 0.01),
        _u("µg/mL", "microgramo por mililitro", 1e-3),
        _u("% m/v", "porcentaje masa/volumen", 10.0),
        _u("ppm", "partes por millón (en agua)", 1e-3),
        _u("ppb", "partes por mil millones (en agua)", 1e-6),
    ), nota="ppm y ppb se calculan suponiendo densidad 1 g/mL (disolución acuosa diluida)."),

    # ----------------------------- Informática ----------------------------- #
    Categoria("Almacenamiento de datos", "Informática", (
        _u("B", "byte", 1.0),
        _u("bit", "bit", 0.125),
        _u("nibble", "nibble (4 bits)", 0.5),
        _u("kB", "kilobyte (10³)", 1e3),
        _u("MB", "megabyte (10⁶)", 1e6),
        _u("GB", "gigabyte (10⁹)", 1e9),
        _u("TB", "terabyte (10¹²)", 1e12),
        _u("PB", "petabyte (10¹⁵)", 1e15),
        _u("EB", "exabyte (10¹⁸)", 1e18),
        _u("KiB", "kibibyte (2¹⁰)", 1024.0),
        _u("MiB", "mebibyte (2²⁰)", 1024.0 ** 2),
        _u("GiB", "gibibyte (2³⁰)", 1024.0 ** 3),
        _u("TiB", "tebibyte (2⁴⁰)", 1024.0 ** 4),
        _u("PiB", "pebibyte (2⁵⁰)", 1024.0 ** 5),
        _u("kbit", "kilobit", 125.0),
        _u("Mbit", "megabit", 125000.0),
        _u("Gbit", "gigabit", 1.25e8),
        _u("Tbit", "terabit", 1.25e11),
        _u("Kibit", "kibibit", 128.0),
        _u("Mibit", "mebibit", 131072.0),
        _u("Gibit", "gibibit", 134217728.0),
    ), nota="Los prefijos kB/MB/GB son potencias de 10; KiB/MiB/GiB son potencias de 2."),

    Categoria("Velocidad de transferencia", "Informática", (
        _u("bit/s", "bit por segundo", 1.0),
        _u("kbit/s", "kilobit por segundo", 1e3),
        _u("Mbit/s", "megabit por segundo", 1e6),
        _u("Gbit/s", "gigabit por segundo", 1e9),
        _u("Tbit/s", "terabit por segundo", 1e12),
        _u("B/s", "byte por segundo", 8.0),
        _u("kB/s", "kilobyte por segundo", 8e3),
        _u("MB/s", "megabyte por segundo", 8e6),
        _u("GB/s", "gigabyte por segundo", 8e9),
        _u("KiB/s", "kibibyte por segundo", 8 * 1024.0),
        _u("MiB/s", "mebibyte por segundo", 8 * 1024.0 ** 2),
        _u("GiB/s", "gibibyte por segundo", 8 * 1024.0 ** 3),
    )),

    # ----------------------------- Cotidianas ------------------------------ #
    Categoria("Consumo de combustible", "Cotidianas", (
        _u("L/100km", "litros por 100 kilómetros", 1.0),
        _u("L/km", "litros por kilómetro", 100.0),
        _u("km/L", "kilómetros por litro", 100.0, inversa=True),
        _u("mi/gal US", "millas por galón (EE. UU.)", _GALON_US * 1e8 / _MILLA, inversa=True),
        _u("mi/gal UK", "millas por galón (imperial)", _GALON_UK * 1e8 / _MILLA, inversa=True),
        _u("km/gal US", "kilómetros por galón (EE. UU.)", _GALON_US * 1e5, inversa=True),
        _u("mi/L", "millas por litro", 1e5 / _MILLA, inversa=True),
    ), nota="Relación inversa: a más L/100 km, menos km/L. El valor 0 no es convertible."),

    Categoria("Medidas de cocina", "Cotidianas", (
        _u("mL", "mililitro", 1.0),
        _u("L", "litro", 1000.0),
        _u("cucharadita", "cucharadita EE. UU. (tsp)", _GALON_US * 1e6 / 768),
        _u("cucharada", "cucharada EE. UU. (tbsp)", _GALON_US * 1e6 / 256),
        _u("cucharadita métrica", "cucharadita métrica", 5.0),
        _u("cucharada métrica", "cucharada métrica", 15.0),
        _u("taza US", "taza estadounidense", _GALON_US * 1e6 / 16),
        _u("taza métrica", "taza métrica", 250.0),
        _u("fl oz US", "onza líquida estadounidense", _GALON_US * 1e6 / 128),
        _u("pinta US", "pinta estadounidense", _GALON_US * 1e6 / 8),
        _u("cuarto US", "cuarto estadounidense", _GALON_US * 1e6 / 4),
        _u("galón US", "galón estadounidense", _GALON_US * 1e6),
        _u("pizca", "pizca (1/16 de cucharadita)", _GALON_US * 1e6 / 768 / 16),
        _u("gota", "gota métrica", 0.05),
    )),

    Categoria("Tipografía", "Cotidianas", (
        _u("mm", "milímetro", 1.0),
        _u("cm", "centímetro", 10.0),
        _u("in", "pulgada", 25.4),
        _u("pt", "punto PostScript/DTP (1/72 in)", 25.4 / 72),
        _u("pica", "pica (12 pt)", 25.4 / 6),
        _u("pt Didot", "punto Didot", 0.3759715),
        _u("cícero", "cícero (12 pt Didot)", 4.511658),
        _u("twip", "twip (1/1440 in)", 25.4 / 1440),
        _u("px", "píxel a 96 ppp", 25.4 / 96),
        _u("px@72", "píxel a 72 ppp", 25.4 / 72),
    )),

    Categoria("Proporción", "Cotidianas", (
        _u("fracción", "fracción decimal (1 = todo)", 1.0),
        _u("%", "porcentaje", 0.01),
        _u("‰", "por mil", 1e-3),
        _u("‱", "punto básico (por diez mil)", 1e-4),
        _u("ppm", "partes por millón", 1e-6),
        _u("ppb", "partes por mil millones", 1e-9),
        _u("ppt", "partes por billón", 1e-12),
    )),

    Categoria("Cantidades y prefijos", "Cotidianas", (
        _u("unidad", "unidad", 1.0),
        _u("decena", "decena", 10.0),
        _u("docena", "docena", 12.0),
        _u("centena", "centena", 100.0),
        _u("gruesa", "gruesa (12 docenas)", 144.0),
        _u("millar", "millar", 1000.0),
        _u("millón", "millón", 1e6),
        _u("millardo", "millardo (mil millones)", 1e9),
        _u("billón", "billón (10¹², escala larga)", 1e12),
        _u("k", "kilo (10³)", 1e3),
        _u("M", "mega (10⁶)", 1e6),
        _u("G", "giga (10⁹)", 1e9),
        _u("T", "tera (10¹²)", 1e12),
        _u("P", "peta (10¹⁵)", 1e15),
        _u("E", "exa (10¹⁸)", 1e18),
        _u("m", "mili (10⁻³)", 1e-3),
        _u("µ", "micro (10⁻⁶)", 1e-6),
        _u("n", "nano (10⁻⁹)", 1e-9),
        _u("p", "pico (10⁻¹²)", 1e-12),
        _u("f", "femto (10⁻¹⁵)", 1e-15),
        _u("a", "atto (10⁻¹⁸)", 1e-18),
    )),
]

#: Categorías indexadas por nombre, en el orden en que se muestran.
CATEGORIAS: dict[str, Categoria] = {c.nombre: c for c in _CATALOGO}

#: Grupos temáticos -> nombres de categoría, para la navegación de la interfaz.
GRUPOS: dict[str, list[str]] = {}
for _c in _CATALOGO:
    GRUPOS.setdefault(_c.grupo, []).append(_c.nombre)


# --------------------------------------------------------------------------- #
# API pública
# --------------------------------------------------------------------------- #


def categoria(nombre: str) -> Categoria:
    try:
        return CATEGORIAS[nombre]
    except KeyError:
        raise ErrorConversion(f"Categoría desconocida: {nombre!r}") from None


def convertir(valor: float, origen: str, destino: str, nombre_categoria: str) -> float:
    """Convierte ``valor`` de la unidad ``origen`` a ``destino``.

    >>> round(convertir(1, "km", "m", "Longitud"))
    1000
    >>> round(convertir(100, "°C", "°F", "Temperatura"), 4)
    212.0
    """
    cat = categoria(nombre_categoria)
    u_origen = cat.unidad(origen)
    u_destino = cat.unidad(destino)

    if u_origen is u_destino:
        return float(valor)

    try:
        return u_destino.desde_base(u_origen.a_base(float(valor)))
    except ZeroDivisionError:
        raise ErrorConversion("La conversión no está definida para ese valor") from None
    except OverflowError:
        raise ErrorConversion("El resultado es demasiado grande") from None


def tabla_completa(valor: float, origen: str, nombre_categoria: str) -> list[tuple[Unidad, float]]:
    """Convierte ``valor`` a todas las unidades de la categoría de una vez."""
    cat = categoria(nombre_categoria)
    u_origen = cat.unidad(origen)
    base = u_origen.a_base(float(valor))

    resultados: list[tuple[Unidad, float]] = []
    for unidad in cat.unidades:
        try:
            resultados.append((unidad, unidad.desde_base(base)))
        except (ErrorConversion, ZeroDivisionError, OverflowError):
            continue
    return resultados


def buscar(texto: str) -> list[tuple[str, Unidad]]:
    """Busca unidades por símbolo o nombre, ignorando mayúsculas y acentos.

    Devuelve pares (categoría, unidad); las coincidencias exactas de símbolo van
    primero, porque suelen ser lo que se busca.
    """
    consulta = normalizar(texto.strip())
    if not consulta:
        return []

    exactas: list[tuple[str, Unidad]] = []
    parciales: list[tuple[str, Unidad]] = []
    for cat in _CATALOGO:
        for unidad in cat.unidades:
            simbolo = normalizar(unidad.simbolo)
            nombre = normalizar(unidad.nombre)
            if simbolo == consulta:
                exactas.append((cat.nombre, unidad))
            elif consulta in simbolo or consulta in nombre:
                parciales.append((cat.nombre, unidad))
    return exactas + parciales


def resumen() -> str:
    """Texto informativo con el tamaño del catálogo."""
    total = sum(len(c.unidades) for c in _CATALOGO)
    return f"{len(_CATALOGO)} categorías y {total} unidades"
