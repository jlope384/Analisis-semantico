// Errores semanticos: variable redeclarada en el mismo ambito
// y condicion de if que no es boolean.
let x: integer = 1;
let x: integer = 2;
if (x) { print(x); }
