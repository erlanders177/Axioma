plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "io.github.erlanders177.axioma"
    compileSdk = 35

    defaultConfig {
        applicationId = "io.github.erlanders177.axioma"
        minSdk = 24
        targetSdk = 35
        versionCode = 10
        versionName = "5.0.0"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        ndk {
            // El intérprete de Python es código nativo: hay que decir para qué
            // procesadores se compila. arm64 son los móviles; x86_64, el
            // emulador con el que se prueba.
            abiFilters += listOf("arm64-v8a", "x86_64")
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

    // La clave de firma sólo existe al publicar; en un clon cualquiera se
    // compila igual, sin firmar.
    val almacen = System.getenv("ANDROID_KEYSTORE_FILE")
    if (almacen != null) {
        signingConfigs.create("release") {
            storeFile = file(almacen)
            storePassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
            keyAlias = "axioma"
            keyPassword = System.getenv("ANDROID_KEYSTORE_PASSWORD")
        }
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
