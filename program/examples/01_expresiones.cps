// Aritmetica entera y float, precedencia, logicos con cortocircuito y strings.
let a: integer = 17;
let b: integer = 5;
print(a + b * 2);
print((a + b) * 2);
print(a / b);
print(a % b);
print(-a + 3);

let x: float = 2.5;
let y: float = x * 4 + 0.5;
print(y);
print(y / 2);

print(a > b && b > 10);
print(a > b || b > 10);
print(!(a == 17));

let saludo: string = "hola";
let completo: string = saludo + " " + "mundo";
print(completo);
print(completo == "hola mundo");
print(a > 10 ? "grande" : "pequeno");
