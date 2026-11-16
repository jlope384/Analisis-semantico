#!/bin/sh
# Corre un comando dentro del contenedor csp-image con program/ montado en /program.
# Equivale al alias:  alias cps='docker run --rm -v "$(pwd)/program":/program csp-image'
# Funciona en macOS, Linux y Git Bash de Windows. Se puede llamar desde cualquier carpeta.
#   ./cps.sh python3 Driver.py demo/1_correctos/03_clases.cps --tac
#   ./cps.sh sh demo/correr_demo.sh demo/3_errores_semanticos
#   ./cps.sh pytest -q
#   ./cps.sh                -> abre una terminal dentro del contenedor
raiz=$(cd "$(dirname "$0")" && pwd)

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    # Git Bash convierte rutas como /program a C:/Program Files/Git/program; se desactiva
    # y se usa la ruta de Windows (C:/Users/...) para el volumen.
    export MSYS_NO_PATHCONV=1
    host=$(cd "$raiz/program" && pwd -W)
    ;;
  *)
    host="$raiz/program"
    ;;
esac

# -it solo si hay terminal interactiva (para la shell); sin ella la salida se puede filtrar con grep.
if [ -t 0 ] && [ -t 1 ]; then tty="-it"; else tty=""; fi

if [ $# -eq 0 ]; then set -- bash; fi
exec docker run --rm $tty -v "$host":/program csp-image "$@"
