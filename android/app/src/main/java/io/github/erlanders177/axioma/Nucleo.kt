package io.github.erlanders177.axioma

import android.content.Context
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONObject

/**
 * El motor de cálculo de Axioma, que es Python.
 *
 * Dentro de la aplicación corre el mismo `src/core` que la versión de
 * escritorio y la del navegador. No se reescribe la matemática en Kotlin:
 * tres implementaciones distintas acabarían dando tres resultados distintos, y
 * el que fallara sería siempre el que no se está mirando.
 *
 * Todo lo que devuelve el puente es JSON, con la misma forma en los tres
 * sitios: `{ok: true, datos: …}` o `{ok: false, error: "…"}`.
 */
object Nucleo {

    /** Arranca el intérprete. Es idempotente: se puede llamar sin miedo. */
    fun iniciar(contexto: Context) {
        if (!Python.isStarted()) {
            Python.start(AndroidPlatform(contexto.applicationContext))
        }
    }

    /** Llama a una función del puente y devuelve su respuesta ya interpretada. */
    fun llamar(funcion: String, vararg argumentos: Any?): JSONObject {
        return try {
            val puente = Python.getInstance().getModule("puente")
            JSONObject(puente.callAttr(funcion, *argumentos).toString())
        } catch (e: Exception) {
            // Un fallo del intérprete no puede tumbar la aplicación: se
            // devuelve con la misma forma que un error del propio núcleo.
            JSONObject().put("ok", false).put("error", e.message ?: e.toString())
        }
    }

    /** Los datos de una respuesta correcta, o `null` si vino con error. */
    fun datos(respuesta: JSONObject): JSONObject? =
        if (respuesta.optBoolean("ok")) respuesta.optJSONObject("datos") else null

    /** El mensaje de error, listo para enseñar. */
    fun error(respuesta: JSONObject): String =
        respuesta.optString("error", "No se pudo calcular")
}
