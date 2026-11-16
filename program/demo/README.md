# Demo para la presentación

Programas para mostrar el compilador en vivo, de lo que funciona a cada tipo de error.

| Carpeta | Qué muestra | Resultado esperado |
|---|---|---|
| `1_correctos/` | llamadas y retornos, `getReg`/spill, clases y vtable, closures, arreglos y try/catch | compila y corre en MARS |
| `2_errores_sintacticos/` | `;`, `)` o `}` faltantes, expresión incompleta | error de sintaxis con línea y columna |
| `3_errores_semanticos/` | tipos, variable no declarada, constante, argumentos, `return`/`break`, redeclaración, miembro inexistente | error semántico, no se genera MIPS |
| `4_errores_ejecucion/` | índice fuera de rango, división entre cero, acceso a `null` | compila, pero MARS termina con error y código 1 |

## Cómo correrlo

Desde la raíz del repo:

```bash
# todo
docker run --rm -v "$(pwd)/program":/program csp-image sh demo/correr_demo.sh

# una carpeta o un archivo
docker run --rm -v "$(pwd)/program":/program csp-image sh demo/correr_demo.sh demo/3_errores_semanticos
docker run --rm -v "$(pwd)/program":/program csp-image sh demo/correr_demo.sh demo/1_correctos/03_clases.cps
```

Para ver las fases intermedias de un programa:

```bash
docker run --rm -v "$(pwd)/program":/program csp-image python3 Driver.py demo/1_correctos/01_llamadas_y_retornos.cps --tac
docker run --rm -v "$(pwd)/program":/program csp-image python3 Driver.py demo/1_correctos/01_llamadas_y_retornos.cps --mips
```

En VS Code, abrir cualquier `.cps` de aquí muestra los errores subrayados, y los
comandos **Compilar a MIPS** y **Compilar y ejecutar en MARS** funcionan igual.

## Orden sugerido

1. `1_correctos/01_llamadas_y_retornos.cps` con `--mips`: prólogo, epílogo y paso de argumentos.
2. `1_correctos/02_registros_y_spill.cps` con `--mips`: uso de `$t`/`$s` y spill a la pila.
3. El resto de `1_correctos/` corriendo en MARS.
4. `2_errores_sintacticos/`, `3_errores_semanticos/` y `4_errores_ejecucion/`.
