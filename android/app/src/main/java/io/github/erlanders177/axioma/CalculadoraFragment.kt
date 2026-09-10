package io.github.erlanders177.axioma

import android.graphics.Typeface
import android.view.Gravity
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.EditText
import android.widget.GridLayout
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog

/**
 * La calculadora científica, con su propio teclado.
 *
 * Aquí el teclado es de la aplicación, con `sin`, `cos`, `√` y `π`. El del
 * sistema no aparece nunca solo: sale a petición, con el botón de escribir,
 * para los nombres de variable y poco más.
 */
class CalculadoraFragment : ApartadoFragment() {

    override val clave = "calculadora"

    private lateinit var pantalla: TextView
    private lateinit var previa: TextView
    private var expresion = ""
    private var modoAngulo = "DEG"

    /** (rótulo, qué inserta). Lo que empieza por `#` es una orden. */
    private val teclas = listOf(
        "sin" to "sin(", "cos" to "cos(", "tan" to "tan(", "√" to "sqrt(", "C" to "#limpiar",
        "ln" to "ln(", "log" to "log10(", "(" to "(", ")" to ")", "⌫" to "#borrar",
        "7" to "7", "8" to "8", "9" to "9", "÷" to "/", "^" to "^",
        "4" to "4", "5" to "5", "6" to "6", "×" to "*", "π" to "pi",
        "1" to "1", "2" to "2", "3" to "3", "−" to "-", "!" to "!",
        "0" to "0", "." to ".", "ans" to "ans", "+" to "+", "=" to "#calcular",
    )

    override fun construir(raiz: LinearLayout) {
        val contexto = requireContext()

        // -- pantalla ------------------------------------------------------- //
        val marco = LinearLayout(contexto)
        marco.orientation = LinearLayout.VERTICAL
        marco.setBackgroundResource(R.drawable.fondo_panel)
        val relleno = Piezas.puntos(contexto, 14)
        marco.setPadding(relleno, relleno, relleno, relleno)

        pantalla = TextView(contexto)
        pantalla.text = "0"
        pantalla.textSize = 32f
        pantalla.gravity = Gravity.END
        pantalla.setTextColor(contexto.getColor(R.color.texto))
        pantalla.setTextIsSelectable(true)
        pantalla.tag = "pantalla"          // por dónde la agarra la prueba

        previa = TextView(contexto)
        previa.textSize = 15f
        previa.gravity = Gravity.END
        previa.setTextColor(contexto.getColor(R.color.suave))

        marco.addView(pantalla)
        marco.addView(previa)
        raiz.addView(marco)

        // -- modo de ángulo y escritura libre -------------------------------- //
        val fila = LinearLayout(contexto)
        fila.orientation = LinearLayout.HORIZONTAL

        val modo = Piezas.desplegable(
            contexto, listOf("DEG — grados", "RAD — radianes", "GRAD — gradianes"))
        modo.layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
        modo.onItemSelectedListener = Piezas.alElegir { posicion ->
            modoAngulo = listOf("DEG", "RAD", "GRAD")[posicion]
            actualizarPrevia()
        }
        fila.addView(modo)

        val escribir = Piezas.boton(contexto, "⌨") { escribirAMano() }
        escribir.layoutParams = LinearLayout.LayoutParams(
            Piezas.puntos(contexto, 56), WRAP_CONTENT
        ).also { it.leftMargin = Piezas.puntos(contexto, 8) }
        fila.addView(escribir)
        raiz.addView(fila)

        // -- teclado --------------------------------------------------------- //
        val teclado = GridLayout(contexto)
        teclado.columnCount = 5
        teclado.useDefaultMargins = true
        for ((rotulo, orden) in teclas) {
            teclado.addView(tecla(rotulo, orden))
        }
        raiz.addView(teclado)
    }

    private fun tecla(rotulo: String, orden: String): TextView {
        val contexto = requireContext()
        val vista = TextView(contexto)
        vista.text = rotulo
        vista.gravity = Gravity.CENTER
        vista.textSize = if (rotulo.length > 2) 14f else 18f
        vista.setTextColor(
            contexto.getColor(
                when {
                    orden == "#calcular" -> android.R.color.white
                    rotulo in listOf("÷", "×", "−", "+", "^", "(", ")", "C", "⌫") -> R.color.acento
                    rotulo.first().isDigit() || rotulo == "." -> R.color.texto
                    else -> R.color.suave
                }
            )
        )
        vista.setBackgroundResource(
            if (orden == "#calcular") R.drawable.fondo_tecla_igual else R.drawable.fondo_tecla
        )
        if (orden == "#calcular") vista.setTypeface(null, Typeface.BOLD)

        val parametros = GridLayout.LayoutParams()
        parametros.width = 0
        parametros.height = Piezas.puntos(contexto, 52)
        parametros.columnSpec = GridLayout.spec(GridLayout.UNDEFINED, 1f)
        vista.layoutParams = parametros

        vista.isClickable = true
        vista.setOnClickListener { pulsar(orden) }
        return vista
    }

    private fun pulsar(orden: String) {
        when (orden) {
            "#limpiar" -> { expresion = ""; previa.text = "" }
            "#borrar" -> expresion = expresion.dropLast(1)
            "#calcular" -> { calcular(); return }
            else -> expresion += orden
        }
        pantalla.text = if (expresion.isEmpty()) "0" else expresion
        actualizarPrevia()
    }

    private fun calcular() {
        if (expresion.isBlank()) return
        val anterior = expresion
        Nucleo.llamarAparte("calcular", expresion, modoAngulo, 6) { respuesta ->
            val datos = Nucleo.datos(respuesta)
            if (datos == null) {
                previa.text = Nucleo.error(respuesta)
                previa.setTextColor(requireContext().getColor(R.color.error))
                return@llamarAparte
            }
            previa.setTextColor(requireContext().getColor(R.color.suave))
            val texto = datos.getString("texto")
            val variable = datos.optString("variable", "")
            anotar("$anterior = $texto")
            if (variable.isNullOrEmpty() || variable == "null") {
                expresion = texto
                previa.text = ""
            } else {
                expresion = ""
                previa.text = "$variable = $texto"
            }
            pantalla.text = if (expresion.isEmpty()) "0" else expresion
        }
    }

    private fun actualizarPrevia() {
        if (!Nucleo.listo || expresion.isBlank()) { previa.text = ""; return }
        Nucleo.llamarAparte("vista_previa", expresion, modoAngulo, 6) { respuesta ->
            val datos = Nucleo.datos(respuesta)
            val texto = datos?.optString("texto").orEmpty()
            previa.text = if (texto.isEmpty()) "" else "= $texto"
        }
    }

    /** El teclado del sistema, a petición: para nombres de variable. */
    private fun escribirAMano() {
        val contexto = requireContext()
        val campo = EditText(contexto)
        campo.setText(expresion)
        campo.setSingleLine()
        AlertDialog.Builder(contexto)
            .setTitle("Escribir la operación")
            .setView(campo)
            .setNegativeButton("Cancelar", null)
            .setPositiveButton("Aceptar") { _, _ ->
                expresion = campo.text.toString()
                pantalla.text = if (expresion.isEmpty()) "0" else expresion
                actualizarPrevia()
            }
            .show()
    }
}
