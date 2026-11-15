// Funciones anidadas que leen y escriben variables de las funciones que las
// contienen (enlace de acceso), con varios niveles y recursion.
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

function externa(x: integer): integer {
  let acumulado: integer = 0;
  function media(y: integer): integer {
    let local: integer = y * 2;
    function interna(z: integer): integer {
      acumulado = acumulado + z;
      return x + local + z;
    }
    return interna(1) + interna(2);
  }
  let r: integer = media(10);
  print(acumulado);
  return r;
}
print(externa(100));

function sumaHasta(n: integer): integer {
  let llamadas: integer = 0;
  function suma(k: integer): integer {
    llamadas = llamadas + 1;
    if (k == 0) { return 0; }
    return k + suma(k - 1);
  }
  let total: integer = suma(n);
  print(llamadas);
  return total;
}
print(sumaHasta(10));
