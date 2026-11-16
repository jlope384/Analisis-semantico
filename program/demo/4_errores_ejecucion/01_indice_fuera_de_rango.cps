// Compila bien, pero falla en MARS: indice fuera de rango sin try/catch.
let xs: integer[] = [1, 2, 3];
print(xs[1]);
print(xs[5]);
print("no se imprime");
