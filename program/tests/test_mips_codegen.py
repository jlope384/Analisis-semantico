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


# --- errores ------------------------------------------------------------------

def test_closure_over_outer_local_is_reported_as_codegen_error():
    result = compile_source("""
        function outer(): integer {
          let x: integer = 1;
          function inner(): integer { return x + 1; }
          return inner();
        }
        print(outer());
    """)
    assert result.mips is None
    assert any("closures" in e for e in result.errors)


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
