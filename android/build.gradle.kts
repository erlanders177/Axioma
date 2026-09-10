// Axioma para Android.
//
// La aplicación es nativa, pero la matemática NO se reescribe: dentro corre el
// mismo `src/core` que la versión de escritorio y la web, con un intérprete de
// Python empotrado (Chaquopy). Tres calculadoras que se desvían con el tiempo
// sería la peor manera de tener tres versiones.

plugins {
    id("com.android.application") version "8.7.3" apply false
    id("org.jetbrains.kotlin.android") version "2.0.21" apply false
    id("com.chaquo.python") version "17.0.0" apply false
}
