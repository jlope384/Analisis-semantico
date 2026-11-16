// Error semantico: acceso a un metodo que la clase no tiene.
class Punto {
  let x: integer;
  function constructor(x: integer) { this.x = x; }
}
let p: Punto = new Punto(1);
p.mover(3);
