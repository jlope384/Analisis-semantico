"""Ejecuta un programa MIPS en el simulador MARS y devuelve su salida.

Busca MARS en este orden:
1. el comando `mars` (instalado por el Dockerfile),
2. la variable de entorno MARS_JAR con la ruta a Mars4_5.jar (requiere java).
"""

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass


@dataclass
class RunResult:
    output: str  # lo que imprimio el programa
    exit_code: int


def mars_command():
    if shutil.which("mars"):
        return ["mars"]
    jar = os.environ.get("MARS_JAR")
    if jar and os.path.exists(jar) and shutil.which("java"):
        return ["java", "-Djava.awt.headless=true", "-jar", jar, "nc"]
    return None


def is_available() -> bool:
    return mars_command() is not None


def run_mips(assembly: str, max_steps: int = 5_000_000, timeout: int = 60) -> RunResult:
    command = mars_command()
    if command is None:
        raise RuntimeError("no se encontro MARS: instale el comando 'mars' o defina MARS_JAR")

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "programa.asm")
        with open(path, "w", encoding="utf-8") as f:
            f.write(assembly)
        # se1: un error del simulador termina con codigo 1; un limite de pasos evita ciclos infinitos
        completed = subprocess.run(
            command + ["se1", str(max_steps), path],
            capture_output=True, text=True, timeout=timeout,
        )
    return RunResult(completed.stdout, completed.returncode)
