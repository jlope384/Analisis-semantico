// Arreglos, try/catch y un error atrapado.
let xs: integer[] = [5, 3, 8, 1];
let suma: integer = 0;
foreach (x in xs) { suma = suma + x; }
print("suma:");
print(suma);
try {
  print(xs[10]);
} catch (err) {
  print("atrapado: " + err);
}
print("el programa sigue");
