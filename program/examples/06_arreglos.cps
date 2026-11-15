// Arreglos: indexacion, asignacion, foreach y ordenamiento burbuja.
function ordenar(xs: integer[], n: integer) {
  for (let i: integer = 0; i < n - 1; i = i + 1) {
    for (let j: integer = 0; j < n - 1 - i; j = j + 1) {
      if (xs[j] > xs[j + 1]) {
        let tmp: integer = xs[j];
        xs[j] = xs[j + 1];
        xs[j + 1] = tmp;
      }
    }
  }
}

function suma(xs: integer[]): integer {
  let s: integer = 0;
  foreach (x in xs) { s = s + x; }
  return s;
}

let datos: integer[] = [42, 7, 19, 3, 25, 11];
ordenar(datos, 6);
foreach (d in datos) { print(d); }
print(suma(datos));

let matriz: integer[][] = [[1, 2], [3, 4]];
print(matriz[1][0] + matriz[0][1]);
