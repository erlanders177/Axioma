package io.github.erlanders177.axioma

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.BeforeClass
import org.junit.Test
import org.junit.runner.RunWith

/**
 * Que el núcleo dé en Android lo mismo que en Windows y en el navegador.
 *
 * Se ejecuta en un móvil o en un emulador de verdad, porque es la única forma
 * de comprobar que el intérprete empotrado arranca y que sympy está donde tiene
 * que estar.
 */
@RunWith(AndroidJUnit4::class)
class NucleoTest {

    companion object {
        @BeforeClass
        @JvmStatic
        fun arrancarPython() {
            Nucleo.iniciar(InstrumentationRegistry.getInstrumentation().targetContext)
        }
    }

    private fun datos(respuesta: JSONObject): JSONObject {
        assertTrue("respuesta con error: ${Nucleo.error(respuesta)}",
                   respuesta.optBoolean("ok"))
        return respuesta.getJSONObject("datos")
    }

    @Test
    fun calculaComoLasDemasVersiones() {
        val r = datos(Nucleo.llamar("calcular", "2*sin(30)+sqrt(16)", "DEG", 6))
        assertEquals("5", r.getString("texto"))
    }

    @Test
    fun operaConUnidades() {
        val r = datos(Nucleo.llamar("calcular", "3 km + 200 m", "DEG", 6))
        assertEquals("3.2 km", r.getString("texto"))
    }

    @Test
    fun laGeometriaMezclaUnidades() {
        val valores = """{"r": "5 cm", "h": "50 mm"}"""
        val r = datos(Nucleo.llamar("calcular_figura", "Cilindro", valores, 6))
        val primero = r.getJSONArray("resultados").getJSONObject(0)
        assertEquals("Volumen", primero.getString("etiqueta"))
        assertEquals("392.699 cm³", primero.getString("texto"))
    }

    @Test
    fun resuelveEcuacionesConSympy() {
        val r = datos(Nucleo.llamar("resolver_ecuacion", "x^2 - 5x + 6 = 0", 6))
        assertEquals("x", r.getString("incognita"))
        val soluciones = r.getJSONArray("soluciones")
        assertEquals(2, soluciones.length())
        assertEquals("2", soluciones.getJSONObject(0).getString("exacto"))
        assertEquals("3", soluciones.getJSONObject(1).getString("exacto"))
    }

    @Test
    fun laCalculadoraDaFraccionesYLaTeclaSD() {
        Nucleo.llamar("teclear", "limpiar", "", "DEG", 6)
        datos(Nucleo.llamar("teclear", "escribir", "1/2+1/3", "DEG", 6))
        val r = datos(Nucleo.llamar("teclear", "calcular", "", "DEG", 6))
        assertEquals("5/6", r.getJSONObject("resultado").getString("texto"))
        val d = datos(Nucleo.llamar("teclear", "sd", "", "DEG", 6))
        assertEquals("0.833333", d.getJSONObject("resultado").getString("texto"))
    }

    @Test
    fun elPasoAPasoFuncionaDentroDelMovil() {
        val cuenta = Nucleo.llamar("pasos_de_cuenta", "sqrt(72)", "DEG", "{}", 6)
        assertTrue(cuenta.toString(), cuenta.toString().contains("6√2"))
        val figura = Nucleo.llamar("pasos_figura", "Cilindro",
                                   """{"r": "5 cm", "h": "10 cm"}""", 6)
        assertTrue(figura.toString(), figura.toString().contains("250π"))
        val ecuacion = Nucleo.llamar("pasos_ecuacion", "x^2 - 5x + 6 = 0")
        assertTrue(ecuacion.toString(), ecuacion.optBoolean("ok"))
    }

    @Test
    fun hay61FigurasY555Unidades() {
        val figuras = Nucleo.llamar("lista_figuras").getJSONArray("datos")
        assertEquals(61, figuras.length())

        val categorias = Nucleo.llamar("categorias").getJSONArray("datos")
        assertTrue("deberían ser varios grupos de magnitudes", categorias.length() > 3)
    }
}
