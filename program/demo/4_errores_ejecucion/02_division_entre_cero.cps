// Compila bien, pero falla en MARS: division entre cero.
function dividir(a: integer, b: integer): integer { return a / b; }
print(dividir(10, 2));
print(dividir(10, 0));
print("no se imprime");
