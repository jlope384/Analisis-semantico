// Recursion, mas de cuatro argumentos y llamadas anidadas como argumentos.
function factorial(n: integer): integer {
  if (n <= 1) { return 1; }
  return n * factorial(n - 1);
}

function fib(n: integer): integer {
  if (n < 2) { return n; }
  return fib(n - 1) + fib(n - 2);
}

function mcd(a: integer, b: integer): integer {
  if (b == 0) { return a; }
  return mcd(b, a % b);
}

function ponderada(a: integer, b: integer, c: integer, d: integer, e: integer): integer {
  return a + 2 * b + 3 * c + 4 * d + 5 * e;
}

function promedio(a: float, b: float): float {
  return (a + b) / 2;
}

print(factorial(10));
print(fib(20));
print(mcd(1071, 462));
print(ponderada(1, 2, 3, 4, 5));
print(mcd(factorial(5), fib(12)));
print(promedio(3, 4.5));
