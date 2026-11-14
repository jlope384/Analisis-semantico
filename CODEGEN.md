# Generación de código: TAC → MIPS

Este documento describe el backend del compilador, que traduce el código
de tres direcciones (ver [TAC.md](TAC.md)) a ensamblador **MIPS32** que
corre en el simulador **MARS 4.5**. Cubre la organización de la memoria,
la secuencia de llamada y retorno, el algoritmo de asignación de registros
(`getReg`), el runtime y cómo probarlo.

```bash
python3 Driver.py programa.cps --mips programa.asm   # genera el ensamblador
mars programa.asm                                    # lo ejecuta (dentro de Docker)
```

## 1. Organización

```
TACProgram ──> codegen/mips_generator.py ──> .asm
                   │  por cada función:
                   ├─ codegen/liveness.py    bloques básicos, vida de temporales, siguiente uso
                   ├─ codegen/registers.py   descriptores de registros y getReg()
                   └─ codegen/runtime.py     rutinas de soporte (strings, print, errores)
```

| Archivo | Qué hace |
|---|---|
| `codegen/liveness.py` | Parte cada función en bloques básicos, arma el grafo de flujo, calcula los temporales vivos a la salida de cada bloque y el **siguiente uso** de cada operando en cada instrucción. |
| `codegen/registers.py` | `RegisterAllocator`: descriptores de registro y de dirección, `get_reg()` (getReg), spills, y sincronización con memoria al final de cada bloque y antes de cada llamada. |
| `codegen/mips_generator.py` | `MIPSGenerator`: traduce cada cuádruplo, arma prólogo y epílogo y emite las secciones `.data` y `.text`. |
| `codegen/runtime.py` | Rutinas en ensamblador que se agregan a todo programa: concatenación y comparación de strings, impresión, lanzamiento de errores. |
| `codegen/simulator.py` | Ejecuta un `.asm` en MARS (lo usan los tests). |

El generador de TAC le pasa al backend, además del TAC, el registro de
activación de cada función (`frames`), su símbolo (`function_symbols`) y la
tabla nombre-en-el-TAC → símbolo de cada función (`names`). Así el backend
sabe la dirección y el tipo de cada operando sin volver a recorrer el árbol.

## 2. Memoria

```
              direcciones altas
 ┌─────────────────────────────┐
 │ pila  (crece hacia abajo)   │  $sp, $fp: marcos de las funciones
 │             ...             │
 │ heap  (crece hacia arriba)  │  objetos, arreglos y strings (syscall 9, sbrk)
 │ .data                       │  __globals (variables globales, vía $gp),
 │                             │  vtables, literales, datos del runtime
 │ .text                       │  main, funciones, runtime
 └─────────────────────────────┘
```

- **Globales**: un bloque `__globals` en `.data`. `main` carga su dirección
  en `$gp`, y una global con offset `k` se accede como `k($gp)`. El offset es
  el que asignó el análisis semántico (`--symbols`).
- **Locales, parámetros y temporales**: en el registro de activación de su
  función, en `offset($fp)`. El temporal `tN` vive en
  `tamaño_de_variables + 8·(N−1)`.
- **Objetos**: `[ vtable | campos heredados | campos propios ]`, con los
  offsets de `ClassSymbol.compute_layout`. `new C` reserva el tamaño de la
  clase y guarda `__vt_C` en el offset 0.
- **Vtables**: `__vt_C: .word fn_C__m1, fn_B__m2, ...`, un slot por método en
  el orden de `ClassSymbol.vtable()`.
- **Arreglos**: `[ longitud | elem 0 | elem 1 | ... ]`, 4 bytes por elemento.
  `a[i]` verifica que `a` no sea null y que `0 ≤ i < longitud`.
- **Strings**: punteros a cadenas terminadas en 0. Los literales van en
  `.data`, y las concatenaciones crean una cadena nueva en el heap.
- **Valores**: `integer` y `boolean` son una palabra (32 bits), `float` es
  precisión simple (`$f`), y las referencias son direcciones de 32 bits.
  Las áreas de memoria conservan los tamaños de la tabla de símbolos (8 bytes
  para float y referencias), así que cada valor cabe en su espacio.

## 3. Secuencia de llamada y retorno

Los argumentos se pasan **por la pila**, una palabra cada uno, en el orden
del `param`. El resultado vuelve en `$v0` (o en `$f0` si es `float`). Un
método recibe `this` como primer argumento.

**Llamador** (`param x` … `call f, n`):

```mips
        addiu $sp, $sp, -4        # param x  (uno por argumento)
        sw    $t0, 0($sp)
        ...                       # se guardan en memoria los valores vivos en $t
        jal   fn_f                # (o jalr $v1 en una llamada por la vtable)
        addiu $sp, $sp, 4n        # quita los argumentos
        move  $t0, $v0            # resultado
```

**Llamado** (prólogo y epílogo de `fn_f`, con marco de `F` bytes):

```mips
fn_f:   addiu $sp, $sp, -F
        sw    $ra, F-4($sp)
        sw    $fp, F-8($sp)
        sw    $s0, k($sp)         # solo los $s que la función usa
        move  $fp, $sp
        lw    $a2, F+4(n-1-i)($fp)  # copia el argumento i a su lugar
        sw    $a2, offset_i($fp)    # en el registro de activación
        ...
ret_fn_f:
        lw    $s0, k($fp)
        lw    $ra, F-4($fp)
        move  $sp, $fp
        lw    $fp, F-8($sp)
        addiu $sp, $sp, F
        jr    $ra
```

Marco resultante, desde `$fp` hacia direcciones altas:

```
 0($fp)                                     F($fp)
 ┌──────────────────────────────┬───────────┬────────┬─────┬───────────────────────┐
 │ registro de activación (TAC) │ $s usados │ $fp ant│ $ra │ argumentos (llamador) │
 │ params | locales | temporales│           │        │     │ arg n-1 ... arg 0     │
 └──────────────────────────────┴───────────┴────────┴─────┴───────────────────────┘
```

Todo acceso a variables es relativo a `$fp`, así que apilar argumentos
(`$sp` cambia) o hacer spill en medio de una llamada no altera ninguna
dirección. `return x` deja el valor en `$v0`/`$f0` y salta al epílogo.
Al terminar, `main` hace `syscall 10`.

## 4. Asignación de registros (`getReg`)

### Clases de registros

| Registros | Uso | Quién los preserva |
|---|---|---|
| `$t0–$t9` | temporales del TAC | llamador (se guardan antes de `jal` si siguen vivos) |
| `$s0–$s7` | variables (locales, parámetros, `this`, globales) | llamado (prólogo/epílogo) |
| `$f4–$f11`, `$f16–$f19` | temporales `float` | llamador |
| `$f20–$f31` | variables `float` | llamado |
| `$a0–$a3`, `$v0`, `$v1`, `$f0–$f3`, `$f12` | scratch: literales, argumentos de syscall y del runtime, resultados | — |
| `$gp`, `$sp`, `$fp`, `$ra` | globales, pila, marco, retorno | — |

`$at` queda libre para las pseudo-instrucciones del ensamblador.

### Análisis previo (`liveness.py`)

1. **Bloques básicos.** Una etiqueta empieza un bloque, y un salto o un
   `return` lo termina.
2. **Grafo de flujo.** Un bloque tiene como sucesores el destino de su salto
   y el bloque siguiente. Los bloques dentro de un `try` también tienen como
   sucesor el bloque de su `catch`, porque un error puede saltar ahí desde
   cualquier punto.
3. **Vida de temporales.** Se usa el análisis de flujo hacia atrás clásico,
   `in = use ∪ (out − def)` y `out = ∪ in(sucesores)`, iterado hasta un
   punto fijo. Las variables se consideran siempre vivas al salir de un
   bloque.
4. **Siguiente uso.** Cada bloque se recorre de abajo hacia arriba, empezando
   con los valores vivos a la salida. Así se sabe, en cada instrucción, cuándo
   se vuelve a usar cada operando, o si ya está muerto.

### Descriptores

- **Descriptor de registro**: el valor que tiene cada registro.
- **Descriptor de dirección**: el registro donde está cada valor (su lugar
  en memoria siempre existe).
- **Conjunto sucio**: los valores cuyo registro es más nuevo que su memoria.

### `get_reg(x)`

1. Si `x` ya está en un registro, se usa ese.
2. Si no, se toma un registro libre de su clase (`$t` o `$s`, entero o float).
3. Si no hay ninguno libre, se busca uno cuyo valor esté **muerto** (sin
   siguiente uso) y se reutiliza sin guardarlo.
4. Si tampoco, se elige el registro cuyo valor se usa **más lejos** en el
   futuro, prefiriendo uno limpio. Si está sucio se hace **spill**
   (`sw reg, lugar  # spill x`) antes de reutilizarlo.

Los registros que ya usa la instrucción actual se bloquean para que no se
elijan como víctima. Si `x` se va a leer se carga de memoria (`lw`), y si se
va a escribir solo se marca sucio. Después de cada instrucción se liberan
los registros de temporales muertos.

### Sincronización con memoria

| Punto | Acción |
|---|---|
| Fin de bloque básico | Guarda los valores sucios que siguen vivos y vacía los descriptores. |
| Antes de `jal`/`jalr` | Guarda los valores sucios vivos, olvida `$t`/`$f` temporales y globales (el llamado puede cambiarlos) y conserva las locales en `$s`. |
| Antes de una instrucción que puede lanzar un error, en una función con `try` | Guarda los valores sucios vivos, porque el `catch` los lee de memoria. |

Ejemplo (`fact`): `n` queda en `$s0` durante la llamada recursiva y no se
vuelve a cargar, porque el llamado preserva `$s0`.

```mips
        # t1 = n - 1
        lw    $s0, 0($fp)
        addiu $t0, $s0, -1
        # param t1
        addiu $sp, $sp, -4
        sw    $t0, 0($sp)
        # t1 = call fact, 1
        jal   fn_fact
        addiu $sp, $sp, 4
        move  $t0, $v0
        # t1 = n * t1
        mul   $t0, $s0, $t0
```

## 5. Traducción de cada instrucción

| TAC | MIPS |
|---|---|
| `x = y op z` (integer) | `addu`/`subu`/`mul`, `div`+`mflo`/`mfhi` (con chequeo de cero), `slt`/`sle`/`sgt`/`sge`/`seq`/`sne`; `addiu` si `z` es una constante pequeña |
| `x = y op z` (float) | `add.s`/`sub.s`/`mul.s`/`div.s`; comparaciones con `c.lt.s`/`c.le.s`/`c.eq.s` + `bc1t`; un `integer` se promueve con `mtc1` + `cvt.s.w` |
| `x = y + z` (string) | `jal __concat` |
| `x = y == z` (string) | `jal __streq` (compara contenido) |
| `x = -y`, `x = !y` | `subu x, $zero, y` / `neg.s`, `xori x, y, 1` |
| `if x goto L`, `ifFalse x goto L`, `goto L` | `bnez`, `beqz`, `j` |
| `x = new C, k` | `sbrk(k)` y `sw __vt_C, 0(x)` |
| `x = new_array n` | `sbrk(4 + 4n)` y la longitud en el offset 0 |
| `x = a[i]`, `a[i] = x` | chequeo de null y de límites, `lw`/`sw 4+4i(a)` |
| `x = o.f`, `o.f = x` | chequeo de null, `lw`/`sw offset_f(o)` |
| `x = o.vtable`; `x = x[k]`; `call x, n` | `lw x, 0(o)`; `lw x, 4k(x)`; `jalr` |
| `x = len a` | `lw x, 0(a)` |
| `print x` | syscall 1 (integer), 2 (float), `__print_str`, `__print_bool`, y un salto de línea |
| `try_begin L` / `try_end` | apila/desapila `(L, $sp, $fp)` en la pila de manejadores |
| `x = catch` | `lw x, __exception` (el mensaje del error) |

## 6. Errores en tiempo de ejecución y try/catch

El runtime mantiene una **pila de manejadores** (`__handlers`, hasta 64
`try` anidados). `try_begin L` apila la dirección del catch con los `$sp` y
`$fp` de ese momento. Un error (índice fuera de rango, acceso a null,
división entre cero) llama a `__raise` con su mensaje:

- Si hay manejador, lo desapila, restaura `$sp` y `$fp` (esto descarta los
  marcos de las funciones que se llamaron dentro del try), guarda el mensaje
  en `__exception` y salta al catch.
- Si no hay, imprime `Error en tiempo de ejecucion: <mensaje>` y termina con
  código de salida 1.

`break`, `continue` y `return` dentro de un `try` emiten `try_end` antes de
saltar (en el generador de TAC), así que la pila de manejadores siempre
queda balanceada. La variable del `catch` es de tipo `string`.

## 7. Cómo probarlo

El `Dockerfile` instala MARS 4.5.1 y deja el comando `mars` (consola, sin
interfaz gráfica):

```bash
docker build --rm . -t csp-image
docker run --rm -v "$(pwd)/program":/program csp-image python3 Driver.py program.cps --mips program.asm
docker run --rm -v "$(pwd)/program":/program csp-image mars program.asm
```

También se puede abrir el `.asm` en la interfaz gráfica de MARS (Assemble →
Run) para ver los registros y la memoria paso a paso.

### Batería de tests

```bash
docker run --rm -v "$(pwd)/program":/program csp-image pytest
```

| Archivo | Qué prueba |
|---|---|
| `tests/test_liveness.py` | bloques básicos, sucesores, vida de temporales, siguiente uso, flujo hacia el catch |
| `tests/test_mips_codegen.py` | prólogo/epílogo, paso de argumentos, $s guardados, vtable, clases de registros, reutilización de registros, spill bajo presión, floats, errores (closures, programas inválidos) |
| `tests/test_mips_execution.py` | **se compila y ejecuta en MARS**: aritmética, floats, lógicos con cortocircuito, ternario, strings, bucles, switch, recursión, más de 4 argumentos, llamadas anidadas, valores que sobreviven a llamadas, globales, presión de registros (spill), clases con herencia y despacho dinámico, arreglos, ordenamiento, try/catch (también a través de funciones), errores no capturados |

Los tests que ejecutan MARS se saltan automáticamente si el simulador no
está instalado (por ejemplo, al correr `pytest` fuera de Docker). Para
correrlos fuera de Docker, define `MARS_JAR` con la ruta a `Mars4_5.jar` y
ten `java` en el `PATH`.

## 8. Supuestos y limitaciones

1. **Closures.** Una función anidada que lee variables locales de la función
   que la contiene no se puede traducir (haría falta un *access link*). El
   compilador lo reporta como error de generación de código. Las funciones
   anidadas que solo usan sus propias variables y las globales sí funcionan.
2. **Float en precisión simple** (`.s`). MARS imprime el valor con la
   representación de Java (`4.0`, `2.5`).
3. **Strings inmutables.** Cada concatenación reserva memoria nueva, y el
   heap nunca se libera (no hay recolector de basura).
4. **Pila de manejadores** de 64 entradas: más de 64 `try` anidados a la vez
   desbordan el área.
5. **Llamadas por la vtable**: se usa el tipo del método en el tipo estático
   del receptor para convertir argumentos `integer` → `float`. Se asume que
   un método que sobrescribe a otro tiene la misma firma.
