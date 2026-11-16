// Secuencia de llamada y retorno: recursion, mas de 4 argumentos
// y llamadas anidadas. Ver el prologo/epilogo en el .asm generado.
function factorial(n: integer): integer {
  if (n <= 1) { return 1; }
  return n * factorial(n - 1);
}

function suma6(a: integer, b: integer, c: integer, d: integer, e: integer, f: integer): integer {
  return a + b + c + d + e + f;
}

function doble(x: integer): integer { return x * 2; }

print(factorial(5));
print(suma6(1, 2, 3, 4, 5, 6));
print(doble(doble(doble(3))));
