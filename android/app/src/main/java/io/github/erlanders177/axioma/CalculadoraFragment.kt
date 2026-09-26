package io.github.erlanders177.axioma

import android.content.Context
import android.graphics.Canvas
import android.graphics.ColorFilter
import android.graphics.Paint
import android.graphics.PixelFormat
import android.graphics.RectF
import android.graphics.Typeface
import android.graphics.drawable.Drawable
import android.view.Gravity
import android.view.View
import android.view.ViewGroup.LayoutParams.WRAP_CONTENT
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AlertDialog
import org.json.JSONObject

/**
 * La calculadora científica, con su propio teclado.
 *
 * Como una calculadora escolar: la tecla de fracción pone dos huecos, uno
 * arriba y otro abajo, y el resultado sale exacto (√2/2, 3/4) con la tecla
 * S⇔D para pasarlo a decimal. Qué hace cada tecla lo decide el núcleo —la
 * misma clase `Calculadora` que usan Windows y la web—; aquí sólo se le pasan
 * las teclas y se dibuja la pantalla que devuelve.
 *
 * El teclado del sistema no aparece nunca solo: sale a petición, con el botón
 * de escribir, para los nombres de variable y poco más.
 */
class CalculadoraFragment : ApartadoFragment() {

    override val clave = "calculadora"

    private lateinit var entrada: FormulaView
    private lateinit var resultado: FormulaView
    private lateinit var teclaSD: TextView
    private lateinit var pasos: PasoAPaso
    private var modoAngulo = "DEG"

    /** Lo escrito, en una línea: se recuerda al cerrar y se ofrece al teclear a mano. */
    private var escrito = ""
    private var valorResultado: Double? = null

    /** Teclas pulsadas antes de que el motor estuviera listo: no se pierden. */
    private val pendientes = mutableListOf<Pair<String, String>>()

    /** (rótulo, orden). Lo que empieza por `#` es una orden; lo demás, lo que se escribe. */
    private val teclas = listOf(
        "◀" to "#izquierda", "▶" to "#derecha", "" to "#fraccion", "S⇔D" to "#sd", "C" to "#limpiar",
        "sin" to "sin(", "cos" to "cos(", "tan" to "tan(", "√" to "√(", "⌫" to "#borrar",
        "ln" to "ln(", "log" to "log(", "(" to "(", ")" to ")", "xʸ" to "^",
        "7" to "7", "8" to "8", "9" to "9", "÷" to "÷", "π" to "π",
        "4" to "4", "5" to "5", "6" to "6", "×" to "×", "x²" to "²",
        "1" to "1", "2" to "2", "3" to "3", "−" to "−", "Ans" to "Ans",
        "0" to "0", "." to ".", "!" to "!", "+" to "+", "=" to "#calcular",
    )

    override fun construir(raiz: LinearLayout) {
        val contexto = requireContext()

        // -- pantalla ------------------------------------------------------- //
        val marco = LinearLayout(contexto)
        marco.orientation = LinearLayout.VERTICAL
        marco.setBackgroundResource(R.drawable.fondo_panel)
        val relleno = Piezas.puntos(contexto, 12)
        marco.setPadding(relleno, relleno / 2, relleno, relleno / 2)

        entrada = FormulaView(contexto)
        entrada.tag = "entrada"
        resultado = FormulaView(contexto)
        resultado.tag = "resultado"            // por dónde lo agarran las pruebas
        resultado.isClickable = true
        resultado.setOnClickListener {
            valorResultado?.let { guardarComoVariable("resultado", it) }
        }
        marco.addView(entrada)
        marco.addView(resultado)
        raiz.addView(marco)

        // -- modo de ángulo, escritura libre y paso a paso ------------------- //
        val fila = LinearLayout(contexto)
        fila.orientation = LinearLayout.HORIZONTAL
        fila.gravity = Gravity.CENTER_VERTICAL

        // Sólo las siglas: comparte fila con otros dos botones y no caben más.
        val modo = Piezas.desplegable(contexto, listOf("DEG", "RAD", "GRAD"))
        modo.layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
        modo.onItemSelectedListener = Piezas.alElegir { posicion ->
            modoAngulo = listOf("DEG", "RAD", "GRAD")[posicion]
            if (Nucleo.listo) teclear("estado")
        }
        fila.addView(modo)

        val escribir = Piezas.boton(contexto, "⌨") { escribirAMano() }
        escribir.layoutParams = LinearLayout.LayoutParams(
            Piezas.puntos(contexto, 52), WRAP_CONTENT
        ).also { it.leftMargin = Piezas.puntos(contexto, 8) }
        fila.addView(escribir)

        pasos = PasoAPaso(contexto, clave)
        pasos.boton.layoutParams = LinearLayout.LayoutParams(0, WRAP_CONTENT, 1f)
            .also { it.leftMargin = Piezas.puntos(contexto, 8) }
        fila.addView(pasos.boton)
        raiz.addView(fila)
        raiz.addView(pasos.caja)

        // -- teclado --------------------------------------------------------- //
        //
        // Filas con pesos y no una rejilla: con GridLayout, los márgenes que
        // añade por su cuenta se suman al ancho y la última columna se sale de
        // la pantalla en los móviles estrechos.
        for (fila5 in teclas.chunked(5)) {
            val filaTeclas = LinearLayout(contexto)
            filaTeclas.orientation = LinearLayout.HORIZONTAL
            val parametros = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
            parametros.topMargin = Piezas.puntos(contexto, 7)
            filaTeclas.layoutParams = parametros

            for ((rotulo, orden) in fila5) filaTeclas.addView(tecla(rotulo, orden))
            raiz.addView(filaTeclas)
        }

        pintarProvisional()
        cuandoListo {
            val guardado = requireContext()
                .getSharedPreferences("axioma-calculadora", Context.MODE_PRIVATE)
                .getString("escrito", "").orEmpty()
            if (pendientes.isEmpty()) {
                if (guardado.isNotEmpty()) teclear("cargar", guardado) else teclear("estado")
            }
            // Si el paso a paso está encendido en algún apartado, sympy se
            // carga ya en el hilo de fondo: así no hay que esperarlo al pedirlo.
            if (PasoAPaso.algunoEncendido(requireContext())) {
                Nucleo.llamarAparte("preparar_pesado", null) { }
            }
        }
    }

    override fun onPause() {
        super.onPause()
        // Que cerrar la aplicación no cueste la cuenta a medias.
        context?.getSharedPreferences("axioma-calculadora", Context.MODE_PRIVATE)
            ?.edit()?.putString("escrito", escrito)?.apply()
    }

    private fun tecla(rotulo: String, orden: String): View {
        val contexto = requireContext()
        val vista: View
        if (orden == "#fraccion") {
            // La tecla de fracción se dibuja con lo que hace: dos huecos y la raya.
            val imagen = ImageView(contexto)
            imagen.setImageDrawable(
                IconoFraccion(contexto.getColor(R.color.acento), Piezas.puntos(contexto, 24)))
            imagen.scaleType = ImageView.ScaleType.CENTER
            imagen.contentDescription = "Fracción"
            vista = imagen
        } else {
            val texto = TextView(contexto)
            texto.text = rotulo
            texto.gravity = Gravity.CENTER
            texto.textSize = if (rotulo.length > 2) 14f else 18f
            texto.setTextColor(
                contexto.getColor(
                    when {
                        orden == "#calcular" -> android.R.color.white
                        rotulo in listOf("÷", "×", "−", "+", "xʸ", "(", ")", "C", "⌫") -> R.color.acento
                        rotulo.first().isDigit() || rotulo == "." -> R.color.texto
                        else -> R.color.suave
                    }
                )
            )
            if (orden == "#calcular") texto.setTypeface(null, Typeface.BOLD)
            if (orden == "#sd") teclaSD = texto
            if (orden == "#izquierda") texto.contentDescription = "Mover a la izquierda"
            if (orden == "#derecha") texto.contentDescription = "Mover a la derecha"
            vista = texto
        }
        vista.setBackgroundResource(
            if (orden == "#calcular") R.drawable.fondo_tecla_igual else R.drawable.fondo_tecla
        )
        val parametros = LinearLayout.LayoutParams(0, Piezas.puntos(contexto, 50), 1f)
        parametros.marginStart = Piezas.puntos(contexto, 3)
        parametros.marginEnd = Piezas.puntos(contexto, 3)
        vista.layoutParams = parametros

        // Por dónde la encuentran las pruebas: el texto «1» no basta, porque
        // en otros apartados hay campos que también dicen «1».
        vista.tag = "tecla-$orden"
        vista.isClickable = true
        vista.setOnClickListener { pulsar(orden) }
        return vista
    }

    private fun pulsar(orden: String) {
        if (orden.startsWith("#")) teclear(orden.drop(1)) else teclear("insertar", orden)
    }

    /** Una tecla al núcleo, y a dibujar lo que conteste. */
    private fun teclear(orden: String, argumento: String = "") {
        if (!Nucleo.listo) {
            pendientes.add(orden to argumento)
            if (pendientes.size == 1) cuandoListo { soltarPendientes() }
            pintarProvisional()
            return
        }
        val respuesta = Nucleo.llamar("teclear", orden, argumento, modoAngulo, 6)
        val datos = Nucleo.datos(respuesta)
        if (datos == null) {
            resultado.ponerTexto(Nucleo.error(respuesta), "error", 15f)
            return
        }
        pintar(datos)
    }

    private fun soltarPendientes() {
        val tareas = pendientes.toList()
        pendientes.clear()
        for ((orden, argumento) in tareas) teclear(orden, argumento)
    }

    /** Lo tecleado antes de tener motor, tal cual, para que no parezca perdido. */
    private fun pintarProvisional() {
        var texto = ""
        for ((orden, argumento) in pendientes) {
            texto = when (orden) {
                "insertar", "escribir" -> texto + argumento
                "cargar" -> argumento
                "fraccion" -> "$texto/"
                "borrar" -> texto.dropLast(1)
                "limpiar" -> ""
                else -> texto
            }
        }
        entrada.ponerTexto(texto, "suave", 30f)
        resultado.ponerTexto(
            if (pendientes.any { it.first == "calcular" }) "Preparando el motor…" else "",
            "suave", 15f)
    }

    private fun pintar(d: JSONObject) {
        val calculado = d.optBoolean("calculado")
        entrada.poner(d.getJSONArray("entrada"), if (calculado) "suave" else "texto",
                      if (calculado) 20f else 30f)
        escrito = d.texto("texto")

        val visible = d.optJSONObject("resultado")
        val error = d.texto("error")
        when {
            error.isNotEmpty() -> resultado.ponerTexto(error, "error", 15f)
            visible != null -> resultado.poner(visible.getJSONArray("arbol"), "texto", 32f)
            else -> resultado.ponerTexto(d.texto("previa"), "suave", 16f)
        }
        valorResultado = visible?.optDouble("valor")

        val conExacto = visible?.optBoolean("tiene_exacto") == true
        teclaSD.alpha = if (conExacto) 1f else 0.4f
        teclaSD.setTextColor(requireContext().getColor(
            if (visible?.optBoolean("en_decimal") == true) R.color.acento else R.color.suave))

        val anotacion = d.optJSONObject("anotar")
        if (anotacion != null) {
            anotar(anotacion.getString("texto"))
            pedirPasos()
        }
    }

    /** El desarrollo de la última cuenta, en el hilo de fondo (sympy tarda). */
    private fun pedirPasos() {
        val cuenta = Nucleo.datos(Nucleo.llamar("cuenta_calculadora")) ?: return
        val hechos = cuenta.optJSONArray("pasos")
        if (hechos != null) {
            if (pasos.activo) pasos.pintar(hechos)
            return
        }
        pasos.pedir("pasos_de_cuenta", cuenta.getString("texto"), cuenta.getString("modo"),
                    cuenta.getJSONObject("entorno").toString(), cuenta.optInt("decimales", 6))
    }

    /** El teclado del sistema, a petición: para nombres de variable. */
    private fun escribirAMano() {
        val contexto = requireContext()
        val campo = EditText(contexto)
        campo.setText(escrito)
        campo.setSelection(campo.text.length)
        campo.setSingleLine()
        AlertDialog.Builder(contexto)
            .setTitle("Escribir la operación")
            .setMessage("«/» hace una fracción. Para guardar una variable: r = 5")
            .setView(campo)
            .setNegativeButton("Cancelar", null)
            .setPositiveButton("Aceptar") { _, _ ->
                teclear("cargar", campo.text.toString())
            }
            .show()
    }

    /** Un campo de texto de la respuesta, o vacío si no está o es null. */
    private fun JSONObject.texto(nombre: String): String =
        if (isNull(nombre)) "" else optString(nombre)
}

/** La tecla de fracción: dos huecos y la raya, que es lo que hace. */
private class IconoFraccion(private val color: Int, private val lado: Int) : Drawable() {

    private val trazo = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeWidth = maxOf(2f, lado / 14f)
    }

    override fun getIntrinsicWidth() = (lado * 0.9f).toInt()
    override fun getIntrinsicHeight() = lado

    override fun draw(lienzo: Canvas) {
        trazo.color = color
        val ancho = bounds.width().toFloat()
        val alto = bounds.height().toFloat()
        val cajaAncho = ancho * 0.46f
        val cajaAlto = alto * 0.3f
        val izquierda = bounds.left + (ancho - cajaAncho) / 2
        lienzo.drawRoundRect(RectF(izquierda, bounds.top + 2f, izquierda + cajaAncho,
                                   bounds.top + 2f + cajaAlto), 5f, 5f, trazo)
        lienzo.drawRoundRect(RectF(izquierda, bounds.bottom - 2f - cajaAlto,
                                   izquierda + cajaAncho, bounds.bottom - 2f), 5f, 5f, trazo)
        val medio = bounds.top + alto / 2
        lienzo.drawLine(bounds.left + ancho * 0.12f, medio, bounds.right - ancho * 0.12f, medio, trazo)
    }

    override fun setAlpha(alpha: Int) { trazo.alpha = alpha }
    override fun setColorFilter(filtro: ColorFilter?) { trazo.colorFilter = filtro }
    @Deprecated("Deprecated in Java")
    override fun getOpacity() = PixelFormat.TRANSLUCENT
}
