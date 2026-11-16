#!/bin/sh
# Corre el guion de la presentacion parte por parte. Desde la raiz del repo:
#   ./presentacion.sh preparar   -> construye la imagen si falta, genera el parser y corre las pruebas
#   ./presentacion.sh 1          -> corre los comandos de la parte 1 (asi hasta la 9)
#   ./presentacion.sh todo       -> todas las partes seguidas
# Antes de cada comando se muestra y se espera Enter, para ir al ritmo de quien presenta.
cd "$(dirname "$0")" || exit 1
CPS=./cps.sh

titulo() { printf '\n\033[1;36m=== %s ===\033[0m\n' "$1"; }
nota()   { printf '\033[2m%s\033[0m\n' "$1"; }
correr() {
  printf '\n\033[1;33m$ cps %s\033[0m' "$*"
  [ -n "$SIN_PAUSA" ] || read -r _
  echo
  $CPS "$@"
}

preparar() {
  titulo "Preparar"
  if ! docker info >/dev/null 2>&1; then
    echo "Docker no responde. Abrir Docker Desktop (Windows) o 'colima start' (Mac) y volver a correr."
    exit 1
  fi
  if ! docker image inspect csp-image >/dev/null 2>&1; then
    echo "Construyendo la imagen csp-image (solo la primera vez)..."
    docker build -t csp-image . || exit 1
  fi
  SIN_PAUSA=1 correr antlr -Dlanguage=Python3 Compiscript.g4
  SIN_PAUSA=1 correr pytest -q
  nota "Esperado: 277 passed."
}

parte1() {
  titulo "1. Introduccion - Cifuentes"
  correr python3 Driver.py demo/1_correctos/01_llamadas_y_retornos.cps --tac
  nota "Esperado: begin_func factorial, 12 ... t1 = call factorial, 1"
}

parte2() {
  titulo "2. Memoria y secuencia de llamada - Lopez"
  correr python3 Driver.py demo/1_correctos/01_llamadas_y_retornos.cps --mips demo/01.asm
  nota "Abrir program/demo/01.asm en VS Code y buscar fn_suma6:"
  correr sh demo/correr_demo.sh demo/1_correctos/01_llamadas_y_retornos.cps
  nota "Esperado: 120, 21, 24 y codigo de salida 0."
}

parte3() {
  titulo "3. Asignacion de registros (getReg) - Lopez"
  correr sh -c "python3 Driver.py demo/1_correctos/02_registros_y_spill.cps --mips | grep -n spill"
  nota "Esperado: 5 lineas # spill."
  correr sh demo/correr_demo.sh demo/1_correctos/02_registros_y_spill.cps
  nota "Esperado: 295."
}

parte4() {
  titulo "4. Clases y despacho dinamico - Lopez"
  correr sh demo/correr_demo.sh demo/1_correctos/03_clases.cps
  nota "Esperado: Firulais dice guau, Michi dice miau."
}

parte5() {
  titulo "5. Funciones anidadas (closures) - Cifuentes"
  correr sh demo/correr_demo.sh demo/1_correctos/04_closures.cps
  correr sh -c "python3 Driver.py demo/1_correctos/04_closures.cps --mips | grep -n enlace"
  nota "Esperado: 6, 16, 16 y lineas con # enlace de acceso."
}

parte6() {
  titulo "6. Excepciones y errores en ejecucion - Cifuentes"
  correr sh demo/correr_demo.sh demo/1_correctos/05_arreglos_y_excepciones.cps
  correr sh demo/correr_demo.sh demo/4_errores_ejecucion
  nota "Esperado: 'atrapado: indice fuera de rango'; luego 3 programas con error y codigo 1."
}

parte7() {
  titulo "7. Errores de compilacion - Cifuentes"
  correr sh demo/correr_demo.sh demo/2_errores_sintacticos
  correr sh demo/correr_demo.sh demo/3_errores_semanticos
  nota "Esperado: [no compila] con linea y columna en cada archivo."
}

parte8() {
  titulo "8. IDE en vivo - Cifuentes (manual en VS Code)"
  nota "Abrir program/demo/3_errores_semanticos/04_llamada_incorrecta.cps, corregir suma(1) -> suma(1, 2),"
  nota "quitar \"dos\", guardar, y correr los 3 comandos Compiscript con Ctrl+Shift+P (Cmd+Shift+P en Mac)."
  printf 'Enter para deshacer los cambios con git checkout program/demo...'
  read -r _
  git checkout program/demo
}

parte9() {
  titulo "9. Pruebas y cierre - Lopez"
  correr pytest -q
  nota "Esperado: 277 passed."
}

case "${1:-}" in
  preparar) preparar ;;
  [1-9])    "parte$1" ;;
  todo)     for i in 1 2 3 4 5 6 7 8 9; do "parte$i"; done ;;
  *)        sed -n '2,6p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
