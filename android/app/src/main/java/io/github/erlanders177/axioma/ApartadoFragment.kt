package io.github.erlanders177.axioma

import android.content.Context
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment

/**
 * Base de los siete apartados.
 *
 * Cada uno se monta sobre una columna con desplazamiento y añade lo suyo. Aquí
 * queda lo que comparten: el historial propio, guardar un resultado como
 * variable, y esperar al motor sin bloquear la pantalla.
 */
abstract class ApartadoFragment : Fragment() {

    /** Clave del apartado. Es la que separa un historial de otro. */
    abstract val clave: String

    protected lateinit var contenido: LinearLayout
    private lateinit var listaHistorial: LinearLayout

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        val contexto = requireContext()
        val desplazable = ScrollView(contexto)
        contenido = LinearLayout(contexto)
        contenido.orientation = LinearLayout.VERTICAL
        val relleno = Piezas.puntos(contexto, 16)
        contenido.setPadding(relleno, relleno, relleno, relleno)
        desplazable.addView(contenido)

        construir(contenido)
        montarHistorial(contexto)
        return desplazable
    }

    /** Lo que pone cada apartado en su columna. */
    abstract fun construir(raiz: LinearLayout)

    /** Se llama en cuanto el motor está listo, para lo que dependa de Python. */
    protected fun cuandoListo(tarea: () -> Unit) {
        Nucleo.cuandoListo { if (isAdded) tarea() }
    }

    // ------------------------------------------------------------ historial -- //

    private fun montarHistorial(contexto: Context) {
        contenido.addView(Piezas.titulo(contexto, "Historial"))
        listaHistorial = LinearLayout(contexto)
        listaHistorial.orientation = LinearLayout.VERTICAL
        contenido.addView(listaHistorial)
        pintarHistorial()
    }

    /** Guarda una operación en el historial de **este** apartado. */
    protected fun anotar(texto: String) {
        val memoria = requireContext()
            .getSharedPreferences("axioma-historial", Context.MODE_PRIVATE)
        val guardado = memoria.getString(clave, "").orEmpty()
        val entradas = (listOf(texto) + guardado.split("\n").filter { it.isNotBlank() })
            .take(50)
        memoria.edit().putString(clave, entradas.joinToString("\n")).apply()
        pintarHistorial()
    }

    private fun pintarHistorial() {
        val contexto = requireContext()
        listaHistorial.removeAllViews()
        val memoria = contexto.getSharedPreferences("axioma-historial", Context.MODE_PRIVATE)
        val entradas = memoria.getString(clave, "").orEmpty()
            .split("\n").filter { it.isNotBlank() }
        if (entradas.isEmpty()) {
            listaHistorial.addView(Piezas.aviso(contexto, "Todavía no hay nada guardado."))
            return
        }
        for (entrada in entradas.take(12)) {
            val linea = TextView(contexto)
            linea.text = entrada
            linea.setTextColor(contexto.getColor(R.color.suave))
            linea.textSize = 13f
            val vertical = Piezas.puntos(contexto, 7)
            linea.setPadding(0, vertical, 0, vertical)
            listaHistorial.addView(linea)
        }
    }

    // ------------------------------------------------------------ variables -- //

    /**
     * Ofrece guardar un resultado como variable compartida.
     *
     * Es lo que permite calcular el volumen de una figura y usarlo dentro de
     * una ecuación sin copiar el número a mano, con todos sus decimales.
     */
    protected fun guardarComoVariable(etiqueta: String, valor: Double) {
        val contexto = requireContext()
        val campo = EditText(contexto)
        campo.setText(nombreSugerido(etiqueta))
        campo.setSingleLine()

        AlertDialog.Builder(contexto)
            .setTitle("Usar en otros apartados")
            .setMessage("Guardar $valor como variable. Podrá escribir ese nombre " +
                        "en cualquier apartado.")
            .setView(campo)
            .setNegativeButton("Cancelar", null)
            .setPositiveButton("Guardar") { _, _ ->
                val nombre = campo.text.toString().trim()
                if (nombre.isEmpty()) return@setPositiveButton
                val respuesta = Nucleo.llamar("definir_variable", nombre, valor)
                if (!respuesta.optBoolean("ok")) {
                    AlertDialog.Builder(contexto)
                        .setMessage(Nucleo.error(respuesta))
                        .setPositiveButton("Vale", null)
                        .show()
                }
            }
            .show()
    }

    private fun nombreSugerido(etiqueta: String): String {
        val sinTildes = java.text.Normalizer
            .normalize(etiqueta, java.text.Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}"), "")
        val limpio = sinTildes.replace(Regex("[^0-9A-Za-z]+"), "_")
            .trim('_').lowercase()
        return if (limpio.isEmpty() || limpio.first().isDigit()) "resultado" else limpio
    }
}
