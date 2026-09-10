package io.github.erlanders177.axioma

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Handler
import android.os.Looper
import androidx.appcompat.app.AlertDialog
import org.json.JSONObject
import java.net.URL
import java.util.concurrent.Executors

/**
 * Avisa cuando hay una versión nueva.
 *
 * Axioma no está en Google Play, así que nadie la actualiza por su cuenta: sin
 * esto, quien la instaló hace meses se queda con esa para siempre y ni se
 * entera de que ha cambiado. Se comprueba una vez al día contra las versiones
 * publicadas en GitHub.
 *
 * El APK nuevo lleva el mismo identificador y la misma firma que el instalado,
 * así que Android lo trata como **actualización** y se instala encima, sin
 * desinstalar ni perder nada.
 */
object Actualizaciones {

    private const val ULTIMA = "https://api.github.com/repos/erlanders177/Axioma/releases/latest"
    private const val DESCARGA =
        "https://github.com/erlanders177/Axioma/releases/latest/download/Axioma.apk"
    private const val MEMORIA = "axioma-actualizaciones"
    private const val UN_DIA = 24 * 60 * 60 * 1000L

    private val hilo = Executors.newSingleThreadExecutor()
    private val principal = Handler(Looper.getMainLooper())

    /** Comprueba y, si hay novedad, lo dice. Nunca molesta más de una vez al día. */
    fun comprobar(contexto: Context, siempre: Boolean = false) {
        val memoria = contexto.getSharedPreferences(MEMORIA, Context.MODE_PRIVATE)
        val ultima = memoria.getLong("ultima", 0)
        if (!siempre && System.currentTimeMillis() - ultima < UN_DIA) return

        hilo.execute {
            val version = try {
                val texto = URL(ULTIMA).readText()
                JSONObject(texto).optString("tag_name").trim().removePrefix("v")
            } catch (e: Exception) {
                return@execute            // sin conexión: ya se mirará otro día
            }
            memoria.edit().putLong("ultima", System.currentTimeMillis()).apply()
            if (version.isEmpty()) return@execute
            if (esPosterior(version, BuildConfig.VERSION_NAME)) {
                principal.post { ofrecer(contexto, version) }
            } else if (siempre) {
                principal.post {
                    AlertDialog.Builder(contexto)
                        .setMessage("Ya tiene la última versión (${BuildConfig.VERSION_NAME}).")
                        .setPositiveButton("Vale", null)
                        .show()
                }
            }
        }
    }

    private fun ofrecer(contexto: Context, version: String) {
        AlertDialog.Builder(contexto)
            .setTitle("Hay una versión nueva")
            .setMessage(
                "Axioma $version ya está disponible; usted tiene la " +
                "${BuildConfig.VERSION_NAME}.\n\nSe instala encima de la actual, " +
                "sin perder nada."
            )
            .setNegativeButton("Ahora no", null)
            .setPositiveButton("Descargar") { _, _ ->
                contexto.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(DESCARGA)))
            }
            .show()
    }

    /**
     * ¿Es `candidata` posterior a `actual`? Compara 5.1.0 con 5.0.3 por partes.
     *
     * Comparar como texto diría que «5.10» es anterior a «5.9», que es justo el
     * momento en que la gente dejaría de recibir avisos.
     */
    fun esPosterior(candidata: String, actual: String): Boolean {
        val a = candidata.split(".").map { it.toIntOrNull() ?: 0 }
        val b = actual.split(".").map { it.toIntOrNull() ?: 0 }
        for (i in 0 until maxOf(a.size, b.size)) {
            val uno = a.getOrElse(i) { 0 }
            val otro = b.getOrElse(i) { 0 }
            if (uno != otro) return uno > otro
        }
        return false
    }
}
