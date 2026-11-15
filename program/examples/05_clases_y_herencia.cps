// Clases con constructor, campos, herencia y despacho dinamico por la vtable.
class Figura {
  let nombre: string;
  function constructor(nombre: string) { this.nombre = nombre; }
  function area(): integer { return 0; }
  function describir(): string { return this.nombre; }
}

class Rectangulo : Figura {
  let ancho: integer;
  let alto: integer;
  function constructor(ancho: integer, alto: integer) {
    this.nombre = "rectangulo";
    this.ancho = ancho;
    this.alto = alto;
  }
  function area(): integer { return this.ancho * this.alto; }
}

class Cuadrado : Rectangulo {
  function constructor(lado: integer) {
    this.nombre = "cuadrado";
    this.ancho = lado;
    this.alto = lado;
  }
  function describir(): string { return "cuadrado de lado " + "fijo"; }
}

let total: integer = 0;
function mostrar(f: Figura): integer {
  print(f.describir());
  print(f.area());
  return f.area();
}
total = total + mostrar(new Figura("punto"));
total = total + mostrar(new Rectangulo(3, 4));
let c: Figura = new Cuadrado(5);
total = total + mostrar(c);
print(total);
