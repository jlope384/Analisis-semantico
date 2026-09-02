let a: integer = 10;
let b: string = "hola";
let c: boolean = true;
let d = null;

const PI: integer = 314;

function saludar(nombre: string): string {
  return "Hola " + nombre;
}

let mensaje = saludar("Mundo");
print(mensaje);

class Animal {
  let nombre: string;

  function constructor(nombre: string) {
    this.nombre = nombre;
  }

  function hablar(): string {
    return this.nombre + " hace ruido.";
  }
}

class Perro : Animal {
  function hablar(): string {
    return this.nombre + " ladra.";
  }
}

let perro: Perro = new Perro("Toby");
print(perro.hablar());

let notas: integer[] = [90, 85, 100];

for (let i: integer = 0; i < 3; i = i + 1) {
  print(notas[i]);
}

foreach (nota in notas) {
  if (nota < 60) {
    continue;
  }
  if (nota == 100) {
    break;
  }
  print(nota);
}

function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}

print(factorial(5));
