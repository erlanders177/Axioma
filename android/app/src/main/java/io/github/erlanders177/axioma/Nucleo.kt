package io.github.erlanders177.axioma

import android.content.Context
import android.os.Handler
import android.os.Looper
import com.chaquo.python.Python
import com.chaquo.python.android.AndroidPlatform
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.Executors

/**
 * El motor de cálculo de Axioma, que es Python.
 *
 * Dentro de la aplicación corre el mismo `src/core` que la versión de
 * escritorio y la del navegador. No se reescribe la matemática en Kotlin:
 * tres implementaciones distintas acabarían dando tres resultados distintos, y
 * el que fallara sería siempre el que no se está mirando.
 *
 * Todo lo que devuelve el puente es JSON con la misma forma en los tres sitios:
 * `{ok: true, datos: …}` o `{ok: false, error: "…"}`.
 */
object Nucleo {

    @Volatile
    var listo = false
        private set

    private val pendientes = mutableListOf<() -> Unit>()
    private val principal = Handler(Looper.getMainLooper())
    private val hilo = Executors.newSingleThreadExecutor()

    /**
     * Arranca el intérprete sin bloquear la pantalla.
     *
     * Tarda un segundo largo la primera vez. Hacerlo en el hilo de la interfaz
     * dejaría la aplicación congelada justo al abrirla, que es la peor primera
     * impresión posible.
     */
    fun arrancar(contexto: Context) {
        if (listo) return
        val aplicacion = contexto.applicationContext
        hilo.execute {
            if (!Python.isStarted()) Python.start(AndroidPlatform(aplicacion))
            // Se toca el puente aquí, en segundo plano: importar el núcleo
            // construye las tablas de unidades y figuras, y eso también cuesta.
            Python.getInstance().getModule("puente")
            principal.post {
                listo = true
                val tareas = pendientes.toList()
                pendientes.clear()
                tareas.forEach { it() }
            }
        }
    }

    /** Para las pruebas y para arrancar a la fuerza en un hilo cualquiera. */
    fun iniciar(contexto: Context) {
        if (!Python.isStarted()) Python.start(AndroidPlatform(contexto.applicationContext))
        listo = true
    }

    /** Ejecuta algo en cuanto el motor esté listo. Si ya lo está, ahora mismo. */
    fun cuandoListo(tarea: () -> Unit) {
        if (listo) tarea() else pendientes.add(tarea)
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

    /**
     * Como `llamar`, pero fuera del hilo de la interfaz.
     *
     * Resolver una ecuación con sympy puede tardar segundos, y ese rato la
     * pantalla no puede quedarse muda.
     */
    fun llamarAparte(funcion: String, vararg argumentos: Any?, alTerminar: (JSONObject) -> Unit) {
        hilo.execute {
            val respuesta = llamar(funcion, *argumentos)
            principal.post { alTerminar(respuesta) }
        }
    }

    /** Los datos de una respuesta correcta, o `null` si vino con error. */
    fun datos(respuesta: JSONObject): JSONObject? =
        if (respuesta.optBoolean("ok")) respuesta.optJSONObject("datos") else null

    /** Igual, cuando lo que devuelve el puente es una lista. */
    fun lista(respuesta: JSONObject): JSONArray? =
        if (respuesta.optBoolean("ok")) respuesta.optJSONArray("datos") else null

    /** El mensaje de error, listo para enseñar. */
    fun error(respuesta: JSONObject): String =
        respuesta.optString("error", "No se pudo calcular")
}
