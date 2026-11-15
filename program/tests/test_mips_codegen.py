"""Pruebas del ensamblador generado que no necesitan el simulador:
secuencia de llamada, asignacion de registros (getReg) y casos no soportados."""

from compiler import compile_source
from Driver import main as driver_main


def mips(source: str) -> str:
    result = compile_source(source)
    assert result.errors == []
    return result.mips


def function_code(asm: str, label: str) -> list[str]:
    lines = [l.strip() for l in asm.splitlines()]
    start = lines.index(f"{label}:")
    end = next(i for i in range(start + 1, len(lines)) if lines[i] == "jr    $ra")
    return lines[start:end + 1]


# --- secuencia de llamada -----------------------------------------------------

def test_function_prologue_saves_ra_fp_and_copies_arguments():
    code = function_code(mips("function f(a: integer, b: integer): integer { return a - b; }"), "fn_f")
    assert code[1].startswith("addiu $sp, $sp, -")
    assert any(l.startswith("sw    $ra,") for l in code[:4])
    assert any(l.startswith("sw    $fp,") for l in code[:4])
    assert "move  $fp, $sp" in code
    # los dos argumentos se copian del area del llamador al registro de activacion
    assert sum("# argumento" in l for l in code) == 2


def test_caller_pushes_arguments_and_pops_them_after_the_call():
    asm = mips("function f(a: integer, b: integer): integer { return a; } print(f(1, 2));")
    lines = [l.strip() for l in asm.splitlines()]
    call = lines.index("jal   fn_f")
    assert lines.count("addiu $sp, $sp, -4") == 2
    assert lines[call + 1] == "addiu $sp, $sp, 8"
    assert lines[call + 2].startswith("move ") and lines[call + 2].endswith("$v0")


def test_epilogue_restores_the_saved_registers_it_used():
    code = function_code(mips("""
        function f(n: integer): integer { let x: integer = n + 1; return x * 2; }
    """), "fn_f")
    saved = [l.split()[1].rstrip(",") for l in code if l.startswith("sw    $s")]
    restored = [l.split()[1].rstrip(",") for l in code if l.startswith("lw    $s")
                and "($fp)" in l and l.split(",")[1].strip().endswith("($fp)")]
    assert saved and set(saved) <= set(restored)


def test_virtual_call_goes_through_the_vtable():
    asm = mips("""
        class A { function f(): integer { return 1; } }
        class B : A { function f(): integer { return 2; } }
        let a: A = new B();
        print(a.f());
    """)
    assert "__vt_B: .word fn_B__f" in asm
    assert "jalr  $v1" in asm


# --- asignacion de registros --------------------------------------------------

def test_temporaries_use_t_registers_and_variables_use_s_registers():
    code = function_code(mips("function f(n: integer): integer { return n * 3 + 1; }"), "fn_f")
    body = "\n".join(code)
    assert "$s0" in body  # la variable n
    assert "$t0" in body  # los temporales


def test_dead_temporary_register_is_reused():
    code = function_code(mips("function f(a: integer): integer { return (a + 1) * (a + 2) + 3; }"), "fn_f")
    used_t = {tok.rstrip(",") for l in code for tok in l.split() if tok.startswith("$t")}
    # t1 y t2 son los unicos temporales vivos a la vez
    assert used_t <= {"$t0", "$t1"}


def test_high_register_pressure_spills_to_the_activation_record():
    decls = " ".join(f"let v{i}: integer = {i};" for i in range(14))
    nested = "(" * 13 + "v0" + "".join(f" + (v{i} * {i + 1}))" for i in range(1, 14))
    terms = " + ".join(f"(v{i} * {i + 1})" for i in range(14))
    # ningun temporal queda vivo mucho tiempo en `nested`, pero en `terms` si
    asm = mips(f"function f(): integer {{ {decls} return {terms} + {nested}; }}")
    assert "# spill" in asm


def test_float_values_use_floating_point_registers():
    asm = mips("let x: float = 1.5; let y: float = x * 2; print(y);")
    assert "__flt_0: .float 1.5" in asm
    assert "mul.s" in asm
    assert "cvt.s.w" in asm  # el 2 se promueve a float


# --- funciones anidadas: enlace de acceso (access link) ------------------------

CLOSURE = """
    function outer(n: integer): integer {
      let x: integer = 1;
      function inner(k: integer): integer { x = x + k; return x + n; }
      return inner(2);
    }
    print(outer(5));
"""


def lines_of(asm: str) -> list[str]:
    return [l.strip() for l in asm.splitlines()]


def test_call_to_nested_function_pushes_callers_fp_as_access_link():
    code = function_code(mips(CLOSURE), "fn_outer")
    call = code.index("jal   fn_outer__inner")
    # el ultimo valor apilado antes del jal es el $fp del marco que contiene a inner
    assert code[call - 2] == "addiu $sp, $sp, -4"
    assert code[call - 1].startswith("sw    $fp, 0($sp)")
    # se quitan el argumento y el enlace
    assert code[call + 1] == "addiu $sp, $sp, 8"


def test_top_level_call_does_not_push_an_access_link():
    asm = mips("function f(a: integer): integer { return a; } print(f(1));")
    assert "enlace de acceso" not in asm


def test_nested_function_saves_its_access_link_and_reads_its_arguments_after_it():
    code = function_code(mips(CLOSURE), "fn_outer__inner")
    size = int(code[1].split("-")[-1])
    link = code.index(f"lw    $a2, {size}($fp)   # enlace de acceso")
    assert code[link + 1].startswith("sw    $a2, ")
    # el unico argumento queda justo encima del enlace
    assert f"lw    $a2, {size + 4}($fp)   # argumento k" in code


def test_nonlocal_variable_is_reached_through_the_access_link():
    code = function_code(mips(CLOSURE), "fn_outer__inner")
    body = "\n".join(code)
    assert "lw    $k1, " in body and "# enlace de acceso" in body
    # x (offset 4 en outer) y n (offset 0) se leen y escriben a partir de $k1
    assert any(l.endswith(", 4($k1)") and l.startswith("lw") for l in code)
    assert any(l.endswith(", 4($k1)") and l.startswith("sw") for l in code)
    assert any(l.endswith(", 0($k1)") for l in code)


def test_two_levels_follow_the_chain_twice():
    code = function_code(mips("""
        function a(): integer {
          let x: integer = 1;
          function b(): integer {
            function c(): integer { return x; }
            return c();
          }
          return b();
        }
        print(a());
    """), "fn_a__b__c")
    chain = [l for l in code if l.startswith("lw    $k1, ")]
    assert chain[0].endswith("($fp)   # enlace de acceso")
    assert chain[1].endswith("($k1)")


def test_recursive_nested_call_passes_its_own_access_link():
    code = function_code(mips("""
        function outer(): integer {
          let base: integer = 1;
          function fact(n: integer): integer {
            if (n <= 1) { return base; }
            return n * fact(n - 1);
          }
          return fact(4);
        }
        print(outer());
    """), "fn_outer__fact")
    call = code.index("jal   fn_outer__fact")
    # fact esta a la misma profundidad que si misma: se pasa su propio enlace (1 salto)
    assert code[call - 3].startswith("lw    $k1, ") and code[call - 3].endswith("($fp)   # enlace de acceso")
    assert code[call - 1].startswith("sw    $k1, 0($sp)")


def test_captured_variable_is_reloaded_after_calling_the_nested_function():
    code = function_code(mips("""
        function outer(): integer {
          let x: integer = 1;
          function bump() { x = x + 1; }
          bump();
          return x;
        }
        print(outer());
    """), "fn_outer")
    call = code.index("jal   fn_outer__bump")
    # x no se queda en un $s a traves de la llamada: se vuelve a leer de memoria
    assert any(l.startswith("lw    $s") and l.endswith("4($fp)") for l in code[call:])


# --- errores ------------------------------------------------------------------

def test_program_with_semantic_errors_produces_no_mips():
    result = compile_source('let a: integer = "hola";')
    assert result.mips is None


def test_driver_writes_the_assembly_file(tmp_path):
    source = tmp_path / "p.cps"
    source.write_text("print(1 + 2);", encoding="utf-8")
    output = tmp_path / "p.asm"
    assert driver_main(str(source), mips_output=str(output)) == 0
    text = output.read_text(encoding="utf-8")
    assert text.startswith(".data")
    assert "main:" in text and "syscall" in text
