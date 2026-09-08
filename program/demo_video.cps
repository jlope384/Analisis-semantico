// Archivo de demo para el video.
// Empieza SIN errores. Durante la grabacion, descomenta UNA linea "BUG N"
// a la vez, guarda (Cmd+S / Ctrl+S) y muestra el subrayado rojo que aparece
// en VS Code. Luego vuelve a comentarla antes de pasar al siguiente bug.

let edad: integer = 25;
let nombre: string = "Ana";
let activo: boolean = true;

// BUG 1 (tipos en asignacion): descomenta para ver el error de tipo
// edad = "no soy un entero";

// BUG 2 (logica): && exige booleanos en ambos lados
// let resultado: boolean = edad && activo;

const PI: float = 3.14;
// BUG 3 (const sin inicializar en su declaracion): la gramatica misma exige
// el '=' en una constante, asi que esto se marca como error de sintaxis
// (igual aparece subrayado en rojo en el editor). Descomenta para verla:
// const LIMITE: integer;

function calcularArea(radio: float): float {
  return PI * radio * radio;
}

print(calcularArea(2.0));

class Persona {
  let nombreCompleto: string;

  function constructor(nombreCompleto: string) {
    this.nombreCompleto = nombreCompleto;
  }

  function saludar(): string {
    return "Hola, soy " + this.nombreCompleto;
  }
}

let persona: Persona = new Persona("Carlos");
print(persona.saludar());

// BUG 4 (miembro inexistente en una clase): descomenta para ver el error
// print(persona.correo);

while (edad > 0) {
  edad = edad - 1;
  if (edad == 10) {
    break;
  }
}

// BUG 5 (control de flujo): 'break' fuera de cualquier bucle o switch
// break;
