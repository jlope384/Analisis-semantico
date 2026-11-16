// Asignacion de registros (getReg): muchos valores vivos a la vez
// obligan a usar los $s y a hacer spill a la pila.
function presion(a: integer, b: integer): integer {
  let c: integer = a + b;
  let d: integer = a * b;
  let e: integer = c - d;
  let f: integer = c * 2;
  let g: integer = d + 7;
  let h: integer = e + f;
  let i: integer = g - h;
  let j: integer = a + c + e;
  let k: integer = b + d + f;
  let l: integer = (a + b) * (c + d) - (e + f) * (g - h);
  return a + b + c + d + e + f + g + h + i + j + k + l;
}
let total: integer = 0;
for (let n: integer = 1; n <= 3; n = n + 1) {
  total = total + presion(n, n + 1);
}
print(total);
