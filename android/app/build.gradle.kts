plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

/* La versión sale de src/__init__.py, la misma que Windows y la web.
 *
 * Escrita aquí a mano, se quedaba atrás: el APK de una versión nueva salía con
 * el mismo número interno que el anterior, y Android se niega a instalar
 * encima un APK cuyo número no sube. Las actualizaciones morían justo en el
 * segundo intento.
 *
 * El número interno se deriva de la versión (5.0.2 → 50002), así que sube
 * solo y siempre en el mismo orden que la versión visible. */
val versionDelProyecto: String = Regex("__version__\s*=\s*\"([^\"]+)\"")
    .find(file("../../src/__init__.py").readText())
    ?.groupValues?.get(1) ?: "0.0.0"

val numeroInterno: Int = versionDelProyecto.split(".")
    .map { it.toIntOrNull() ?: 0 }
    .let { (it.getOrElse(0) { 0 } * 10000) + (it.getOrElse(1) { 0 } * 100) + it.getOrElse(2) { 0 } }

android {
    namespace = "io.github.erlanders177.axioma"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.erlanders177.axioma"
        minSdk = 24
        targetSdk = 35
        versionCode = numeroInterno
        versionName = versionDelProyecto
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        ndk {
            // El intérprete de Python es código nativo: hay que decir para qué
            // procesadores se compila. arm64 son los móviles; x86_64, el
            // emulador con el que se prueba.
            abiFilters += listOf("arm64-v8a", "x86_64")
        }
    }

    // Antes de buildTypes a propósito: ahí se busca por nombre, y si todavía
    // no existe se obtiene null sin protestar. El APK sale sin firmar, y sin
    // firma Android no lo instala.
    val almacen = System.getenv("ANDROID_KEYSTORE_FILE")
    if (almacen != null && file(almacen).exists()) {
        signingConfigs.create("release") {
            storeFile = file(almacen)
            storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
            keyAlias = "axioma"
            keyPassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    buildFeatures {
        viewBinding = true
        buildConfig = true
    }
}

chaquopy {
    defaultConfig {
        version = "3.12"
        pip {
            // Lo único que el núcleo necesita de fuera.
            install("sympy==1.13.3")
        }
    }
    // El núcleo y el puente los copia aquí `tools/preparar_android.py`, igual
    // que `preparar_web.py` hace su copia para el navegador.
    sourceSets { getByName("main") { srcDir("src/main/python") } }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.viewpager2:viewpager2:1.1.0")

    testImplementation("junit:junit:4.13.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.espresso:espresso-core:3.6.1")
}
