#!/bin/sh
# Corre los programas de la demo: compila cada .cps y, si compila, ejecuta el
# MIPS en MARS. Se usa dentro del contenedor (directorio /program):
#   sh demo/correr_demo.sh                      -> todas las carpetas
#   sh demo/correr_demo.sh demo/3_errores_semanticos   -> una carpeta
#   sh demo/correr_demo.sh demo/1_correctos/03_clases.cps -> un archivo
cd "$(dirname "$0")/.." || exit 1
[ -f CompiscriptParser.py ] || antlr -Dlanguage=Python3 Compiscript.g4

objetivo=${1:-demo}
if [ -f "$objetivo" ]; then archivos=$objetivo; else archivos=$(find "$objetivo" -name '*.cps' | sort); fi

for f in $archivos; do
  echo
  echo "=================================================================="
  echo "$f"
  echo "------------------------------------------------------------------"
  sed -n '1,/^[^\/]/p' "$f" | grep '^//'
  asm="/tmp/$(basename "$f" .cps).asm"
  if python3 Driver.py "$f" --mips "$asm" > /tmp/errores.txt 2>&1; then
    echo "[compila] ejecutando en MARS:"
    mars "$asm"
    echo "[codigo de salida: $?]"
  else
    echo "[no compila]"
    cat /tmp/errores.txt
  fi
done
