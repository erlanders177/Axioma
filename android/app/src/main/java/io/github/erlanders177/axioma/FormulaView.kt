package io.github.erlanders177.axioma

import android.content.Context
import android.graphics.Canvas
import android.graphics.DashPathEffect
import android.graphics.Paint
import android.graphics.Path
import android.graphics.RectF
import android.util.TypedValue
import android.view.View
import org.json.JSONArray
import org.json.JSONObject
import kotlin.math.max
import kotlin.math.min

/**
 * Una fórmula dibujada como en el cuaderno: fracciones con su raya, raíces con
 * su signo, los huecos por rellenar y el cursor.
 *
 * Dibuja el árbol que devuelve el núcleo —el mismo que dibujan la web y la
 * versión de Windows—: `{"t": "frac", "n": …, "d": …}`, `{"t": "raiz", …}`,
 * texto, huecos y cursor. Aquí sólo se decide dónde va cada trozo.
 *
 * Todo se alinea sobre un eje horizontal: una fracción tiene el numerador por
 * encima y el denominador por debajo, y el texto va centrado en él.
 */
class FormulaView(contexto: Context) : View(contexto) {

    private data class Medida(val ancho: Float, val arriba: Float, val abajo: Float)

    private var arbol = JSONArray()
    private var tamano = sp(28f)
    private var color = contexto.getColor(R.color.texto)
    private val colorSuave = contexto.getColor(R.color.suave)
    private val colorAcento = contexto.getColor(R.color.acento)
    private var parpadeo = true

    /** Texto plano de lo dibujado («5/6», «2√2»): para TalkBack y las pruebas. */
    var texto: String = ""
        private set

    private val pincel = Paint(Paint.ANTI_ALIAS_FLAG)
    private val trazo = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        style = Paint.Style.STROKE
        strokeCap = Paint.Cap.ROUND
        strokeJoin = Paint.Join.ROUND
    }

    private val parpadear = object : Runnable {
        override fun run() {
            parpadeo = !parpadeo
            invalidate()
            postDelayed(this, 530)
        }
    }

    private fun sp(valor: Float) = TypedValue.applyDimension(
        TypedValue.COMPLEX_UNIT_SP, valor, resources.displayMetrics)

    // ---------------------------------------------------------------- contenido -- //

    /** `colorNombre`: "texto", "suave", "error". */
    fun poner(nuevo: JSONArray, colorNombre: String = "texto", tamanoSp: Float? = null) {
        arbol = nuevo
        color = context.getColor(when (colorNombre) {
            "suave" -> R.color.suave
            "error" -> R.color.error
            else -> R.color.texto
        })
        if (tamanoSp != null) tamano = sp(tamanoSp)
        texto = textoPlano(arbol)
        contentDescription = texto
        parpadeo = true
        removeCallbacks(parpadear)
        if (tieneCursor(arbol)) postDelayed(parpadear, 530)
        requestLayout()
        invalidate()
    }

    fun ponerTexto(contenido: String, colorNombre: String = "texto", tamanoSp: Float? = null) {
        val fila = JSONArray()
        if (contenido.isNotEmpty()) fila.put(JSONObject().put("t", "txt").put("v", contenido))
        poner(fila, colorNombre, tamanoSp)
    }

    override fun onDetachedFromWindow() {
        removeCallbacks(parpadear)
        super.onDetachedFromWindow()
    }

    private fun tieneCursor(fila: JSONArray): Boolean {
        for (i in 0 until fila.length()) {
            val nodo = fila.getJSONObject(i)
            if (nodo.optString("t") == "cursor") return true
            for (clave in listOf("n", "d", "r")) {
                val hija = nodo.optJSONArray(clave)
                if (hija != null && tieneCursor(hija)) return true
            }
        }
        return false
    }

    // ------------------------------------------------------------------- medir -- //

    private fun altoTexto(t: Float): Float {
        pincel.textSize = t
        val m = pincel.fontMetrics
        return m.descent - m.ascent
    }

    private fun medirFila(fila: JSONArray, t: Float): Medida {
        if (fila.length() == 0) {
            val mitad = altoTexto(t) / 2
            return Medida(0f, mitad, mitad)
        }
        var ancho = 0f
        var arriba = 0f
        var abajo = 0f
        for (i in 0 until fila.length()) {
            val m = medir(fila.getJSONObject(i), t, i == 0)
            ancho += m.ancho
            arriba = max(arriba, m.arriba)
            abajo = max(abajo, m.abajo)
        }
        return Medida(ancho, arriba, abajo)
    }

    private fun medir(nodo: JSONObject, t: Float, primero: Boolean): Medida {
        val mitad = altoTexto(t) / 2
        return when (nodo.optString("t")) {
            "txt" -> {
                pincel.textSize = t
                Medida(pincel.measureText(espaciar(nodo.optString("v"), primero)), mitad, mitad)
            }
            "cursor" -> Medida(t * 0.08f, mitad, mitad)
            "hueco" -> Medida(t * 0.62f + t * 0.12f, t * 0.42f, t * 0.42f)
            "frac" -> {
                val interior = t * 0.9f
                val arriba = medirFila(nodo.getJSONArray("n"), interior)
                val abajo = medirFila(nodo.getJSONArray("d"), interior)
                val hueco = max(2f, t * 0.08f)
                Medida(max(arriba.ancho, abajo.ancho) + t * 0.3f,
                       arriba.arriba + arriba.abajo + hueco,
                       abajo.arriba + abajo.abajo + hueco)
            }
            "raiz" -> {
                val dentro = medirFila(nodo.getJSONArray("r"), t)
                val signo = t * 0.55f + if (nodo.has("i")) t * 0.15f else 0f
                Medida(signo + dentro.ancho + t * 0.12f, dentro.arriba + t * 0.12f, dentro.abajo)
            }
            else -> Medida(0f, mitad, mitad)
        }
    }

    override fun onMeasure(anchoSpec: Int, altoSpec: Int) {
        val ancho = MeasureSpec.getSize(anchoSpec)
        val medida = medirFila(if (arbol.length() == 0) cero() else arbol, tamano)
        val alto = max(tamano * 1.4f, medida.arriba + medida.abajo + tamano * 0.3f)
        setMeasuredDimension(ancho, alto.toInt())
    }

    private fun cero() = JSONArray().put(JSONObject().put("t", "txt").put("v", "0"))

    // ----------------------------------------------------------------- dibujar -- //

    override fun onDraw(lienzo: Canvas) {
        super.onDraw(lienzo)
        val medida = medirFila(arbol, tamano)
        val eje = (height - (medida.arriba + medida.abajo)) / 2 + medida.arriba
        val margen = tamano * 0.2f
        var x = width - margen - medida.ancho
        if (x < margen) {
            // No cabe: se desplaza lo justo para que el cursor quede a la vista.
            val cursor = xDelCursor()
            if (cursor != null) x = max(x, min(margen, width - margen * 3 - cursor))
        }
        dibujarFila(lienzo, arbol, x, eje, tamano, color)
    }

    private fun dibujarFila(lienzo: Canvas, fila: JSONArray, desde: Float, eje: Float,
                            t: Float, tinta: Int): Float {
        var x = desde
        for (i in 0 until fila.length()) x = dibujar(lienzo, fila.getJSONObject(i), x, eje, t, tinta, i == 0)
        return x
    }

    private fun dibujar(lienzo: Canvas, nodo: JSONObject, x: Float, eje: Float, t: Float,
                        tinta: Int, primero: Boolean): Float {
        val medida = medir(nodo, t, primero)
        val grosor = max(2f, t / 14f)
        when (nodo.optString("t")) {
            "txt" -> {
                pincel.textSize = t
                pincel.color = tinta
                val m = pincel.fontMetrics
                val base = eje - (m.descent - m.ascent) / 2 - m.ascent
                lienzo.drawText(espaciar(nodo.optString("v"), primero), x, base, pincel)
            }
            "cursor" -> if (parpadeo) {
                pincel.color = colorAcento
                lienzo.drawRect(x, eje - medida.arriba, x + max(3f, t * 0.07f),
                                eje + medida.abajo, pincel)
            }
            "hueco" -> {
                val caja = RectF(x + t * 0.06f, eje - medida.arriba,
                                 x + medida.ancho - t * 0.06f, eje + medida.abajo)
                if (nodo.optBoolean("activo")) {
                    pincel.color = colorAcento
                    pincel.alpha = 60
                    lienzo.drawRoundRect(caja, 6f, 6f, pincel)
                    pincel.alpha = 255
                    trazo.color = colorAcento
                    trazo.pathEffect = null
                } else {
                    trazo.color = colorSuave
                    trazo.pathEffect = DashPathEffect(floatArrayOf(8f, 6f), 0f)
                }
                trazo.strokeWidth = 3f
                lienzo.drawRoundRect(caja, 6f, 6f, trazo)
                trazo.pathEffect = null
            }
            "frac" -> {
                val interior = t * 0.9f
                val arriba = medirFila(nodo.getJSONArray("n"), interior)
                val abajo = medirFila(nodo.getJSONArray("d"), interior)
                val hueco = max(2f, t * 0.08f)
                trazo.color = tinta
                trazo.strokeWidth = grosor
                lienzo.drawLine(x + t * 0.06f, eje, x + medida.ancho - t * 0.06f, eje, trazo)
                val centro = x + medida.ancho / 2
                dibujarFila(lienzo, nodo.getJSONArray("n"), centro - arriba.ancho / 2,
                            eje - hueco - arriba.abajo, interior, tinta)
                dibujarFila(lienzo, nodo.getJSONArray("d"), centro - abajo.ancho / 2,
                            eje + hueco + abajo.arriba, interior, tinta)
            }
            "raiz" -> {
                val inicio = x + if (nodo.has("i")) t * 0.15f else 0f
                val signo = t * 0.55f
                val alto = eje - medida.arriba + grosor / 2
                val bajo = eje + medida.abajo
                val camino = Path()
                camino.moveTo(inicio, eje + t * 0.05f)
                camino.lineTo(inicio + signo * 0.25f, eje - t * 0.02f)
                camino.lineTo(inicio + signo * 0.5f, bajo)
                camino.lineTo(inicio + signo * 0.95f, alto)
                camino.lineTo(x + medida.ancho, alto)
                trazo.color = tinta
                trazo.strokeWidth = grosor
                lienzo.drawPath(camino, trazo)
                if (nodo.has("i")) {
                    pincel.textSize = t * 0.45f
                    pincel.color = tinta
                    lienzo.drawText(nodo.getString("i"), x, eje - t * 0.1f, pincel)
                }
                dibujarFila(lienzo, nodo.getJSONArray("r"), inicio + signo, eje, t, tinta)
            }
        }
        return x + medida.ancho
    }

    /** Dónde cae el cursor contando desde el principio de la fila. */
    private fun xDelCursor(): Float? {
        var x = 0f
        for (i in 0 until arbol.length()) {
            val nodo = arbol.getJSONObject(i)
            val encontrado = buscarCursor(nodo, x, tamano, i == 0)
            if (encontrado != null) return encontrado
            x += medir(nodo, tamano, i == 0).ancho
        }
        return null
    }

    private fun buscarCursor(nodo: JSONObject, x: Float, t: Float, primero: Boolean): Float? {
        when (nodo.optString("t")) {
            "cursor" -> return x
            "hueco" -> if (nodo.optBoolean("activo")) return x
            "frac" -> {
                val interior = t * 0.9f
                val medida = medir(nodo, t, primero)
                for (clave in listOf("n", "d")) {
                    val fila = nodo.getJSONArray(clave)
                    var inicio = x + (medida.ancho - medirFila(fila, interior).ancho) / 2
                    for (i in 0 until fila.length()) {
                        val hijo = fila.getJSONObject(i)
                        val encontrado = buscarCursor(hijo, inicio, interior, i == 0)
                        if (encontrado != null) return encontrado
                        inicio += medir(hijo, interior, i == 0).ancho
                    }
                }
            }
            "raiz" -> {
                var inicio = x + t * 0.55f + if (nodo.has("i")) t * 0.15f else 0f
                val fila = nodo.getJSONArray("r")
                for (i in 0 until fila.length()) {
                    val hijo = fila.getJSONObject(i)
                    val encontrado = buscarCursor(hijo, inicio, t, i == 0)
                    if (encontrado != null) return encontrado
                    inicio += medir(hijo, t, i == 0).ancho
                }
            }
        }
        return null
    }

    companion object {
        private val OPERADOR = Regex("\\s*([+−×÷=])\\s*")

        /** «1+2» se lee mejor con un poco de aire: «1 + 2». El signo de delante, no. */
        fun espaciar(texto: String, primero: Boolean): String =
            OPERADOR.replace(texto) { m ->
                if (primero && m.range.first == 0) m.value.trimStart()
                else " ${m.groupValues[1]} "
            }

        /** El árbol en una línea: «5/6», «2√2 + 1/3», «(√5 + 1)/2». */
        fun textoPlano(fila: JSONArray): String {
            val partes = StringBuilder()
            for (i in 0 until fila.length()) {
                val nodo = fila.getJSONObject(i)
                when (nodo.optString("t")) {
                    "txt" -> partes.append(nodo.optString("v"))
                    "raiz" -> partes.append(if (nodo.optString("i") == "3") "∛" else "√")
                        .append(textoPlano(nodo.getJSONArray("r")))
                    "frac" -> {
                        val arriba = textoPlano(nodo.getJSONArray("n"))
                        val abajo = textoPlano(nodo.getJSONArray("d"))
                        partes.append(if (" + " in arriba || " − " in arriba) "($arriba)" else arriba)
                        partes.append("/")
                        partes.append(if (abajo.all { it.isDigit() }) abajo else "($abajo)")
                    }
                }
            }
            return partes.toString()
        }
    }
}
