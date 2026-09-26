package io.github.erlanders177.axioma

import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.click
import androidx.test.espresso.action.ViewActions.scrollTo
import androidx.test.espresso.assertion.ViewAssertions.matches
import androidx.test.espresso.matcher.ViewMatchers.withContentDescription
import androidx.test.espresso.matcher.ViewMatchers.withTagValue
import androidx.test.espresso.matcher.ViewMatchers.withText
import androidx.test.ext.junit.rules.ActivityScenarioRule
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.hamcrest.Matchers.equalTo
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class InterfazTest {

    @get:Rule
    val actividad = ActivityScenarioRule(MainActivity::class.java)

    private fun esperarAlMotor() {
        val limite = System.currentTimeMillis() + 60_000
        while (!Nucleo.listo && System.currentTimeMillis() < limite) Thread.sleep(200)
        Thread.sleep(500)
    }

    private fun pulsar(texto: String) {
        // scrollTo antes de cada pulsación: Espresso se niega a tocar una
        // tecla que no esté del todo a la vista, y el teclado queda abajo.
        onView(withText(texto)).perform(scrollTo(), click())
    }

    private fun pulsarPorNombre(nombre: String) {
        onView(withContentDescription(nombre)).perform(scrollTo(), click())
    }

    private fun resultadoEs(texto: String) {
        onView(withTagValue(equalTo("resultado" as Any)))
            .check(matches(withContentDescription(texto)))
    }

    @Test
    fun elTecladoDeLaAplicacionCalcula() {
        esperarAlMotor()
        pulsar("C")
        pulsar("7")
        pulsar("+")
        pulsar("8")
        pulsar("=")
        Thread.sleep(500)
        resultadoEs("15")
    }

    @Test
    fun laTeclaDeFraccionTieneDosHuecos() {
        esperarAlMotor()
        pulsar("C")
        pulsarPorNombre("Fracción")
        pulsar("1")
        pulsarPorNombre("Mover a la derecha")      // del numerador al denominador
        pulsar("2")
        pulsarPorNombre("Mover a la derecha")      // fuera de la fracción
        pulsar("+")
        pulsarPorNombre("Fracción")
        pulsar("1")
        pulsarPorNombre("Mover a la derecha")
        pulsar("3")
        pulsar("=")
        Thread.sleep(500)
        resultadoEs("5/6")
        pulsar("S⇔D")
        resultadoEs("0.833333")
    }

    @Test
    fun elResultadoSaleExacto() {
        esperarAlMotor()
        pulsar("C")
        pulsar("√")
        pulsar("8")
        pulsar(")")
        pulsar("=")
        Thread.sleep(500)
        resultadoEs("2√2")
    }
}
