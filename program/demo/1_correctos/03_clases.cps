// Clases, herencia y despacho dinamico por vtable.
class Animal {
  let nombre: string;
  function constructor(nombre: string) { this.nombre = nombre; }
  function sonido(): string { return "..."; }
  function hablar(): string { return this.nombre + " dice " + this.sonido(); }
}
class Perro : Animal {
  function sonido(): string { return "guau"; }
}
class Gato : Animal {
  function sonido(): string { return "miau"; }
}
let perro: Animal = new Perro("Firulais");
let gato: Animal = new Gato("Michi");
let animales: Animal[] = [perro, gato];
foreach (a in animales) {
  print(a.hablar());
}
