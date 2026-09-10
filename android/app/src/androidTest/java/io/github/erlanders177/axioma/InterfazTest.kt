package io.github.erlanders177.axioma

import androidx.test.espresso.Espresso.onView
import androidx.test.espresso.action.ViewActions.click
import androidx.test.espresso.assertion.ViewAssertions.matches
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

    @Test
    fun elTecladoDeLaAplicacionCalcula() {
        esperarAlMotor()
        onView(withText("7")).perform(click())
        onView(withText("+")).perform(click())
        onView(withText("8")).perform(click())
        onView(withText("=")).perform(click())
        Thread.sleep(1500)
        onView(withTagValue(equalTo("pantalla" as Any)))
            .check(matches(withText("15")))
    }
}
