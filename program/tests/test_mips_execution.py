"""Pruebas de punta a punta: se compila cada programa a MIPS, se ejecuta en MARS
y se compara lo que imprime.

Requieren el simulador (comando `mars` o MARS_JAR); dentro del contenedor de
Docker ya esta instalado:

    docker run --rm -v "$(pwd)/program":/program csp-image pytest tests/test_mips_execution.py
"""

import pytest

from compiler import compile_source
from codegen import simulator

pytestmark = pytest.mark.skipif(not simulator.is_available(), reason="MARS no esta instalado")


def run(source: str):
    result = compile_source(source)
    assert result.errors == []
    return simulator.run_mips(result.mips)


def output_of(source: str) -> list[str]:
    execution = run(source)
    assert execution.exit_code == 0, execution.output
    return [line.strip() for line in execution.output.splitlines() if line.strip()]


# --- expresiones ---------------------------------------------------------------

def test_integer_arithmetic_and_precedence():
    assert output_of("""
        let a: integer = 7;
        let b: integer = 3;
        print(a + b * 2);
        print((a + b) * 2);
        print(a / b);
        print(a % b);
        print(-a + 1);
        print(a - b - 1);
    """) == ["13", "20", "2", "1", "-6", "3"]


def test_float_arithmetic_with_integer_promotion():
    assert output_of("""
        let x: float = 1.5;
        let y: float = x * 2 + 0.25;
        print(y);
        let z: float = 3;
        print(z / 2);
        print(-x);
    """) == ["3.25", "1.5", "-1.5"]


def test_comparisons_on_integers_and_floats():
    assert output_of("""
        let a: integer = 2;
        let f: float = 2.5;
        print(a < 3);
        print(a >= 3);
        print(f > a);
        print(f == 2.5);
        print(a != 2);
    """) == ["true", "false", "true", "true", "false"]


def test_logical_operators_short_circuit():
    assert output_of("""
        function noise(v: boolean): boolean { print("evaluado"); return v; }
        print(false && noise(true));
        print(true || noise(true));
        print(true && noise(false));
        print(!(1 < 2));
    """) == ["false", "true", "evaluado", "false", "false"]


def test_ternary_operator():
    assert output_of("""
        let n: integer = 5;
        print(n > 3 ? "grande" : "chico");
        print(n > 9 ? 1 : 0);
    """) == ["grande", "0"]


def test_string_concatenation_and_equality():
    assert output_of("""
        let a: string = "hola";
        let b: string = a + " " + "mundo";
        print(b);
        print(b == "hola mundo");
        print(a != "hola");
    """) == ["hola mundo", "true", "false"]


# --- control de flujo ------------------------------------------------------------

def test_if_else_and_loops():
    assert output_of("""
        let i: integer = 0;
        let total: integer = 0;
        while (i < 5) { total = total + i; i = i + 1; }
        print(total);
        do { i = i - 2; } while (i > 0);
        print(i);
        for (let j: integer = 0; j < 3; j = j + 1) {
          if (j == 1) { print("uno"); } else { print(j); }
        }
    """) == ["10", "-1", "0", "uno", "2"]


def test_break_and_continue():
    assert output_of("""
        for (let i: integer = 0; i < 10; i = i + 1) {
          if (i % 2 == 0) { continue; }
          if (i > 6) { break; }
          print(i);
        }
    """) == ["1", "3", "5"]


def test_switch_with_fall_through_and_default():
    assert output_of("""
        function name(n: integer): string {
          let r: string = "";
          switch (n) {
            case 1: r = r + "uno "; break;
            case 2: r = r + "dos ";
            case 3: r = r + "tres "; break;
            default: r = "otro";
          }
          return r;
        }
        print(name(1));
        print(name(2));
        print(name(7));
    """) == ["uno", "dos tres", "otro"]


# --- funciones y secuencia de llamada --------------------------------------------

def test_recursion_preserves_frames():
    assert output_of("""
        function fib(n: integer): integer {
          if (n < 2) { return n; }
          return fib(n - 1) + fib(n - 2);
        }
        function fact(n: integer): integer {
          if (n <= 1) { return 1; }
          return n * fact(n - 1);
        }
        print(fib(15));
        print(fact(10));
    """) == ["610", "3628800"]


def test_more_than_four_arguments_are_passed_on_the_stack():
    assert output_of("""
        function sum6(a: integer, b: integer, c: integer, d: integer, e: integer, f: integer): integer {
          return a + 2 * b + 3 * c + 4 * d + 5 * e + 6 * f;
        }
        print(sum6(1, 2, 3, 4, 5, 6));
    """) == ["91"]


def test_nested_calls_as_arguments():
    assert output_of("""
        function sq(x: integer): integer { return x * x; }
        function add(a: integer, b: integer): integer { return a + b; }
        print(add(sq(3), add(sq(2), 1)));
    """) == ["14"]


def test_float_parameters_and_return_values():
    assert output_of("""
        function half(x: float): float { return x / 2; }
        print(half(5));
        print(half(1.5) + 1);
    """) == ["2.5", "1.75"]


def test_caller_values_survive_calls():
    # a, b y el temporal de 'a * b' deben sobrevivir a la llamada (registros $s / spill de $t)
    assert output_of("""
        function clobber(n: integer): integer {
          let x: integer = n * 100; let y: integer = x + 1; return y;
        }
        function f(a: integer, b: integer): integer {
          let r: integer = a * b + clobber(9) + a - b;
          return r;
        }
        print(f(6, 7));
    """) == ["942"]  # 42 + 901 + 6 - 7


def test_globals_modified_by_a_function_are_reloaded():
    assert output_of("""
        let counter: integer = 0;
        function bump() { counter = counter + 1; }
        bump(); bump();
        print(counter);
        counter = counter * 10;
        bump();
        print(counter);
    """) == ["2", "21"]


# --- asignacion de registros bajo presion ------------------------------------------

def test_expression_with_more_live_temporaries_than_registers():
    # cada factor queda vivo hasta el final: obliga a hacer spill de temporales
    terms = " + ".join(f"(v{i} * {i + 1})" for i in range(14))
    decls = " ".join(f"let v{i}: integer = {i};" for i in range(14))
    nested = "(" * 13 + "v0" + "".join(f" + (v{i} * {i + 1}))" for i in range(1, 14))
    expected = sum(i * (i + 1) for i in range(14))
    assert output_of(f"""
        {decls}
        print({terms});
        print({nested});
    """) == [str(expected), str(expected)]


def test_function_with_more_local_variables_than_saved_registers():
    decls = " ".join(f"let x{i}: integer = n + {i};" for i in range(12))
    total = " + ".join(f"x{i}" for i in range(12))
    assert output_of(f"""
        function many(n: integer): integer {{ {decls} return {total}; }}
        print(many(1));
    """) == [str(sum(1 + i for i in range(12)))]


# --- clases y objetos -------------------------------------------------------------

# --- funciones anidadas (closures con enlace de acceso) -------------------------

def test_nested_function_reads_and_writes_outer_variable():
    assert output_of("""
        function counter(start: integer): integer {
          let count: integer = start;
          function step(by: integer): integer {
            count = count + by;
            return count;
          }
          print(step(1));
          print(step(10));
          return count;
        }
        print(counter(5));
    """) == ["6", "16", "16"]


def test_two_and_three_levels_of_nesting():
    assert output_of("""
        function a(x: integer): integer {
          let ax: integer = x * 10;
          function b(y: integer): integer {
            let by: integer = y + 1;
            function c(z: integer): integer {
              ax = ax + 1;
              return ax + by + z + x;
            }
            return c(100);
          }
          let r: integer = b(2);
          print(ax);
          return r;
        }
        print(a(3));
    """) == ["31", "137"]


def test_recursion_inside_a_nested_function():
    assert output_of("""
        function sumTo(limit: integer): integer {
          let calls: integer = 0;
          function go(n: integer): integer {
            calls = calls + 1;
            if (n == 0) { return 0; }
            return n + go(n - 1);
          }
          let total: integer = go(limit);
          print(calls);
          return total;
        }
        print(sumTo(10));
    """) == ["11", "55"]


def test_sibling_nested_functions_share_the_outer_frame():
    assert output_of("""
        function outer(): integer {
          let v: integer = 0;
          function inc() { v = v + 1; }
          function twice() { inc(); inc(); }
          twice();
          twice();
          inc();
          return v;
        }
        print(outer());
    """) == ["5"]


def test_closure_over_floats_strings_and_arrays_inside_loops():
    assert output_of("""
        function run(): string {
          let total: float = 0.5;
          let text: string = "a";
          let xs: integer[] = [1, 2, 3];
          function visit(i: integer) {
            total = total + xs[i];
            text = text + "b";
            xs[i] = xs[i] * 2;
          }
          for (let i: integer = 0; i < 3; i = i + 1) { visit(i); }
          print(total);
          print(xs[2]);
          return text;
        }
        print(run());
    """) == ["6.5", "6", "abbb"]


def test_inner_variable_shadowing_an_outer_one():
    assert output_of("""
        function outer(): integer {
          let x: integer = 1;
          function inner(): integer {
            let before: integer = x;
            if (true) { let x: integer = 100; print(x); }
            return before + x;
          }
          return inner();
        }
        print(outer());
    """) == ["100", "2"]


def test_error_in_nested_function_caught_by_outer_try():
    assert output_of("""
        function outer(): integer {
          let xs: integer[] = [7];
          let status: integer = 0;
          function get(i: integer): integer { status = 1; return xs[i]; }
          try { print(get(0)); print(get(5)); } catch (e) { print(e); status = status + 10; }
          return status;
        }
        print(outer());
    """) == ["7", "indice fuera de rango", "11"]


def test_objects_fields_constructor_and_virtual_dispatch():
    assert output_of("""
        class Animal {
          let nombre: string;
          let patas: integer = 4;
          function constructor(nombre: string) { this.nombre = nombre; }
          function hablar(): string { return this.nombre + " hace ruido"; }
          function describir(): string { return hablar(); }
        }
        class Perro : Animal {
          function hablar(): string { return this.nombre + " ladra"; }
        }
        class Pajaro : Animal {
          function constructor(nombre: string) { this.nombre = nombre; this.patas = 2; }
        }
        let animales: Animal[] = [new Animal("Gato"), new Animal("Tom"), new Animal("Ave")];
        animales[1] = new Perro("Toby");
        animales[2] = new Pajaro("Piolin");
        foreach (a in animales) {
          print(a.describir());
          print(a.patas);
        }
    """) == ["Gato hace ruido", "4", "Toby ladra", "4", "Piolin hace ruido", "2"]


def test_methods_with_arguments_and_object_fields():
    assert output_of("""
        class Cuenta {
          let saldo: integer = 0;
          function depositar(monto: integer) { this.saldo = this.saldo + monto; }
          function retirar(monto: integer): boolean {
            if (monto > saldo) { return false; }
            saldo = saldo - monto;
            return true;
          }
        }
        let c: Cuenta = new Cuenta();
        c.depositar(100);
        print(c.retirar(30));
        print(c.retirar(500));
        print(c.saldo);
    """) == ["true", "false", "70"]


# --- arreglos -----------------------------------------------------------------------

def test_arrays_index_assignment_and_foreach():
    assert output_of("""
        let xs: integer[] = [5, 3, 8];
        xs[1] = xs[0] + xs[2];
        foreach (x in xs) { print(x); }
        let m: integer[][] = [[1, 2], [3, 4]];
        m[1][0] = 9;
        print(m[1][0] + m[0][1]);
        let names: string[] = ["a", "b"];
        print(names[0] + names[1]);
        let fs: float[] = [1.5, 2.5];
        print(fs[0] + fs[1]);
    """) == ["5", "13", "8", "11", "ab", "4.0"]


def test_bubble_sort():
    assert output_of("""
        function sort(a: integer[], n: integer) {
          for (let i: integer = 0; i < n; i = i + 1) {
            for (let j: integer = 0; j < n - 1 - i; j = j + 1) {
              if (a[j] > a[j + 1]) { let t: integer = a[j]; a[j] = a[j + 1]; a[j + 1] = t; }
            }
          }
        }
        let v: integer[] = [9, 4, 7, 1, 8, 2];
        sort(v, 6);
        foreach (x in v) { print(x); }
    """) == ["1", "2", "4", "7", "8", "9"]


# --- errores en tiempo de ejecucion y try/catch --------------------------------------

def test_index_out_of_range_is_caught():
    assert output_of("""
        let xs: integer[] = [1, 2];
        let r: integer = 0;
        try { r = 5; print(xs[2]); r = 7; } catch (err) { print(err); }
        print(r);
    """) == ["indice fuera de rango", "5"]


def test_division_by_zero_is_caught():
    assert output_of("""
        let zero: integer = 0;
        try { print(10 / zero); } catch (e) { print("capturado: " + e); }
    """) == ["capturado: division entre cero"]


def test_error_in_callee_unwinds_to_callers_catch():
    assert output_of("""
        function get(a: integer[], i: integer): integer { return a[i]; }
        function deep(a: integer[], i: integer): integer { return get(a, i) + 1; }
        let xs: integer[] = [10];
        try { print(deep(xs, 0)); print(deep(xs, 3)); } catch (e) { print(e); }
        print(deep(xs, 0));
    """) == ["11", "indice fuera de rango", "11"]


def test_break_and_return_inside_try_remove_the_handler():
    assert output_of("""
        function safe(a: integer[], i: integer): integer {
          try { return a[i]; } catch (e) { return -1; }
        }
        let xs: integer[] = [4];
        while (true) { try { break; } catch (e) { print("no"); } }
        print(safe(xs, 0));
        print(safe(xs, 9));
    """) == ["4", "-1"]


def test_uncaught_error_stops_the_program_with_exit_code_1():
    execution = run("""
        let xs: integer[] = [1];
        print("antes");
        print(xs[3]);
        print("despues");
    """)
    assert execution.exit_code == 1
    assert "antes" in execution.output
    assert "Error en tiempo de ejecucion: indice fuera de rango" in execution.output
    assert "despues" not in execution.output


def test_null_object_access_is_a_runtime_error():
    execution = run("""
        class A { let v: integer = 1; }
        let a: A = null;
        print(a.v);
    """)
    assert execution.exit_code == 1
    assert "acceso a una referencia null" in execution.output


def test_sample_program_runs():
    with open("program.cps", encoding="utf-8") as f:
        assert output_of(f.read()) == [
            "Hola Mundo", "Toby ladra.", "90", "85", "100", "90", "85", "120",
        ]


def test_virtual_call_on_null_is_a_runtime_error_that_can_be_caught():
    execution = run("""
        class A { function f(): integer { return 1; } }
        class B : A { function f(): integer { return 2; } }
        let a: A = null;
        try { print(a.f()); } catch (e) { print(e); }
        print(a.f());
        print("despues");
    """)
    assert execution.exit_code == 1
    lines = [l.strip() for l in execution.output.splitlines() if l.strip()]
    assert lines == ["acceso a una referencia null",
                     "Error en tiempo de ejecucion: acceso a una referencia null"]


# --- presion de registros: spill y restauracion -----------------------------------

def _wrap32(value: int) -> int:
    return (value + 2**31) % 2**32 - 2**31


def _right_nested(terms: list[str], last: str) -> str:
    """t0 + (t1 + (t2 + ... + last)): todos los terminos de la izquierda quedan vivos."""
    expression = last
    for term in reversed(terms):
        expression = f"({term} + {expression})"
    return expression


def output_and_asm(source: str):
    result = compile_source(source)
    assert result.errors == []
    execution = simulator.run_mips(result.mips)
    assert execution.exit_code == 0, execution.output
    return [l.strip() for l in execution.output.splitlines() if l.strip()], result.mips


def test_live_temporaries_survive_nested_calls_under_register_pressure():
    count = 14  # mas valores vivos que registros $t (10) y $s (8)
    decls = " ".join(f"let v{i}: integer = {i + 1};" for i in range(count))
    terms = [f"v{i} * {i + 2}" for i in range(count)]
    inner = "add3(v3 * v4, mul2(v5 + v6, add3(v7, v8 * v9, v10)), v11 - v12)"
    source = f"""
        function add3(a: integer, b: integer, c: integer): integer {{ return a + b + c; }}
        function mul2(a: integer, b: integer): integer {{ return a * b; }}
        function run(): integer {{
          {decls}
          let r: integer = {_right_nested(terms, inner)};
          print({' + '.join(f'v{i}' for i in range(count))});
          return r;
        }}
        print(run());
    """
    v = [i + 1 for i in range(count)]
    inner_value = (v[3] * v[4]) + (v[5] + v[6]) * (v[7] + v[8] * v[9] + v[10]) + (v[11] - v[12])
    expected = sum(v[i] * (i + 2) for i in range(count)) + inner_value
    lines, asm = output_and_asm(source)
    assert "# spill" in asm
    assert lines == [str(sum(v)), str(expected)]


def test_loop_with_more_variables_than_saved_registers_and_calls():
    count, iterations = 12, 5
    decls = " ".join(f"let a{i}: integer = {i};" for i in range(count))
    updates = " ".join(
        f"a{i} = a{i} + step(a{(i + 1) % count}, {'i' if i == count - 1 else f'a{(i + 2) % count}'});"
        for i in range(count)
    )
    source = f"""
        function step(x: integer, y: integer): integer {{ return x * 2 - y; }}
        function run(n: integer): integer {{
          {decls}
          let i: integer = 0;
          while (i < n) {{ {updates} i = i + 1; }}
          return {' + '.join(f'a{i}' for i in range(count))};
        }}
        print(run({iterations}));
    """
    a = list(range(count))
    for i in range(iterations):
        for k in range(count):
            y = i if k == count - 1 else a[(k + 2) % count]
            a[k] = _wrap32(a[k] + a[(k + 1) % count] * 2 - y)
    lines, asm = output_and_asm(source)
    assert "# spill" in asm
    assert lines == [str(_wrap32(sum(a)))]


def test_recursion_with_many_live_values_restores_each_frame():
    count = 11
    decls = " ".join(f"let x{i}: integer = n * {i + 1};" for i in range(count))
    terms = [f"x{i}" for i in range(count)]
    source = f"""
        function deep(n: integer): integer {{
          if (n == 0) {{ return 0; }}
          {decls}
          return {_right_nested(terms, "deep(n - 1)")};
        }}
        print(deep(6));
    """

    def deep(n):
        return 0 if n == 0 else sum(n * (i + 1) for i in range(count)) + deep(n - 1)

    lines, asm = output_and_asm(source)
    assert "# spill" in asm
    assert lines == [str(deep(6))]


def test_float_values_survive_calls_under_register_pressure():
    count = 14  # mas que los 12 registros $f temporales y los 12 $f20-$f31
    decls = " ".join(f"let f{i}: float = {i}.5;" for i in range(count))
    terms = [f"f{i} * {i + 1}" for i in range(count)]
    source = f"""
        function half(x: float): float {{ return x / 2; }}
        function run(): float {{
          {decls}
          return {_right_nested(terms, "half(f0 + f13)")};
        }}
        print(run());
    """
    f = [i + 0.5 for i in range(count)]
    expected = sum(f[i] * (i + 1) for i in range(count)) + (f[0] + f[13]) / 2
    lines, asm = output_and_asm(source)
    assert "# spill" in asm
    assert lines == [repr(expected)]
