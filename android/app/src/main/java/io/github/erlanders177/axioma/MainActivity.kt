package io.github.erlanders177.axioma

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import io.github.erlanders177.axioma.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var vista: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        vista = ActivityMainBinding.inflate(layoutInflater)
        setContentView(vista.root)

        Nucleo.iniciar(this)
        val respuesta = Nucleo.llamar("calcular", "2*sin(30)+sqrt(16)", "DEG", 6)
        val datos = Nucleo.datos(respuesta)
        vista.estado.text = if (datos != null) {
            "2*sin(30)+sqrt(16) = ${datos.getString("texto")}"
        } else {
            Nucleo.error(respuesta)
        }
    }
}
