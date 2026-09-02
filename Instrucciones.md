
# 🧪 Compiscript

## 📋 Descripción General

Este lenguaje se encuentra basado en Typescript, por lo que representa un subset del mismo, con algunas diferencias.

---

## 🧰 Instrucciones de Configuración

1. **Construir y Ejecutar el Contenedor Docker:** Desde el directorio raíz, ejecuta el siguiente comando para construir la imagen y lanzar un contenedor interactivo:

   ```bash
   docker build --rm . -t csp-image && docker run --rm -ti -v "$(pwd)/program":/program csp-image
   ```
2. **Entender el Entorno**

   - El directorio `program` se monta dentro del contenedor.
   - Este contiene la **gramática de ANTLR de Compiscript y una versión en BNF**, un archivo `Driver.py` (punto de entrada principal) y un archivo `program.cps` (entrada de prueba con la extensión de archivos de Compiscript).
3. **Generar Archivos de Lexer y Parser:** Dentro del contenedor, compila la gramática ANTLR a Python con:

   ```bash
   antlr -Dlanguage=Python3 Compiscript.g4
   ```
4. **Ejecutar el Analizador**
   Usa el driver para analizar el archivo de prueba:

   ```bash
   python3 Driver.py program.cps
   ```

   - ✅ Si el archivo es sintácticamente correcto, **no se mostrará ningún resultado**.
   - ❌ Si existen errores, ANTLR los mostrará en la consola.

---

## 🧩 Características del Lenguaje

Compiscript soporta los siguientes conceptos fundamentales:

### ✅ Tipos de Datos

```cps
let a: integer = 10;
let b: string = "hola";
let c: boolean = true;
let d = null;
```

### ✅ Literales

```cps
123          // integer
"texto"      // string
true, false  // boolean
null         // nulo
```

### ✅ Expresiones Aritméticas y Lógicas

```cps
let x = 5 + 3 * 2;
let y = !(x < 10 || x > 20);
```

### ✅ Precedencia y Agrupamiento

```cps
let z = (1 + 2) * 3;
```

### ✅ Declaración y Asignación de Variables

```cps
let nombre: string;
nombre = "Compiscript";
```

### ✅ Constantes (`const`)

```cps
const PI: integer = 314;
```

### ✅ Funciones y Parámetros

```cps
function saludar(nombre: string): string {
  return "Hola " + nombre;
}
```

### ✅ Expresiones de Llamada

```cps
let mensaje = saludar("Mundo");
```

### ✅ Acceso a Propiedades (`.`)

```cps
print(dog.nombre);
```

### ✅ Acceso a Elementos de Arreglo (`[]`)

```cps
let lista = [1, 2, 3];
print(lista[0]);
```

### ✅ Arreglos

```cps
let notas: integer[] = [90, 85, 100];
let matriz: integer[][] = [[1, 2], [3, 4]];
```

### ✅ Funciones como Closures

```cps
function crearContador(): integer {
  function siguiente(): integer {
    return 1;
  }
  return siguiente();
}
```

### ✅ Clases y Constructores

```cps
class Animal {
  let nombre: string;

  function constructor(nombre: string) {
    this.nombre = nombre;
  }

  function hablar(): string {
    return this.nombre + " hace ruido.";
  }
}
```

### ✅ Herencia

```cps
class Perro : Animal {
  function hablar(): string {
    return this.nombre + " ladra.";
  }
}
```

### ✅ `this`

```cps
this.nombre = "Firulais";
```

### ✅ Instanciación con `new`

```cps
let perro: Perro = new Perro("Toby");
```

### ✅ Bloques y Ámbitos

```cps
{
  let x = 42;
  print(x);
}
```

### ✅ Control de Flujo

#### `if` / `else`

```cps
if (x > 10) {
  print("Mayor a 10");
} else {
  print("Menor o igual");
}
```

#### `while`

```cps
while (x < 5) {
  x = x + 1;
}
```

#### `do-while`

```cps
do {
  x = x - 1;
} while (x > 0);
```

#### `for`

```cps
for (let i: integer = 0; i < 3; i = i + 1) {
  print(i);
}
```

#### `foreach`

```cps
foreach (item in lista) {
  print(item);
}
```

#### `break` / `continue`

```cps
foreach (n in notas) {
  if (n < 60) continue;
  if (n == 100) break;
  print(n);
}
```

### ✅ `switch / case`

```cps
switch (x) {
  case 1:
    print("uno");
  case 2:
    print("dos");
  default:
    print("otro");
}
```

### ✅ `try / catch`

```cps
try {
  let peligro = lista[100];
} catch (err) {
  print("Error atrapado: " + err);
}
```

### ✅ `return`

```cps
function suma(a: integer, b: integer): integer {
  return a + b;
}
```

### ✅ Recursión

```cps
function factorial(n: integer): integer {
  if (n <= 1) return 1;
  return n * factorial(n - 1);
}
```

---

## 📦 Extensión de Archivo

Todos los archivos fuente de Compiscript deben usar la extensión:

```bash
program.cps
```

# 🧪 Fase de Compilación: Análisis Semántico

## 📋 Descripción General

En esta fase de compilación, deberán de implementar el análisis semántico para un lenguaje denomidado: Compiscript.

* Lea atentamente el README.md en este directorio, en dónde encotrará las generalidades del lenguaje.
* En el directorio ``program`` encontrará la gramática de este lenguaje en ANTLR y en BNF. Se le otorga un playground similar a los laboratorios para que usted pueda experimentar inicialmente.
* **Modalidad: Grupos de 3 integrantes.**

## 📋 Requerimientos

1. **Crear un analizador sintáctico utilizando ANTLR** o cualquier otra herramienta similar de su elección.
   * Se recomienda usar ANTLR dado que es la herramienta que se utiliza en las lecciones del curso, pero puede utilizar otro Generador de Parsers.
2. Añadir **acciones/reglas semánticas** en este analizador sintáctico y **construir un  ́****arbol sintáctico, con una representación visual****.**
   1. **Sistema de Tipos**
      * 🟠 Verificación de tipos en operaciones aritméticas (`+`, `-`, `*`, `/`) — los operandos deben ser de tipo `integer` o `float`.
      * 🟠 Verificación de tipos en operaciones lógicas (`&&`, `||`, `!`) — los operandos deben ser de tipo `boolean`.
      * 🟠 Compatibilidad de tipos en comparaciones (`==`, `!=`, `<`, `<=`, `>`, `>=`) — los operandos deben ser del mismo tipo compatible.
      * 🟠 Verificación de tipos en asignaciones — el tipo del valor debe coincidir con el tipo declarado de la variable.
      * 🟠 Inicialización obligatoria de constantes (`const`) en su declaración.
      * 🟠 Verificación de tipos en listas y estructuras (si se soportan más adelante).
   2. **Manejo de Ámbito**
      * 🟠 Resolución adecuada de nombres de variables y funciones según el ámbito local o global.
      * 🟠 Error por uso de variables no declaradas.
      * 🟠 Prohibir redeclaración de identificadores en el mismo ámbito.
      * 🟠 Control de acceso correcto a variables en bloques anidados.
      * 🟠 Creación de nuevos entornos de símbolo para cada función, clase y bloque.
   3. **Funciones y Procedimientos**
      * 🟠 Validación del número y tipo de argumentos en llamadas a funciones (coincidencia posicional).
      * 🟠 Validación del tipo de retorno de la función — el valor devuelto debe coincidir con el tipo declarado.
      * 🟠 Soporte para funciones recursivas — verificación de que pueden llamarse a sí mismas.
      * 🟠 Soporte para funciones anidadas y closures — debe capturar variables del entorno donde se definen.
      * 🟠 Detección de múltiples declaraciones de funciones con el mismo nombre (si no se soporta sobrecarga).
   4. **Control de Flujo**
      * 🟠 Las condiciones en `if`, `while`, `do-while`, `for`, `switch` deben evaluar expresiones de tipo `boolean`.
      * 🟠 Validación de que se puede usar `break` y `continue` sólo dentro de bucles.
      * 🟠 Validación de que el `return` esté dentro de una función (no fuera del cuerpo de una función).
   5. **Clases y Objetos**
      * 🟠 Validación de existencia de atributos y métodos accedidos mediante `.` (dot notation).
      * 🟠 Verificación de que el constructor (si existe) se llama correctamente.
      * 🟠 Manejo de `this` para referenciar el objeto actual (verificar ámbito).
   6. **Listas y Estructuras de Datos**
      * 🟠 Verificación del tipo de elementos en listas.
      * 🟠 Validación de índices (acceso válido a listas).
   7. **Generales**
      * 🟠 Detección de código muerto (instrucciones después de un `return`, `break`, etc.).
      * 🟠 Verificación de que las expresiones tienen sentido semántico (por ejemplo, no multiplicar funciones).
      * 🟠 Validación de declaraciones duplicadas (variables, parámetros).
3. Implementar la recorrida de este árbol utilizando ANTLR Listeners o Visitors para evaluar las reglas semánticas que se ajusten al lenguaje.
4. **Para los puntos anteriores, referentes a las reglas semánticas, deberá de escribir una batería de tests para validar casos exitosos y casos fallidos en cada una de las reglas mencionadas.**
   * Al momento de presentar su trabajo, esta batería de tests debe estar presente y será tomada en cuenta para validar el funcionamiento de su compilador.
5. Construir una **tabla de símbolos** que interactue con cada fase de la compilación, incluyendo las fases mencionadas anteriormente. Esta tabla debe considerar el **manejo de entornos** y almacenar toda la información necesaria para esta y futuras fases de compilación.
6. Deberá **desarrollar un IDE** que permita a los usuarios escribir su propio código y compilarlo.
7. Deberá crear **documentación asociada a la arquitectura de su implementación** y **documentación de las generalidades de cómo ejecutar su compilador**.
8. Entregar su repositorio de GitHub.
   * Se validan los commits y contribuciones de cada integrante, no se permite "compartir" commits en conjunto, debe notarse claramente qué porción de código implementó cada integrante.

## 📋 Ponderación

| Componente                                                                                   | Puntos          |
| -------------------------------------------------------------------------------------------- | --------------- |
| IDE                                                                                          | 15 puntos       |
| Analizador Sintáctico y Semántico con validación de reglas semánticas y sistema de tipos | 60 puntos       |
| Tabla de símbolos                                                                           | 25 puntos       |
| **Total**                                                                                   | **100 puntos** |