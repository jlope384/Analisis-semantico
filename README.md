# Compiscript — Compilador a MIPS

Implementación del compilador de Compiscript con ANTLR4 y target Python3.
Cubre el análisis léxico, sintáctico y semántico, la generación de
código intermedio (TAC) y la generación de ensamblador MIPS, que se
ejecuta en el simulador MARS.

# Link al video:
https://drive.google.com/drive/folders/1oJakUhT_LeHLsataZ9m95zVwSX6Z9hN2?usp=sharing
   

Ver [Instrucciones.md](Instrucciones.md) para el enunciado completo de la tarea
y [ARCHITECTURE.md](ARCHITECTURE.md) para el detalle de la arquitectura,
[TAC.md](TAC.md) para la documentación del código intermedio y
[CODEGEN.md](CODEGEN.md) para la generación de MIPS (memoria, secuencia de
llamada, asignación de registros con `getReg` y runtime).

## Cómo ejecutar

Todo corre dentro de Docker (Java, ANTLR, Python y el simulador MARS ya
vienen en la imagen). Los comandos se ejecutan desde la raíz del repo.

**1. Construir la imagen y generar el parser** (una sola vez):

```bash
docker build --rm . -t csp-image
docker run --rm -v "$(pwd)/program":/program csp-image antlr -Dlanguage=Python3 Compiscript.g4
```

**2. Revisar un programa** (errores léxicos, sintácticos y semánticos):

```bash
docker run --rm -v "$(pwd)/program":/program csp-image python3 Driver.py examples/04_closures.cps
```

**3. Ver el código intermedio (TAC)** y la tabla de símbolos con direcciones:

```bash
docker run --rm -v "$(pwd)/program":/program csp-image python3 Driver.py examples/04_closures.cps --tac
docker run --rm -v "$(pwd)/program":/program csp-image python3 Driver.py examples/04_closures.cps --tac salida.tac --symbols
```

**4. Generar el ensamblador MIPS** (`--mips`):

```bash
docker run --rm -v "$(pwd)/program":/program csp-image python3 Driver.py examples/04_closures.cps --mips closures.asm
```

**5. Ejecutarlo en MARS** (modo consola):

```bash
docker run --rm -v "$(pwd)/program":/program csp-image mars closures.asm
```

Un error en tiempo de ejecución que nadie atrapa imprime
`Error en tiempo de ejecucion: <mensaje>` y termina con código de salida 1.
El `.asm` también se puede abrir en la interfaz gráfica de MARS
(https://github.com/dpetersanderson/MARS/releases): *Assemble* → *Run*.

Si el programa tiene errores, `Driver.py` los imprime, termina con código 1
y no genera ni el TAC ni el `.asm`.

**6. Correr la batería de tests** (incluye los que ejecutan el MIPS en MARS
y los ejemplos de `program/examples/`):

```bash
docker run --rm -v "$(pwd)/program":/program csp-image pytest
```

**Ejemplos.** `program/examples/` tiene programas representativos (`.cps`)
con su salida esperada (`.out`): expresiones, control de flujo, recursión,
closures, clases y herencia, arreglos, excepciones y un error no atrapado.
`tests/test_examples.py` compila cada uno, lo ejecuta en MARS y compara la
salida. Para agregar uno basta con poner el par `nombre.cps` / `nombre.out`.

**7. Desde VS Code.** Con la extensión instalada (ver
[Extensión de VS Code](#extensión-de-vs-code-editor)), abre un `.cps` y usa
la paleta de comandos (`Cmd+Shift+P` / `Ctrl+Shift+P`):

- **Compiscript: Compilar y mostrar codigo intermedio (TAC)**
- **Compiscript: Compilar a MIPS (.asm)**: guarda el `.asm` junto al `.cps`
- **Compiscript: Compilar y ejecutar en MARS**: además lo ejecuta en una
  terminal, por defecto con `docker run ... csp-image mars`

## Estructura del repositorio

```
program/
  Compiscript.g4        Gramática ANTLR (lexer + parser)
  Driver.py              Punto de entrada CLI: compila un .cps, reporta errores y opcionalmente
                          exporta el arbol (--tree), el TAC (--tac), la tabla de simbolos (--symbols)
                          y el ensamblador MIPS (--mips)
  compiler.py            Pipeline: parser -> analisis semantico -> generacion de TAC
  analyzer.py            Analisis semantico (Listener) + asignacion de direcciones
  tac_generator.py       Generacion de codigo de tres direcciones (Visitor)
  ir/                     Representacion intermedia: cuadruplos, temporales y etiquetas
  codegen/                Backend MIPS: liveness, asignacion de registros (getReg),
                          traduccion TAC -> MIPS, runtime y ejecucion en MARS
  lsp_server.py           Servidor LSP (pygls) que expone el analizador a un editor
  tree_export.py          Arbol de ANTLR -> dict JSON / grafo Graphviz DOT
  program.cps            Programa de ejemplo usado para pruebas manuales
  examples/               Programas .cps de ejemplo con su salida esperada (.out)
  semantic/               Paquete Python con la tabla de simbolos y el sistema de tipos
  tests/                  Bateria de tests (casos exitosos y fallidos por regla semantica)
  requirements.txt        Dependencias de Python para correr el servidor LSP en el host

vscode-extension/        Extension de VS Code (cliente LSP) que actua como el "IDE" del proyecto
ARCHITECTURE.md           Documentacion de arquitectura
```

## Entorno de desarrollo (Docker)

El proyecto se construye y ejecuta dentro de un contenedor Docker que trae Java
(requerido por la herramienta ANTLR y por MARS), el runtime de Python para ANTLR
y el simulador MIPS **MARS 4.5.1** (comando `mars`).

1. Construir la imagen:

   ```bash
   docker build --rm . -t csp-image
   ```

2. Levantar un contenedor interactivo con el directorio `program` montado:

   ```bash
   docker run --rm -ti -v "$(pwd)/program":/program csp-image
   ```

3. Dentro del contenedor, generar el lexer/parser a partir de la gramática:

   ```bash
   antlr -Dlanguage=Python3 Compiscript.g4
   ```

4. Ejecutar el analizador sobre el programa de ejemplo:

   ```bash
   python3 Driver.py program.cps
   ```

5. Generar el código intermedio (TAC) y ver la tabla de símbolos con
   direcciones y registros de activación:

   ```bash
   python3 Driver.py program.cps --tac              # a stdout
   python3 Driver.py program.cps --tac salida.tac   # a un archivo
   python3 Driver.py program.cps --symbols
   ```

6. Generar el ensamblador MIPS y ejecutarlo en MARS:

   ```bash
   python3 Driver.py program.cps --mips program.asm
   mars program.asm
   ```

   El `.asm` también se puede abrir en la interfaz gráfica de MARS
   (descargable de https://github.com/dpetersanderson/MARS/releases) para
   ejecutarlo paso a paso.

7. Correr la batería de tests (dentro del contenedor también se ejecutan
   los tests que corren el MIPS generado en MARS):

   ```bash
   pytest
   ```

Los archivos generados por ANTLR (`CompiscriptLexer.py`, `CompiscriptParser.py`, etc.)
no se versionan — se regeneran a partir de `Compiscript.g4` en cada build.

## Árbol sintáctico visual

`Driver.py` puede volcar el árbol sintáctico de un programa, ya sea como
JSON o como un grafo Graphviz DOT:

```bash
python3 Driver.py program.cps --tree tree.dot
dot -Tpng tree.dot -o tree.png   # requiere graphviz (brew install graphviz / apt install graphviz)
```

La misma representación (como JSON) es la que usa la extensión de VS Code
para el comando **"Compiscript: Mostrar árbol sintáctico"** (ver abajo).

## Extensión de VS Code (editor)

En vez de un IDE propio, el proyecto se usa desde VS Code vía una extensión
que conecta un servidor [LSP](https://microsoft.github.io/language-server-protocol/)
(`program/lsp_server.py`) al editor. Esto da errores semánticos subrayados
en vivo mientras se escribe, resaltado de sintaxis para `.cps`, y el panel
de árbol sintáctico mencionado arriba.

### 1. Preparar el entorno de Python (host, fuera de Docker)

El servidor LSP corre directamente en tu máquina (VS Code necesita
hablarle por stdio), así que necesita el parser ya generado y las
dependencias instaladas fuera del contenedor:

```bash
# 1. Generar el parser (usando el mismo Docker de siempre)
docker run --rm -v "$(pwd)/program":/program csp-image antlr -Dlanguage=Python3 Compiscript.g4

# 2. Crear un entorno virtual e instalar dependencias del servidor
cd program
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Instalar dependencias de la extensión

```bash
cd vscode-extension
npm install
```

### 3. Correr la extensión

1. Abre la carpeta `vscode-extension/` en VS Code.
2. Presiona `F5` (o "Run and Debug" → "Run Extension"). Se abre una nueva
   ventana de VS Code ("Extension Development Host") con la extensión
   cargada.
3. En esa ventana, abre la carpeta raíz de este repo y luego un archivo
   `.cps` (por ejemplo `program/program.cps`).
4. Si el intérprete de Python del paso 1 no es el `python3` por defecto
   de tu PATH, ajusta `compiscript.pythonPath` en la configuración de VS
   Code (Settings → busca "compiscript") para que apunte al `.venv` que
   creaste (p.ej. `program/.venv/bin/python3`).
5. Deberías ver errores semánticos subrayados en rojo al guardar. Corre
   el comando **"Compiscript: Mostrar árbol sintáctico"** (paleta de
   comandos, `Cmd+Shift+P` / `Ctrl+Shift+P`) para ver el árbol del
   archivo activo en un panel lateral.

Para compilar el archivo activo, corre **"Compiscript: Compilar y mostrar
codigo intermedio (TAC)"**. El TAC y la tabla de símbolos con direcciones
se abren en un documento al lado del editor. Si el programa tiene errores,
la extensión los indica y no genera el TAC.

Para generar el ensamblador, corre **"Compiscript: Compilar a MIPS
(.asm)"**: guarda `archivo.asm` junto al `.cps` y lo abre. **"Compiscript:
Compilar y ejecutar en MARS"** además lo ejecuta en una terminal de VS Code.
Por defecto usa el contenedor (`docker run ... csp-image mars archivo.asm`,
así que la imagen `csp-image` debe estar construida). Para usar MARS sin
Docker, cambia `compiscript.runCommand` a
`java -jar C:/ruta/Mars4_5.jar nc "${asm}"`.

Si algo se traba, **"Compiscript: Reiniciar servidor de análisis"**
reinicia el proceso del servidor sin cerrar VS Code.

## Estado actual

- [x] Gramática ANTLR del lenguaje (incluye `integer`, `float` y `string`).
- [x] Entorno Docker para generar el parser y correr el analizador.
- [x] Tabla de símbolos con ámbitos anidados (global, función, clase, bloque).
- [x] Visitor de análisis semántico: sistema de tipos, ámbitos, funciones, clases,
      control de flujo (`if`/`while`/`do-while`/`for`/`foreach`/`switch`,
      `break`/`continue`, código inalcanzable), constructores.
- [x] Batería de tests (pytest) por regla semántica.
- [x] Representación visual del árbol sintáctico (`--tree` en `Driver.py` +
      panel de VS Code).
- [x] Editor: extensión de VS Code con LSP en vez de un IDE propio.
- [x] Documentación de arquitectura (`ARCHITECTURE.md`).

### Fase de generación de código intermedio

- [x] Diseño del TAC en cuádruplos (`ir/tac.py`, documentado en `TAC.md`).
- [x] Tabla de símbolos con direcciones, tamaños, registros de activación,
      layout de objetos y vtables.
- [x] Asignación y reciclaje de temporales.
- [x] Generación de TAC: expresiones (con cortocircuito), asignaciones, control
      de flujo, `switch`, funciones y recursión, clases/objetos con despacho
      dinámico, arreglos, `foreach`, `try/catch`.
- [x] `--tac` y `--symbols` en `Driver.py`.
- [x] Tests del TAC (`tests/test_tac*.py`, `tests/test_memory_layout.py`, `tests/test_compiler.py`).
- [x] Comando **"Compiscript: Compilar y mostrar codigo intermedio (TAC)"** en la extensión de VS Code.

### Fase de generación de código MIPS

- [x] Bloques básicos, análisis de vida y siguiente uso (`codegen/liveness.py`).
- [x] Asignación de registros con `getReg`, descriptores y spill (`codegen/registers.py`).
- [x] Traducción TAC → MIPS: secuencia de llamada, objetos y vtables, arreglos,
      strings, floats, try/catch y errores en tiempo de ejecución.
- [x] Funciones anidadas (closures) con enlace de acceso.
- [x] `--mips` en `Driver.py`, ejecución en MARS y comandos en VS Code.
- [x] Tests: generación, ejecución en MARS, casos fallidos y ejemplos
      (`tests/test_mips_*.py`, `tests/test_examples.py`).
