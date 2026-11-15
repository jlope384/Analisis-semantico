// Un error sin manejador termina el programa con codigo de salida 1.
function profundo(xs: integer[], i: integer): integer {
  return xs[i];
}
let xs: integer[] = [1, 2, 3];
print(profundo(xs, 2));
print(profundo(xs, 3));
print("no se imprime");
