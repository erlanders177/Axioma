package io.github.erlanders177.axioma

import android.content.Context
import android.graphics.Typeface
import android.view.View
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import org.json.JSONArray

/**
 * El botón «Paso a paso» de un apartado y la caja donde se ve el desarrollo.
 *
 * Se queda encendido o apagado como se dejó, también al volver a abrir la
 * aplicación. Encendido, cada cálculo nuevo trae su desarrollo sin tener que
 * volver a pedirlo.
 *
 * El desarrollo lo hace el núcleo (con sympy) en el hilo de fondo: la primera
 * vez tarda unos segundos en cargarse, y la pantalla no puede quedarse muda.
 */
class PasoAPaso(private val contexto: Context, private val clave: String) {

    private val preferencias =
        contexto.getSharedPreferences("axioma-pasos", Context.MODE_PRIVATE)

    var activo: Boolean = preferencias.getBoolean(clave, false)
        private set

    val boton: Button = Piezas.boton(contexto, "Paso a paso") { alternar() }
    val caja: LinearLayout = LinearLayout(contexto)

    /** La última petición: la de volver a pedir, y la que manda si llegan dos. */
    private var ultima: Pair<String, Array<out Any?>>? = null
    private var turno = 0

    init {
        boton.tag = "paso-a-paso-$clave"
        caja.orientation = LinearLayout.VERTICAL
        caja.setBackgroundResource(R.drawable.fondo_panel)
        val relleno = Piezas.puntos(contexto, 12)
        caja.setPadding(relleno, relleno, relleno, relleno)
        val parametros = LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT)
        parametros.topMargin = Piezas.puntos(contexto, 10)
        caja.layoutParams = parametros
        caja.tag = "pasos-$clave"
        caja.visibility = View.GONE
        pintarBoton()
    }

    private fun pintarBoton() {
        boton.alpha = if (activo) 1f else 0.7f
        boton.text = if (activo) "Paso a paso ✓" else "Paso a paso"
    }

    private fun alternar() {
        activo = !activo
        preferencias.edit().putBoolean(clave, activo).apply()
        pintarBoton()
        val pendiente = ultima
        if (activo && pendiente != null) {
            pedir(pendiente.first, *pendiente.second)
        } else if (!activo) {
            turno++
            caja.visibility = View.GONE
        } else {
            caja.visibility = View.VISIBLE
            caja.removeAllViews()
            caja.addView(Piezas.aviso(contexto, "Calcule algo y aquí saldrá cómo se resuelve."))
        }
    }

    /** Pide al núcleo el desarrollo con `funcion(argumentos…)`, si está encendido. */
    fun pedir(funcion: String, vararg argumentos: Any?) {
        ultima = funcion to argumentos
        if (!activo) return
        val mio = ++turno
        caja.visibility = View.VISIBLE
        caja.removeAllViews()
        caja.addView(Piezas.aviso(contexto, "Preparando el desarrollo…"))
        Nucleo.llamarAparte(funcion, *argumentos) { respuesta ->
            if (mio != turno || !activo) return@llamarAparte
            val pasos = Nucleo.lista(respuesta)
            if (pasos == null) {
                mostrarError(Nucleo.error(respuesta))
            } else {
                pintar(pasos)
            }
        }
    }

    /** Pinta una lista que ya se tiene (la calculadora, a veces, la trae hecha). */
    fun pintar(pasos: JSONArray) {
        caja.visibility = View.VISIBLE
        caja.removeAllViews()
        if (pasos.length() == 0) {
            caja.addView(Piezas.aviso(contexto, "Aquí no hay pasos que enseñar."))
            return
        }
        var numero = 0
        for (i in 0 until pasos.length()) {
            val paso = pasos.getJSONObject(i)
            val nivel = paso.optInt("nivel")
            val bloque = LinearLayout(contexto)
            bloque.orientation = LinearLayout.VERTICAL
            val parametros = LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT)
            parametros.topMargin = Piezas.puntos(contexto, if (i == 0) 0 else 8)
            parametros.leftMargin = Piezas.puntos(contexto, 14 * nivel)
            bloque.layoutParams = parametros

            val titulo = TextView(contexto)
            titulo.text = if (nivel == 0) "${++numero}. ${paso.optString("titulo")}"
                          else "· ${paso.optString("titulo")}"
            titulo.setTextColor(contexto.getColor(R.color.texto))
            titulo.setTypeface(null, Typeface.BOLD)
            titulo.textSize = 14f
            bloque.addView(titulo)

            val detalle = paso.optString("detalle")
            if (detalle.isNotEmpty()) {
                val vista = TextView(contexto)
                vista.text = detalle
                vista.setTextColor(contexto.getColor(R.color.suave))
                vista.textSize = 13f
                bloque.addView(vista)
            }
            val expresion = paso.optString("expresion")
            if (expresion.isNotEmpty()) {
                val vista = TextView(contexto)
                vista.text = expresion
                vista.setTextColor(contexto.getColor(R.color.acento))
                vista.typeface = Typeface.MONOSPACE
                vista.textSize = 14f
                vista.setTextIsSelectable(true)
                bloque.addView(vista)
            }
            caja.addView(bloque)
        }
    }

    private fun mostrarError(mensaje: String) {
        caja.visibility = View.VISIBLE
        caja.removeAllViews()
        caja.addView(Piezas.aviso(contexto, mensaje, esError = true))
    }

    companion object {
        /** ¿Hay algún apartado con el paso a paso encendido? Para prepararlo antes. */
        fun algunoEncendido(contexto: Context): Boolean =
            contexto.getSharedPreferences("axioma-pasos", Context.MODE_PRIVATE)
                .all.values.any { it == true }
    }
}
