// Funcion anidada que modifica una variable de la funcion externa
// (enlace de acceso / static link).
function contador(inicio: integer): integer {
  let cuenta: integer = inicio;
  function avanzar(paso: integer): integer {
    cuenta = cuenta + paso;
    return cuenta;
  }
  print(avanzar(1));
  print(avanzar(10));
  return cuenta;
}
print(contador(5));
