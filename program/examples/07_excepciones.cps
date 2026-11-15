// try/catch: errores atrapados en la misma funcion y en un llamador.
function dividir(a: integer, b: integer): integer {
  return a / b;
}

function seguro(xs: integer[], i: integer): integer {
  try {
    return xs[i];
  } catch (e) {
    print(e);
    return -1;
  }
}

let xs: integer[] = [10, 20, 30];
print(seguro(xs, 1));
print(seguro(xs, 7));

try {
  print(dividir(10, 2));
  print(dividir(1, 0));
  print("no se imprime");
} catch (error) {
  print("atrapado: " + error);
}
print("sigue");
