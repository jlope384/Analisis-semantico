"""Casos fallidos de la generacion de codigo:

1. Programas invalidos: el compilador los rechaza con un error semantico y no
   genera ni TAC ni MIPS.
2. Errores en tiempo de ejecucion en MARS que nadie atrapa: el programa
   imprime lo que alcanzo a imprimir, luego
   `Error en tiempo de ejecucion: <mensaje>`, y termina con codigo 1.

Compiscript no tiene `throw`: un error "lanzado sin catch" es un error del
runtime que se propaga sin encontrar un manejador (desde funciones anidadas,
desde dentro de un catch o despues de que el try termino).
"""

import pytest

from compiler import compile_source
from codegen import simulator
from Driver import main as driver_main


# --- 1. programas invalidos: no se genera MIPS ----------------------------------

INVALID_PROGRAMS = [
    ('let a: integer = "x";', "no se puede inicializar 'a'"),
    ("print(y);", "variable 'y' no declarada"),
    ("function f(a: integer): integer { return a; } print(f(1, 2));", "se esperaban 1 argumento(s)"),
    ('function f(): integer { return "s"; }', "debe retornar 'integer'"),
    ("function f(): integer { let x: integer = 1; }", "no tiene ninguna sentencia 'return'"),
    ("break;", "'break' solo puede usarse"),
    ("let a: integer = 1; a();", "no se puede invocar"),
    ("class A {} let a: A = new A(); print(a.nada);", "'nada' no es un miembro"),
    ("const c: integer = 1; c = 2;", "es una constante"),
    ("let a: integer = 1; let a: integer = 2;", "ya fue declarado"),
    ("if (1) { print(1); }", "debe ser boolean"),
    ('let xs: integer[] = [1, "a"];', "mismo tipo"),
    ("function f(): integer { return 1; print(2); }", "codigo inalcanzable"),
    ("print(this);", "'this' solo puede usarse"),
    ("let b: boolean = 1 + true;", "no admite operandos"),
    # funciones anidadas: la interna no existe fuera de la externa
    ("""function outer(): integer {
          function inner(): integer { return 1; }
          return inner();
        }
        print(inner());""", "no declarada"),
    # error dentro de una funcion anidada: tampoco se genera nada
    ("""function outer(): integer {
          let x: integer = 1;
          function inner(): string { return x; }
          return 0;
        }""", "debe retornar 'string'"),
]


@pytest.mark.parametrize("source, message", INVALID_PROGRAMS)
def test_invalid_program_fails_before_generating_mips(source, message):
    result = compile_source(source)
    assert result.errors, "se esperaba un error semantico"
    assert any(message in e for e in result.errors), result.errors
    assert result.tac is None
    assert result.mips is None


def test_driver_reports_error_and_writes_no_assembly(tmp_path, capsys):
    source = tmp_path / "malo.cps"
    source.write_text('let a: integer = "hola";\nprint(a);\n', encoding="utf-8")
    output = tmp_path / "malo.asm"
    assert driver_main(str(source), mips_output=str(output)) == 1
    assert not output.exists()
    assert "no se puede inicializar" in capsys.readouterr().out


def test_syntax_error_produces_no_mips():
    result = compile_source("let x: integer = ;")
    assert result.errors
    assert result.mips is None


# --- 2. errores en tiempo de ejecucion sin manejador ---------------------------

needs_mars = pytest.mark.skipif(not simulator.is_available(), reason="MARS no esta instalado")

INDEX = "indice fuera de rango"
NULL = "acceso a una referencia null"
DIV = "division entre cero"

RUNTIME_ERRORS = {
    "indice_mayor_que_la_longitud": ("let xs: integer[] = [1, 2]; print(xs[2]);", INDEX),
    "indice_negativo": ("let xs: integer[] = [1, 2]; let i: integer = -1; print(xs[i]);", INDEX),
    "escritura_fuera_de_rango": ("let xs: integer[] = [1]; xs[1] = 5;", INDEX),
    "division_entre_cero": ("let a: integer = 7; let b: integer = 0; print(a / b);", DIV),
    "modulo_entre_cero": ("let a: integer = 7; let b: integer = 0; print(a % b);", DIV),
    "lectura_de_campo_null": ("class A { let v: integer = 1; } let a: A = null; print(a.v);", NULL),
    "escritura_de_campo_null": ("class A { let v: integer = 1; } let a: A = null; a.v = 2;", NULL),
    "metodo_sobre_null": (
        "class A { let v: integer = 3; function f(): integer { return this.v; } } "
        "let a: A = null; print(a.f());", NULL),
    "metodo_virtual_sobre_null": (
        "class A { function f(): integer { return 1; } } "
        "class B : A { function f(): integer { return 2; } } "
        "let a: A = null; print(a.f());", NULL),
    "arreglo_null": ("let xs: integer[] = null; print(xs[0]);", NULL),
    "foreach_sobre_null": ("let xs: integer[] = null; foreach (x in xs) { print(x); }", NULL),
    # el error sale de varias funciones sin encontrar manejador
    "propagado_desde_funciones": ("""
        function c(xs: integer[]): integer { return xs[10]; }
        function b(xs: integer[]): integer { return c(xs) + 1; }
        function a(xs: integer[]): integer { return b(xs) + 1; }
        print(a([1, 2, 3]));""", INDEX),
    # error dentro de una funcion anidada (closure)
    "desde_funcion_anidada": ("""
        function outer(): integer {
          let d: integer = 0;
          function inner(n: integer): integer { return n / d; }
          return inner(5);
        }
        print(outer());""", DIV),
    # el catch atrapa el primero, pero un error dentro del catch ya no tiene manejador
    "error_dentro_del_catch": ("""
        let xs: integer[] = [1];
        try { print(xs[5]); } catch (e) { print(e); print(1 / 0); }""", DIV),
    # el try ya termino: su manejador se quito de la pila
    "despues_de_cerrar_el_try": ("""
        let xs: integer[] = [1];
        try { print(xs[0]); } catch (e) { print("no"); }
        print(xs[3]);""", INDEX),
    # el manejador de una funcion que ya retorno no atrapa errores posteriores
    "despues_de_retornar_de_un_try": ("""
        function safe(xs: integer[], i: integer): integer {
          try { return xs[i]; } catch (e) { return -1; }
        }
        let xs: integer[] = [4];
        print(safe(xs, 9));
        print(xs[9]);""", INDEX),
}


def _run(source: str):
    result = compile_source(source)
    assert result.errors == []
    return simulator.run_mips(result.mips)


@needs_mars
@pytest.mark.parametrize("name", sorted(RUNTIME_ERRORS))
def test_uncaught_runtime_error_prints_message_and_exits_with_code_1(name):
    body, message = RUNTIME_ERRORS[name]
    execution = _run(f'print("inicio");\n{body}\nprint("fin");')
    lines = [l.strip() for l in execution.output.splitlines() if l.strip()]
    assert execution.exit_code == 1, execution.output
    assert lines[0] == "inicio"
    assert lines[-1] == f"Error en tiempo de ejecucion: {message}"
    assert "fin" not in lines
    # el error lo reporta el runtime, no MARS
    assert "Runtime exception" not in execution.output


@needs_mars
def test_output_before_the_error_is_kept_in_order():
    execution = _run("""
        let xs: integer[] = [10, 20, 30];
        let i: integer = 0;
        while (true) { print(xs[i]); i = i + 1; }
    """)
    lines = [l.strip() for l in execution.output.splitlines() if l.strip()]
    assert execution.exit_code == 1
    assert lines == ["10", "20", "30", f"Error en tiempo de ejecucion: {INDEX}"]
