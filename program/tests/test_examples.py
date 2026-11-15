"""Compila cada ejemplo de `examples/`, lo ejecuta en MARS y compara su salida
con el `.out` del mismo nombre.

Si la ultima linea esperada es `Error en tiempo de ejecucion: ...`, el ejemplo
debe terminar con codigo de salida 1; si no, con 0. Para agregar un ejemplo
basta con poner el par `nombre.cps` / `nombre.out` en la carpeta.
"""

from pathlib import Path

import pytest

from compiler import compile_source
from codegen import simulator

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
PROGRAMS = sorted(EXAMPLES.glob("*.cps"))
RUNTIME_ERROR = "Error en tiempo de ejecucion:"


def _lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def test_every_example_has_its_expected_output():
    assert PROGRAMS, "no hay ejemplos en examples/"
    missing = [p.name for p in PROGRAMS if not p.with_suffix(".out").exists()]
    assert missing == []


@pytest.mark.skipif(not simulator.is_available(), reason="MARS no esta instalado")
@pytest.mark.parametrize("program", PROGRAMS, ids=lambda p: p.stem)
def test_example_output_matches(program: Path):
    result = compile_source(program.read_text(encoding="utf-8"))
    assert result.errors == []
    expected = _lines(program.with_suffix(".out").read_text(encoding="utf-8"))
    execution = simulator.run_mips(result.mips)
    assert _lines(execution.output) == expected
    expected_exit = 1 if expected and expected[-1].startswith(RUNTIME_ERROR) else 0
    assert execution.exit_code == expected_exit
