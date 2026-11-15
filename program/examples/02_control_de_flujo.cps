// if/else, while, do-while, for, break/continue y switch con fall-through.
let total: integer = 0;
let i: integer = 1;
while (i <= 10) {
  total = total + i;
  i = i + 1;
}
print(total);

do {
  i = i - 3;
} while (i > 0);
print(i);

for (let j: integer = 0; j < 10; j = j + 1) {
  if (j % 3 == 0) { continue; }
  if (j > 7) { break; }
  print(j);
}

function clasificar(n: integer): string {
  let r: string = "";
  switch (n) {
    case 1: r = "uno"; break;
    case 2: r = "dos, ";
    case 3: r = r + "tres"; break;
    default: r = "otro";
  }
  return r;
}
print(clasificar(1));
print(clasificar(2));
print(clasificar(3));
print(clasificar(9));
