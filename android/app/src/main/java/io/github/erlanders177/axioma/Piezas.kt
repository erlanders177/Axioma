package io.github.erlanders177.axioma

import android.content.Context
import android.graphics.Typeface
import android.text.InputType
import android.util.TypedValue
import android.view.Gravity
import android.view.View
import android.view.ViewGroup.LayoutParams.MATCH_PARENT
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView

/**
 * Las piezas sueltas con las que se montan los apartados.
 *
 * La interfaz se construye en código y no en XML porque casi todo es variable:
 * los datos de una figura cambian con la figura, y las unidades de una
 * magnitud con la magnitud. Siete diseños en XML llenos de campos ocultos
 * serían más difíciles de seguir que esto.
 */
object Piezas {

    fun puntos(contexto: Context, valor: Int): Int =
        TypedValue.applyDimension(
            TypedValue.COMPLEX_UNIT_DIP, valor.toFloat(),
            contexto.resources.displayMetrics
        ).toInt()

    private fun margenes(vista: View, arriba: Int = 8, abajo: Int = 0) {
        val parametros = LinearLayout.LayoutParams(MATCH_PARENT, WRAP_CONTENT)
        parametros.topMargin = puntos(vista.context, arriba)
        parametros.bottomMargin = puntos(vista.context, abajo)
        vista.layoutParams = parametros
    }

    fun rotulo(contexto: Context, texto: String): TextView {
        val vista = TextView(contexto)
        vista.text = texto
        vista.setTextColor(contexto.getColor(R.color.suave))
        vista.textSize = 12f
        margenes(vista, arriba = 12)
        return vista
    }

    fun titulo(contexto: Context, texto: String): TextView {
        val vista = TextView(contexto)
        vista.text = texto.uppercase()
        vista.setTextColor(contexto.getColor(R.color.suave))
        vista.textSize = 13f
        vista.letterSpacing = 0.08f
        vista.setTypeface(null, Typeface.BOLD)
        margenes(vista, arriba = 4, abajo = 4)
        return vista
    }

    /** Un campo de texto. Admite «5 cm», «sqrt(16)» o el nombre de una variable. */
    fun campo(contexto: Context, pista: String = ""): EditText {
        val vista = EditText(contexto)
        vista.hint = pista
        vista.setSingleLine()
        vista.inputType = InputType.TYPE_CLASS_TEXT
        vista.setTextColor(contexto.getColor(R.color.texto))
        vista.setHintTextColor(contexto.getColor(R.color.suave))
        vista.setBackgroundResource(R.drawable.fondo_campo)
        vista.textSize = 16f
        val relleno = puntos(contexto, 12)
        vista.setPadding(relleno, relleno, relleno, relleno)
        margenes(vista, arriba = 4)
        return vista
    }

    fun desplegable(contexto: Context, opciones: List<String> = emptyList()): Spinner {
        val vista = Spinner(contexto)
        vista.setBackgroundResource(R.drawable.fondo_campo)
        val relleno = puntos(contexto, 8)
        vista.setPadding(relleno, relleno, relleno, relleno)
        if (opciones.isNotEmpty()) llenar(vista, opciones)
        margenes(vista, arriba = 4)
        return vista
    }

    fun llenar(desplegable: Spinner, opciones: List<String>) {
        val adaptador = ArrayAdapter(
            desplegable.context, android.R.layout.simple_spinner_item, opciones
        )
        adaptador.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        desplegable.adapter = adaptador
    }

    fun boton(contexto: Context, texto: String, alPulsar: () -> Unit): Button {
        val vista = Button(contexto)
        vista.text = texto
        vista.isAllCaps = false
        vista.setTextColor(contexto.getColor(android.R.color.white))
        vista.setBackgroundResource(R.drawable.fondo_boton)
        vista.setOnClickListener { alPulsar() }
        margenes(vista, arriba = 14)
        return vista
    }

    /** Bloque monoespaciado para las salidas largas. */
    fun salida(contexto: Context): TextView {
        val vista = TextView(contexto)
        vista.setTextColor(contexto.getColor(R.color.texto))
        vista.typeface = Typeface.MONOSPACE
        vista.textSize = 13f
        vista.setBackgroundResource(R.drawable.fondo_panel)
        val relleno = puntos(contexto, 12)
        vista.setPadding(relleno, relleno, relleno, relleno)
        vista.setTextIsSelectable(true)
        margenes(vista, arriba = 12)
        return vista
    }

    /**
     * Una fila de resultado: etiqueta a la izquierda, valor a la derecha.
     *
     * Al pulsarla se guarda como variable, igual que en las otras dos
     * versiones: es lo que permite usar el volumen de una figura dentro de una
     * ecuación sin copiar el número a mano.
     */
    fun filaResultado(
        contexto: Context,
        etiqueta: String,
        valor: String,
        alPulsar: (() -> Unit)? = null
    ): LinearLayout {
        val fila = LinearLayout(contexto)
        fila.orientation = LinearLayout.HORIZONTAL
        val vertical = puntos(contexto, 10)
        fila.setPadding(0, vertical, 0, vertical)

        val izquierda = TextView(contexto)
        izquierda.text = etiqueta
        izquierda.setTextColor(contexto.getColor(R.color.suave))
        izquierda.layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)

        val derecha = TextView(contexto)
        derecha.text = valor
        derecha.setTextColor(contexto.getColor(R.color.texto))
        derecha.typeface = Typeface.MONOSPACE
        derecha.gravity = Gravity.END

        fila.addView(izquierda)
        fila.addView(derecha)
        if (alPulsar != null) {
            fila.isClickable = true
            fila.setOnClickListener { alPulsar() }
        }
        margenes(fila, arriba = 0)
        return fila
    }

    /**
     * Escucha de un desplegable, quedándose sólo con lo que interesa.
     *
     * La interfaz de Android pide dos métodos y cuatro parámetros para decir
     * «ha elegido el tercero».
     */
    fun alElegir(accion: (Int) -> Unit) = object : AdapterView.OnItemSelectedListener {
        override fun onItemSelected(
            padre: AdapterView<*>?, vista: View?, posicion: Int, id: Long
        ) = accion(posicion)

        override fun onNothingSelected(padre: AdapterView<*>?) {}
    }

    fun aviso(contexto: Context, texto: String, esError: Boolean = false): TextView {
        val vista = TextView(contexto)
        vista.text = texto
        vista.setTextColor(contexto.getColor(if (esError) R.color.error else R.color.suave))
        vista.textSize = 12f
        margenes(vista, arriba = 8)
        return vista
    }
}
