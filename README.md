# Compiscript — Análisis Semántico

Implementación del analizador léxico, sintáctico y semántico de Compiscript
(fase de Análisis Semántico) usando ANTLR4 con target Python3.

Ver [Instrucciones.md](Instrucciones.md) para el enunciado completo de la tarea.

## Estructura del repositorio

```
program/
  Compiscript.g4        Gramática ANTLR (lexer + parser)
  Driver.py              Punto de entrada: parsea un archivo .cps y corre el analisis semantico
  program.cps            Programa de ejemplo usado para pruebas manuales
  semantic/               Paquete Python con la tabla de simbolos y el visitor de reglas semanticas
  tests/                  Bateria de tests (casos exitosos y fallidos por regla semantica)
```

## Entorno de desarrollo (Docker)

El proyecto se construye y ejecuta dentro de un contenedor Docker que trae Java
(requerido por la herramienta ANTLR) y el runtime de Python para ANTLR.

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

5. Correr la batería de tests:

   ```bash
   pytest
   ```

Los archivos generados por ANTLR (`CompiscriptLexer.py`, `CompiscriptParser.py`, etc.)
no se versionan — se regeneran a partir de `Compiscript.g4` en cada build.

## Estado actual

- [x] Gramática ANTLR del lenguaje.
- [x] Entorno Docker para generar el parser y correr el analizador.
- [ ] Tabla de símbolos.
- [ ] Visitor de análisis semántico (sistema de tipos, ámbitos, funciones, clases, control de flujo).
- [ ] Batería de tests.
- [ ] IDE.
