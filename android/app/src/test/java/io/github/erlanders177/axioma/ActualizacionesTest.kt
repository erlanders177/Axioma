package io.github.erlanders177.axioma

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/**
 * La comparación de versiones, que decide si alguien recibe el aviso.
 *
 * Comparar como texto diría que «5.10» es anterior a «5.9», y a partir de la
 * décima corrección la gente dejaría de enterarse de que hay algo nuevo.
 */
class ActualizacionesTest {

    @Test
    fun reconoceUnaVersionPosterior() {
        assertTrue(Actualizaciones.esPosterior("5.1.0", "5.0.0"))
        assertTrue(Actualizaciones.esPosterior("6.0.0", "5.9.9"))
        assertTrue(Actualizaciones.esPosterior("5.0.1", "5.0.0"))
    }

    @Test
    fun dosCifrasNoSonMenoresQueUna() {
        assertTrue(Actualizaciones.esPosterior("5.10.0", "5.9.0"))
        assertTrue(Actualizaciones.esPosterior("5.0.10", "5.0.9"))
    }

    @Test
    fun noAvisaSiEsLaMismaOAnterior() {
        assertFalse(Actualizaciones.esPosterior("5.0.0", "5.0.0"))
        assertFalse(Actualizaciones.esPosterior("4.9.0", "5.0.0"))
        assertFalse(Actualizaciones.esPosterior("5.0", "5.0.1"))
    }

    @Test
    fun aguantaVersionesRaras() {
        assertFalse(Actualizaciones.esPosterior("", "5.0.0"))
        assertTrue(Actualizaciones.esPosterior("5.1", "5.0.9"))
    }
}
