package io.github.erlanders177.axioma

import android.os.Bundle
import android.view.View
import android.view.inputmethod.EditorInfo
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import androidx.viewpager2.adapter.FragmentStateAdapter
import com.google.android.material.tabs.TabLayoutMediator
import io.github.erlanders177.axioma.databinding.ActivityMainBinding

/**
 * La ventana de Axioma: siete apartados en pestañas y una barra de cálculo.
 *
 * La interfaz se dibuja antes de que el motor esté listo. Python tarda un
 * segundo largo en arrancar, y esperarlo con la pantalla en blanco haría que
 * abrir la aplicación pareciera una instalación, que es justo lo que se
 * quería dejar atrás.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var vista: ActivityMainBinding

    private val apartados: List<Pair<String, () -> Fragment>> = listOf(
        "Calculadora" to { CalculadoraFragment() },
        "Conversiones" to { ConversionesFragment() },
        "Geometría" to { GeometriaFragment() },
        "Ecuaciones" to { EcuacionesFragment() },
        "Cálculo" to { CalculoFragment() },
        "Combinatoria" to { CombinatoriaFragment() },
        "Bases" to { BasesFragment() },
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        vista = ActivityMainBinding.inflate(layoutInflater)
        setContentView(vista.root)

        vista.version.text = "v${BuildConfig.VERSION_NAME}"
        vista.apartados.adapter = Apartados(this)
        vista.apartados.offscreenPageLimit = 2
        TabLayoutMediator(vista.pestanas, vista.apartados) { pestana, posicion ->
            pestana.text = apartados[posicion].first
        }.attach()

        prepararBarra()
        vista.btnVariables.setOnClickListener { mostrarVariables() }

        Nucleo.arrancar(this)
        Nucleo.cuandoListo { vista.avisoMotor.visibility = View.GONE }

        // Sin tienda de aplicaciones, nadie avisa de las versiones nuevas.
        Actualizaciones.comprobar(this)
    }

    private inner class Apartados(actividad: AppCompatActivity) :
        FragmentStateAdapter(actividad) {
        override fun getItemCount() = apartados.size
        override fun createFragment(posicion: Int): Fragment = apartados[posicion].second()
    }

    // ------------------------------------------------------ barra de cálculo -- //

    /**
     * Una cuenta suelta sin salir del apartado en el que se está.
     *
     * Las variables que se definan aquí valen en todos los apartados, que es lo
     * que permite arrastrar un resultado de uno a otro.
     */
    private fun prepararBarra() {
        vista.barraEntrada.setOnEditorActionListener { _, accion, _ ->
            if (accion == EditorInfo.IME_ACTION_DONE) {
                calcularEnLaBarra()
                true
            } else {
                false
            }
        }
    }

    private fun calcularEnLaBarra() {
        val expresion = vista.barraEntrada.text.toString().trim()
        if (expresion.isEmpty()) return
        if (!Nucleo.listo) {
            vista.barraResultado.text = "preparando…"
            Nucleo.cuandoListo { calcularEnLaBarra() }
            return
        }
        Nucleo.llamarAparte("calcular", expresion, "DEG", 6) { respuesta ->
            val datos = Nucleo.datos(respuesta)
            if (datos == null) {
                vista.barraResultado.text = Nucleo.error(respuesta).take(40)
                return@llamarAparte
            }
            vista.barraResultado.text = "= ${datos.getString("texto")}"
            vista.barraEntrada.setText("")
        }
    }

    private fun mostrarVariables() {
        if (!Nucleo.listo) return
        val respuesta = Nucleo.llamar("listar_variables")
        val datos = Nucleo.datos(respuesta)
        val nombres = datos?.keys()?.asSequence()?.toList().orEmpty()
        if (nombres.isEmpty()) {
            AlertDialog.Builder(this)
                .setMessage("No hay ninguna variable definida.\n\nEscriba «r = 5» en la " +
                            "barra de abajo, o pulse un resultado para guardarlo.")
                .setPositiveButton("Vale", null)
                .show()
            return
        }
        val texto = nombres.joinToString("\n") { "$it = ${datos?.get(it)}" }
        AlertDialog.Builder(this)
            .setTitle("Variables")
            .setMessage(texto)
            .setNegativeButton("Cerrar", null)
            .setPositiveButton("Borrar todas") { _, _ -> Nucleo.llamar("borrar_variables") }
            .show()
    }
}
