# Historial de cambios

Las versiones siguen [SemVer](https://semver.org/lang/es/).

---

## 4.0.0

Axioma sale del escritorio: ahora también funciona en el móvil.

### La misma calculadora, en el navegador

Hay una versión web en `web/`, que corre **el mismo núcleo Python** que la de
escritorio. No es una reescritura en JavaScript: Pyodide es Python compilado a
WebAssembly, así que `src/core` se copia dentro del navegador y allí se ejecuta.
Un cilindro de radio `5 cm` y altura `50 mm` da 392.699 cm³ en los dos sitios,
por construcción y no por casualidad.

- **Se adapta a la pantalla.** En un teléfono se ve un apartado cada vez, con el
  menú abajo al alcance del pulgar; en un ordenador, varios en columnas y el
  menú al lado, como en la aplicación de escritorio.
- **Funciona sin conexión.** La primera visita descarga Python; a partir de ahí
  todo sale de la caché. Probado apagando el servidor: sigue calculando.
- **Se instala.** Desde el navegador, «añadir a la pantalla de inicio»: queda
  como una aplicación más, sin tiendas de por medio.
- **Arranca en unos 4 segundos**, porque sympy sólo se descarga cuando se abre
  Ecuaciones o Cálculo. La calculadora, las conversiones, la geometría, la
  combinatoria y las bases no lo necesitan.

Siete apartados de momento: calculadora, conversiones, geometría, ecuaciones,
cálculo, combinatoria y bases. Los otros nueve siguen siendo cosa del
escritorio.

### Cómo se sostiene

- `tools/preparar_web.py` empaqueta `src/core` como paquete, sin tocar una línea
  ni aplanar sus importaciones.
- `web/puente.py` traduce entre el núcleo y la interfaz. No calcula nada: si hay
  algo que resolver, lo resuelve el núcleo.
- **20 pruebas en un Chromium de verdad**, en móvil y en escritorio, que
  comprueban que los resultados coinciden con los del escritorio.
- Una prueba más impide que `web/nucleo.json` se quede desfasado del núcleo: sin
  ella, un arreglo saldría en Windows y no en el móvil, que es la peor clase de
  fallo.

### Otros cambios

- La versión web se publica sola en GitHub Pages al tocar `web/` o `src/core`.

---

## 3.5.0

Lo que sale en un apartado se usa en los demás, y el sitio se reparte a mano.

### Llevar un resultado de un apartado a otro

Doble clic en cualquier fila de resultados y ese valor se guarda como
**variable compartida**: a partir de ahí vale en los campos de cualquier
apartado, en la calculadora, en la barra y **dentro de una ecuación**.

Calcule el volumen de un cilindro en Geometría, guárdelo como `volumen`, y
escriba `x^2 = volumen` en Ecuaciones. Se resuelve.

- En las salidas de texto (ecuaciones, matrices, pasos, gráficas) se selecciona
  el número y se usa el menú del botón derecho.
- Se guarda el **valor exacto**, no el que se ve: el resultado mostrado va
  redondeado a los decimales configurados, y arrastrar ese redondeo a los
  cálculos siguientes es justo lo que se quiere evitar.

### Repartir el sitio arrastrando

Los separadores entre bloques eran de un píxel: había que acertar con el cursor
para mover uno. Ahora son anchos y se iluminan al pasar por encima. Se agarra el
borde entre dos apartados y se arrastra a izquierda o derecha para dar sitio a
uno quitándoselo al otro.

### Corregido

- Una variable de varias letras se partía en factores: `volumen` era
  `v·o·l·u·m·e·n` para el motor simbólico, así que un resultado guardado no
  servía de nada dentro de una ecuación o una función.
- Al sustituir variables se protege la incógnita: quien define `x` y luego
  resuelve `x^2 = 4` no se queda sin ecuación.

---

## 3.4.0

Una sola pantalla. Se acabó cambiar de página.

### Los apartados se enganchan, no se turnan

La calculadora ocupa el centro y no se cierra nunca. Los demás apartados se
enganchan a su alrededor pulsando su nombre en el lateral, **los que se quieran
a la vez**, y se colocan arrastrándolos por su título: a un lado, encima,
debajo, apilados en pestañas o sueltos fuera de la ventana.

Ése era el problema de fondo: para resolver un problema de trigonometría hace
falta ver la figura, la ecuación y la calculadora **al mismo tiempo**. Con un
menú que cambia de página sólo se ve una cosa, y la anterior desaparece.

- Volver a pulsar en el lateral cierra el apartado; <kbd>Ctrl</kbd>+<kbd>W</kbd>
  cierra el que se esté usando y «Cerrar apartados» los quita todos.
- Cerrar un apartado **no borra lo que había escrito**: al reabrirlo sigue ahí.
- La disposición se guarda: la aplicación vuelve a abrirse tal como se dejó.
- «A la vez» limita cuántos puede haber abiertos (2, 3, 4 o sin tope). Al
  pasarse se cierra el más antiguo. De partida no hay tope.

### Cada apartado, con su propio historial

Vuelve a haber un historial por apartado, ahora que se ven varios a la vez: el
de una figura geométrica no pinta nada mezclado con el de la calculadora. Va
plegado, y el botón «Historial» de cada bloque lo despliega; mientras está
plegado, el número que lleva al lado avisa de lo que se ha ido guardando.

### Los paneles se adaptan al hueco

Un panel que no cabe a lo ancho **apila sus columnas** en vez de recortarse, y
el teclado de la calculadora se estrecha con la ventana en lugar de exigir su
ancho. Si al abrir un apartado ya no queda sitio para otra columna, se coloca
debajo del anterior antes que estrujar la calculadora.

### Corregido

- Al cambiar de figura o de método, las etiquetas del formulario anterior se
  seguían dibujando encima: `takeAt` las quita del layout, pero `deleteLater`
  no actúa hasta volver al bucle de eventos.
- El botón «Borrar variables» estaba duplicado en la calculadora y en la barra.

---

## 3.3.0

Unificación: los módulos dejan de ser islas.

### Barra de cálculo en todos los módulos

Ya no hace falta salir del módulo en el que se trabaja para hacer una cuenta
suelta. Si está resolviendo una ecuación trigonométrica y necesita saber cuánto
vale `5*sin(30)`, lo escribe en la barra inferior sin moverse.

Dos decisiones deliberadas:

- **Lo que se calcula ahí va al historial del módulo activo**, no al de la
  calculadora. Si trabaja en una figura geométrica, esa cuenta pertenece a ese
  problema, no a un cajón común.
- **Las variables son compartidas.** Al escribir `h = 5*sin(30)` puede usar `h`
  en los campos del módulo, en la calculadora o en una ecuación.

La barra admite lo mismo que la calculadora, incluidas unidades
(`3 km + 200 m`), y las flechas ↑ ↓ recorren lo ya calculado.

### Un solo historial

Cada uno de los dieciséis paneles llevaba su propio historial, de unos 350 px de
ancho: el mismo espacio y el mismo código repetidos dieciséis veces. Ahora hay
**uno solo**, en la ventana, que va mostrando el del módulo activo. Cada módulo
conserva su historial separado; lo que desaparece es la duplicación.

Eso libera cerca de un 28 % del ancho de la ventana en todos los módulos, que es
lo que deja sitio a la barra de cálculo.

### Unidades en los campos

Los campos numéricos aceptan ahora **unidades, variables y expresiones**:

| Escriba | Y funciona |
|---------|------------|
| `5 cm` y `50 mm` en la misma figura | se unifican solas |
| `sqrt(16)` | vale 4 |
| `radio` | usa la variable definida en la barra |

En Geometría, los resultados salen en la unidad que haya usado: un cilindro de
radio `5 cm` y altura `50 mm` da **392.699 cm³**, no «392.699 u³».

### Notas

Las variables guardan números sin unidad. Por eso `alto = 50 mm` se rechaza con
un aviso: si se admitiera, usar `alto` en un campo en centímetros valdría 50 cm
sin avisar, y un resultado erróneo en silencio es peor que una restricción.

### Corregido

- La unidad de referencia de una figura se elegía recorriendo un conjunto, cuyo
  orden en Python no está garantizado: el mismo cilindro podía dar el resultado
  en cm³ o en mm³ según la ejecución. Ahora se toma el primer campo en el orden
  en que aparecen.

---

## 3.2.0

Cuatro módulos nuevos: Axioma pasa de doce a **dieciséis**. Cubren lo que se
estudia después del cálculo básico, que era el hueco más grande que quedaba.

### Ecuaciones diferenciales

Resuelve EDOs de cualquier orden, con la notación de clase (`y'`, `y''`) o la de
Leibniz (`dy/dx`).

- **Clasifica** el tipo: separable, lineal, exacta, homogénea, Bernoulli,
  Euler-Cauchy, de coeficientes constantes…
- Da la **solución general** o la **particular** si se indican condiciones
  iniciales, y la **comprueba sustituyéndola** en la ecuación original.
- **Campo de direcciones** en las de primer orden: cada flecha marca la
  pendiente que tendría la solución al pasar por ese punto.
- **Sistemas** de hasta cuatro ecuaciones y resolución por **transformada de
  Laplace**.

### Transformadas

Laplace directa e inversa (con descomposición en fracciones simples), Fourier, y
**series de Fourier** con los coeficientes aₙ y bₙ, la detección de simetría par
o impar, y la gráfica que superpone la función con su serie truncada — donde se
ve el fenómeno de Gibbs. Incluye la tabla de transformadas usuales.

### Métodos numéricos

Raíces (bisección, Newton-Raphson, secante), integración (trapecio, Simpson),
interpolación (Lagrange, diferencias divididas) y EDOs (Euler, Runge-Kutta 4).

Todos muestran la **tabla de iteraciones** y la gráfica de convergencia: ver cómo
converge un método, o cómo no lo hace, es la mitad de lo que se estudia.

### Ajuste de curvas

Prueba los modelos lineal, cuadrático, cúbico, polinómico de grado n,
exponencial, logarítmico y potencial; **compara su r² y recomienda el mejor**,
listando aparte los que no se pueden aplicar y por qué.

### Otros cambios

- La navegación lateral se **agrupa por temas** (cálculo diario, álgebra,
  análisis, datos y geometría): con dieciséis módulos, una lista plana se leía
  mal y no cabía en pantalla.

### Corregido

- `analizar_datos` fallaba con decimales separados por comas y espacios
  (`1.5, 2.5`), que es justo lo que sale al pegar una columna de una hoja de
  cálculo. Ahora se distingue bien la coma decimal de la coma separadora.
- En los paneles de EDOs y de ajuste se veían campos que no correspondían al
  modo seleccionado: `currentIndexChanged` no se dispara al construir el panel
  con el índice ya en 0.

---

## 3.1.0

### Nuevo

**Resolución paso a paso.** Ya no sólo se da el resultado: se explica cómo se
llega a él.

- **Derivadas**: se recorre el árbol de la expresión nombrando la regla aplicada
  en cada nodo (producto, cadena, potencia, constante por función, derivada de
  cada función elemental).
- **Integrales**: se indica el método empleado (cambio de variable, integración
  por partes, reescritura previa) y se comprueba el resultado derivándolo.
- **Ecuaciones**: despeje razonado en las de primer grado; factorización,
  discriminante con su interpretación y fórmula en las de segundo. Se comprueba
  la solución sustituyéndola.
- **Sistemas**: método de Gauss con cada operación sobre las filas y la matriz
  redibujada después de cada paso.

**Aritmética con unidades en la calculadora.** `5 km + 300 m` da `5.3 km`, y
`20 °C a °F` da `68 °F`. Admite sumas y restas de la misma magnitud, producto y
división por un número, división entre magnitudes iguales, y conversión
explícita con `a`, `en`, `in`, `to` o `→`.

**Cálculo geométrico inverso.** «Sé que el área vale 50, ¿cuánto mide el lado?».
Disponible en las figuras cuyos datos son continuos.

**Historial con las flechas del teclado.** <kbd>↑</kbd> y <kbd>↓</kbd> recorren
las expresiones ya calculadas, como en una terminal.

**Distribución.**

- Icono propio, en la ventana, la barra de tareas y el ejecutable.
- Integración continua: las pruebas se ejecutan en Windows y Linux con Python
  3.10, 3.12 y 3.13.
- Ejecutable para Windows en la sección de *Releases*.

### Corregido

- La pestaña «Paso a paso» salía con el texto recortado: Qt calculaba el ancho
  sin tener en cuenta el relleno definido en la hoja de estilos.
- El ejecutable pesaba 343 MB porque PyInstaller arrastraba torch, scipy,
  transformers y otras bibliotecas que Axioma no usa, presentes en el entorno de
  desarrollo. Ahora se excluyen explícitamente.

### Notas

La aritmética con unidades **no** crea unidades derivadas (`10 km / 2 h`) ni suma
escalas afines de temperatura (`20 °C + 5 °C`), porque lo primero exigiría un
motor de análisis dimensional y lo segundo no significa nada. En ambos casos se
explica el motivo en lugar de dar un número incorrecto.

---

## 3.0.0

Reescritura completa. La aplicación pasa de siete ventanas sueltas a una sola
ventana con doce módulos, y la lógica de cálculo (`src/core`) queda separada de
la interfaz (`src/ui`), sin depender de PyQt.

### Módulos nuevos

Gráficas de funciones, cálculo (derivadas, integrales, límites, series),
matrices y álgebra lineal, estadística y distribuciones, y números complejos.

### Ampliaciones

- **Conversiones**: de 3 disciplinas y 15 magnitudes a **51 magnitudes y 555
  unidades**, con buscador y equivalencias simultáneas.
- **Geometría**: de 6 figuras a **61** (36 planas y 25 cuerpos), con vista previa
  2D y 3D embebida y las fórmulas aplicadas a la vista.
- **Calculadora**: trigonometría directa e inversa, hiperbólicas, logaritmos,
  memoria, modos DEG/RAD/GRAD, variables propias y vista previa del resultado.
- **Ecuaciones**: detección automática de la incógnita, sintaxis relajada,
  soluciones exactas, descarte de raíces espurias y gráfica.
- **Sistemas**: hasta 10 ecuaciones, clasificación por Rouché-Frobenius.
- **Bases**: negativos, decimales, prefijos `0x`/`0b`/`0o` y complemento a dos.
- **Combinatoria**: además del factorial, combinaciones, permutaciones,
  variaciones, doble factorial, subfactorial, Catalan, gamma y Stirling.
- Temas claro y oscuro, e historial con búsqueda y exportación a CSV/TXT.

### Corregido (respecto a la versión 1)

| Dónde | Problema |
|-------|----------|
| Conversiones | Se multiplicaba por la razón invertida: 1 km daba 0,001 m. Afectaba a **todas** las magnitudes. |
| Conversiones | La temperatura sólo funcionaba si uno de los extremos era kelvin. |
| Conversiones | La unidad `g/L` estaba definida como diccionario y fallaba siempre. |
| Calculadora | Usaba `eval()` sobre la entrada del usuario: ejecutaba código arbitrario. |
| Historial | Borraba por posición en la lista, no por identidad: con la lista filtrada eliminaba la entrada equivocada. |
| Historial | Escritura no atómica; se guardaba junto al ejecutable en lugar del perfil del usuario. |
| Ecuaciones | `UnboundLocalError` cuando no había soluciones; las raíces complejas hacían fallar el cálculo. |
| Sistemas | El parser manual daba signos incorrectos y no admitía incógnitas a la derecha, fracciones ni sistemas no cuadrados. |
| Geometría | No validaba valores negativos ni campos vacíos. |
| Bases | No admitía signo negativo ni parte fraccionaria. |
| Combinatoria | Volcaba enteros de miles de dígitos en una etiqueta, estirando la ventana. |
| Varios | El visualizador de figuras era código muerto que escribía un PNG en el directorio de trabajo. |
