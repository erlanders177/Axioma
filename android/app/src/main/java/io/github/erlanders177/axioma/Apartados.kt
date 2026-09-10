package io.github.erlanders177.axioma

import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Spinner
import android.widget.TextView
import org.json.JSONObject

/* Los apartados que quedan. Todos siguen el mismo patrón: piden datos, se los
 * pasan al núcleo y enseñan lo que devuelve. La matemática no está aquí. */

// --------------------------------------------------------------- conversiones -- //

class ConversionesFragment : ApartadoFragment() {

    override val clave = "conversiones"

    private lateinit var categoria: Spinner
    private lateinit var origen: Spinner
    private lateinit var destino: Spinner
    private lateinit var valor: EditText
    private lateinit var resultado: TextView
    private lateinit var tabla: LinearLayout
    private var categorias = listOf<String>()

    override fun construir(raiz: LinearLayout) {
        val contexto = requireContext()
        raiz.addView(Piezas.titulo(contexto, "Conversiones"))

        raiz.addView(Piezas.rotulo(contexto, "Magnitud"))
        categoria = Piezas.desplegable(contexto)
        raiz.addView(categoria)

        raiz.addView(Piezas.rotulo(contexto, "Valor"))
        valor = Piezas.campo(contexto, "1")
        valor.setText("1")
        raiz.addView(valor)

        raiz.addView(Piezas.rotulo(contexto, "De"))
        origen = Piezas.desplegable(contexto)
        raiz.addView(origen)

        raiz.addView(Piezas.rotulo(contexto, "A"))
        destino = Piezas.desplegable(contexto)
        raiz.addView(destino)

        raiz.addView(Piezas.boton(contexto, "Convertir") { convertir(true) })
        resultado = Piezas.salida(contexto)
        resultado.text = "—"
        raiz.addView(resultado)

        tabla = LinearLayout(contexto)
        tabla.orientation = LinearLayout.VERTICAL
        raiz.addView(tabla)

        cuandoListo {
            val grupos = Nucleo.lista(Nucleo.llamar("categorias")) ?: return@cuandoListo
            val nombres = mutableListOf<String>()
            for (i in 0 until grupos.length()) {
                val lista = grupos.getJSONObject(i).getJSONArray("nombres")
                for (j in 0 until lista.length()) nombres.add(lista.getString(j))
            }
            categorias = nombres
            Piezas.llenar(categoria, nombres)
            categoria.onItemSelectedListener = Piezas.alElegir { cargarUnidades() }
        }
    }

    private fun cargarUnidades() {
        val elegida = categorias.getOrNull(categoria.selectedItemPosition) ?: return
        val datos = Nucleo.datos(Nucleo.llamar("unidades_de", elegida)) ?: return
        val unidades = datos.getJSONArray("unidades")
        val etiquetas = mutableListOf<String>()
        simbolos.clear()
        for (i in 0 until unidades.length()) {
            val unidad = unidades.getJSONObject(i)
            etiquetas.add(unidad.getString("etiqueta"))
            simbolos.add(unidad.getString("simbolo"))
        }
        Piezas.llenar(origen, etiquetas)
        Piezas.llenar(destino, etiquetas)
        if (etiquetas.size > 1) destino.setSelection(1)
        convertir(false)
    }

    private val simbolos = mutableListOf<String>()

    private fun convertir(guardar: Boolean) {
        val elegida = categorias.getOrNull(categoria.selectedItemPosition) ?: return
        val de = simbolos.getOrNull(origen.selectedItemPosition) ?: return
        val a = simbolos.getOrNull(destino.selectedItemPosition) ?: return
        val cantidad = valor.text.toString().replace(',', '.').toDoubleOrNull() ?: return

        val respuesta = Nucleo.llamar("convertir", cantidad, de, a, elegida, 6)
        val datos = Nucleo.datos(respuesta)
        if (datos == null) {
            resultado.text = Nucleo.error(respuesta)
            return
        }
        val texto = "$cantidad $de  =  ${datos.getString("texto")} $a"
        resultado.text = texto
        if (guardar) anotar(texto)

        tabla.removeAllViews()
        val filas = datos.getJSONArray("tabla")
        for (i in 0 until minOf(filas.length(), 12)) {
            val fila = filas.getJSONObject(i)
            tabla.addView(Piezas.filaResultado(
                requireContext(), fila.getString("etiqueta"), fila.getString("texto")
            ) { guardarComoVariable(fila.getString("etiqueta"), fila.getDouble("valor")) })
        }
    }
}

// ------------------------------------------------------------------ geometría -- //

class GeometriaFragment : ApartadoFragment() {

    override val clave = "geometria"

    private lateinit var figura: Spinner
    private lateinit var campos: LinearLayout
    private lateinit var resultados: LinearLayout
    private lateinit var formulas: TextView
    private var nombres = listOf<String>()
    private val simbolos = mutableListOf<String>()
    private val entradas = mutableListOf<EditText>()

    override fun construir(raiz: LinearLayout) {
        val contexto = requireContext()
        raiz.addView(Piezas.titulo(contexto, "Geometría"))

        raiz.addView(Piezas.rotulo(contexto, "Figura"))
        figura = Piezas.desplegable(contexto)
        raiz.addView(figura)

        campos = LinearLayout(contexto)
        campos.orientation = LinearLayout.VERTICAL
        raiz.addView(campos)

        raiz.addView(Piezas.boton(contexto, "Calcular") { calcular(true) })

        resultados = LinearLayout(contexto)
        resultados.orientation = LinearLayout.VERTICAL
        raiz.addView(resultados)

        formulas = Piezas.aviso(contexto, "")
        raiz.addView(formulas)

        cuandoListo {
            val lista = Nucleo.lista(Nucleo.llamar("lista_figuras")) ?: return@cuandoListo
            nombres = (0 until lista.length()).map { lista.getJSONObject(it).getString("nombre") }
            Piezas.llenar(figura, nombres)
            figura.onItemSelectedListener = Piezas.alElegir { cargarParametros() }
        }
    }

    private fun cargarParametros() {
        val elegida = nombres.getOrNull(figura.selectedItemPosition) ?: return
        val datos = Nucleo.datos(Nucleo.llamar("parametros_de", elegida)) ?: return
        val contexto = requireContext()

        campos.removeAllViews()
        entradas.clear()
        simbolos.clear()

        val parametros = datos.getJSONArray("parametros")
        for (i in 0 until parametros.length()) {
            val parametro = parametros.getJSONObject(i)
            val unidad = parametro.optString("unidad", "")
            val etiqueta = parametro.getString("etiqueta") +
                if (unidad.isNotEmpty() && unidad != "u") " ($unidad)" else ""
            campos.addView(Piezas.rotulo(contexto, etiqueta))

            val campo = Piezas.campo(contexto, "admite 5 cm, 50 mm…")
            campo.setText(parametro.optString("predeterminado", ""))
            campos.addView(campo)
            entradas.add(campo)
            simbolos.add(parametro.getString("simbolo"))
        }

        val lista = datos.optJSONArray("formulas")
        formulas.text = if (lista == null) "" else
            (0 until lista.length()).joinToString("     ") { lista.getString(it) }
        calcular(false)
    }

    private fun calcular(guardar: Boolean) {
        val elegida = nombres.getOrNull(figura.selectedItemPosition) ?: return
        val valores = JSONObject()
        for ((i, simbolo) in simbolos.withIndex()) {
            valores.put(simbolo, entradas[i].text.toString())
        }

        Nucleo.llamarAparte("calcular_figura", elegida, valores.toString(), 6) { respuesta ->
            val datos = Nucleo.datos(respuesta)
            resultados.removeAllViews()
            if (datos == null) {
                resultados.addView(Piezas.aviso(requireContext(), Nucleo.error(respuesta), true))
                return@llamarAparte
            }
            val filas = datos.getJSONArray("resultados")
            for (i in 0 until filas.length()) {
                val fila = filas.getJSONObject(i)
                resultados.addView(Piezas.filaResultado(
                    requireContext(), fila.getString("etiqueta"), fila.getString("texto")
                ) { guardarComoVariable(fila.getString("etiqueta"), fila.getDouble("valor")) })
            }
            if (guardar && filas.length() > 0) {
                val primero = filas.getJSONObject(0)
                anotar("$elegida → ${primero.getString("etiqueta")}: ${primero.getString("texto")}")
            }
        }
    }
}

// ----------------------------------------------------------------- ecuaciones -- //

class EcuacionesFragment : ApartadoFragment() {

    override val clave = "ecuaciones"

    private lateinit var entrada: EditText
    private lateinit var salida: TextView

    override fun construir(raiz: LinearLayout) {
        val contexto = requireContext()
        raiz.addView(Piezas.titulo(contexto, "Ecuaciones"))
        raiz.addView(Piezas.rotulo(contexto, "Ecuación"))

        entrada = Piezas.campo(contexto, "x^2 - 5x + 6 = 0")
        entrada.setText("x^2 - 5x + 6 = 0")
        raiz.addView(entrada)

        raiz.addView(Piezas.boton(contexto, "Resolver") { resolver() })
        salida = Piezas.salida(contexto)
        salida.text = "—"
        raiz.addView(salida)
    }

    private fun resolver() {
        val texto = entrada.text.toString()
        salida.text = "Resolviendo…"
        Nucleo.llamarAparte("resolver_ecuacion", texto, 6) { respuesta ->
            val datos = Nucleo.datos(respuesta)
            if (datos == null) {
                salida.text = Nucleo.error(respuesta)
                return@llamarAparte
            }
            val soluciones = datos.getJSONArray("soluciones")
            val lineas = StringBuilder()
            lineas.append("Normalizada:  ").append(datos.getString("normalizada")).append('\n')
            lineas.append("Incógnita:    ").append(datos.getString("incognita")).append('\n')
            lineas.append("Factorizada:  ").append(datos.getString("factorizada")).append("\n\n")
            val incognita = datos.getString("incognita")
            for (i in 0 until soluciones.length()) {
                val solucion = soluciones.getJSONObject(i)
                lineas.append(incognita).append(i + 1).append(" = ")
                    .append(solucion.getString("exacto"))
                val aproximado = solucion.optString("aproximado", "")
                if (aproximado.isNotEmpty() && aproximado != "null") {
                    lineas.append("   ≈ ").append(aproximado)
                }
                lineas.append('\n')
            }
            salida.text = lineas.toString().trimEnd()
            anotar("$texto  →  " + (0 until soluciones.length())
                .joinToString(", ") { soluciones.getJSONObject(it).getString("exacto") })
        }
    }
}

// -------------------------------------------------------------------- cálculo -- //

class CalculoFragment : ApartadoFragment() {

    override val clave = "calculo"

    private val operaciones = listOf(
        "derivada" to "Derivada",
        "integral" to "Integral indefinida",
        "integral_definida" to "Integral definida",
        "limite" to "Límite",
        "analisis" to "Análisis de la función",
    )

    private lateinit var operacion: Spinner
    private lateinit var funcion: EditText
    private lateinit var variable: EditText
    private lateinit var desde: EditText
    private lateinit var hasta: EditText
    private lateinit var salida: TextView

    override fun construir(raiz: LinearLayout) {
        val contexto = requireContext()
        raiz.addView(Piezas.titulo(contexto, "Cálculo"))

        raiz.addView(Piezas.rotulo(contexto, "Operación"))
        operacion = Piezas.desplegable(contexto, operaciones.map { it.second })
        raiz.addView(operacion)

        raiz.addView(Piezas.rotulo(contexto, "Función"))
        funcion = Piezas.campo(contexto, "x^2*sin(x)")
        funcion.setText("x^2*sin(x)")
        raiz.addView(funcion)

        raiz.addView(Piezas.rotulo(contexto, "Variable"))
        variable = Piezas.campo(contexto, "x")
        variable.setText("x")
        raiz.addView(variable)

        raiz.addView(Piezas.rotulo(contexto, "Desde / tiende a"))
        desde = Piezas.campo(contexto, "0")
        raiz.addView(desde)

        raiz.addView(Piezas.rotulo(contexto, "Hasta"))
        hasta = Piezas.campo(contexto, "1")
        raiz.addView(hasta)

        raiz.addView(Piezas.boton(contexto, "Calcular") { calcular() })
        salida = Piezas.salida(contexto)
        salida.text = "—"
        raiz.addView(salida)
    }

    private fun calcular() {
        val clave = operaciones[operacion.selectedItemPosition].first
        salida.text = "Calculando…"
        Nucleo.llamarAparte(
            "calculo", clave, funcion.text.toString(),
            variable.text.toString().ifBlank { "x" },
            desde.text.toString(), hasta.text.toString()
        ) { respuesta ->
            val datos = Nucleo.datos(respuesta)
            if (datos == null) {
                salida.text = Nucleo.error(respuesta)
                return@llamarAparte
            }
            val filas = datos.getJSONArray("filas")
            salida.text = (0 until filas.length()).joinToString("\n") {
                val fila = filas.getJSONObject(it)
                "${fila.getString("etiqueta")}:  ${fila.getString("valor")}"
            }
            anotar("${operaciones[operacion.selectedItemPosition].second} de ${funcion.text}")
        }
    }
}

// --------------------------------------------------------------- combinatoria -- //

class CombinatoriaFragment : ApartadoFragment() {

    override val clave = "combinatoria"

    private val operaciones = listOf(
        "factorial" to "Factorial  n!",
        "combinaciones" to "Combinaciones  C(n, r)",
        "permutaciones" to "Permutaciones  P(n, r)",
        "variaciones_rep" to "Variaciones con repetición",
        "combinaciones_rep" to "Combinaciones con repetición",
    )

    private lateinit var operacion: Spinner
    private lateinit var n: EditText
    private lateinit var r: EditText
    private lateinit var salida: TextView

    override fun construir(raiz: LinearLayout) {
        val contexto = requireContext()
        raiz.addView(Piezas.titulo(contexto, "Combinatoria"))

        raiz.addView(Piezas.rotulo(contexto, "Operación"))
        operacion = Piezas.desplegable(contexto, operaciones.map { it.second })
        raiz.addView(operacion)

        raiz.addView(Piezas.rotulo(contexto, "n"))
        n = Piezas.campo(contexto, "10")
        n.setText("10")
        raiz.addView(n)

        raiz.addView(Piezas.rotulo(contexto, "r"))
        r = Piezas.campo(contexto, "4")
        r.setText("4")
        raiz.addView(r)

        raiz.addView(Piezas.boton(contexto, "Calcular") { calcular() })
        salida = Piezas.salida(contexto)
        salida.text = "—"
        raiz.addView(salida)
    }

    private fun calcular() {
        val clave = operaciones[operacion.selectedItemPosition].first
        val valorN = n.text.toString().toIntOrNull() ?: 0
        val valorR = r.text.toString().toIntOrNull() ?: 0
        Nucleo.llamarAparte("combinatoria", clave, valorN, valorR) { respuesta ->
            val datos = Nucleo.datos(respuesta)
            if (datos == null) {
                salida.text = Nucleo.error(respuesta)
                return@llamarAparte
            }
            val valor = datos.getString("valor")
            salida.text = valor
            anotar("${operaciones[operacion.selectedItemPosition].second}: " +
                   valor.take(40))
        }
    }
}

// ---------------------------------------------------------------------- bases -- //

class BasesFragment : ApartadoFragment() {

    override val clave = "bases"

    private val bases = listOf(10 to "decimal", 2 to "binario", 8 to "octal", 16 to "hexadecimal")

    private lateinit var entrada: EditText
    private lateinit var base: Spinner
    private lateinit var tabla: LinearLayout

    override fun construir(raiz: LinearLayout) {
        val contexto = requireContext()
        raiz.addView(Piezas.titulo(contexto, "Bases numéricas"))

        raiz.addView(Piezas.rotulo(contexto, "Número"))
        entrada = Piezas.campo(contexto, "255")
        entrada.setText("255")
        raiz.addView(entrada)

        raiz.addView(Piezas.rotulo(contexto, "Base de partida"))
        base = Piezas.desplegable(contexto, bases.map { "${it.second} (base ${it.first})" })
        raiz.addView(base)

        raiz.addView(Piezas.boton(contexto, "Convertir") { convertir() })

        tabla = LinearLayout(contexto)
        tabla.orientation = LinearLayout.VERTICAL
        raiz.addView(tabla)

        cuandoListo { convertir() }
    }

    private fun convertir() {
        val origen = bases[base.selectedItemPosition].first
        val respuesta = Nucleo.llamar("convertir_base", entrada.text.toString(), origen, 8)
        val datos = Nucleo.datos(respuesta)
        tabla.removeAllViews()
        if (datos == null) {
            tabla.addView(Piezas.aviso(requireContext(), Nucleo.error(respuesta), true))
            return
        }
        val filas = datos.getJSONArray("tabla")
        for (i in 0 until filas.length()) {
            val fila = filas.getJSONObject(i)
            tabla.addView(Piezas.filaResultado(
                requireContext(),
                "${fila.getString("nombre")} (base ${fila.getInt("base")})",
                fila.getString("texto")
            ))
        }
    }
}
