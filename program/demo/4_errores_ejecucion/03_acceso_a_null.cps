// Compila bien, pero falla en MARS: llamar un metodo sobre null.
class Caja {
  let v: integer;
  function constructor(v: integer) { this.v = v; }
  function valor(): integer { return this.v; }
}
let c: Caja = new Caja(7);
print(c.valor());
c = null;
print(c.valor());
