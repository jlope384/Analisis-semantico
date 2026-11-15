"""Traduccion del TAC a ensamblador MIPS (MARS / SPIM).

Cada funcion del TAC se traduce por separado:

1. `FunctionFlow` (liveness.py) la parte en bloques basicos y calcula el
   siguiente uso de cada operando.
2. Cada cuadruplo se traduce a instrucciones MIPS. Los operandos se piden
   a `RegisterAllocator.get_reg` (registers.py), que decide en que
   registro esta cada valor y emite las cargas y los spills.
3. Al final se arman el prologo y el epilogo, que ya conocen los
   registros $s que uso la funcion.

Secuencia de llamada (ver CODEGEN.md):

    llamador                              llamado
    --------                              -------
    param x   -> addiu $sp,$sp,-4         addiu $sp,$sp,-F
                 sw    x, 0($sp)          sw $ra / $fp / $s usados
    call f, n -> (guarda valores vivos)   move $fp, $sp
                 jal   f                  copia los n argumentos a su
                 addiu $sp,$sp,4n         registro de activacion
                 resultado en $v0 / $f0   ... cuerpo ...
                                          restaura $s / $fp / $ra
                                          addiu $sp,$sp,F ; jr $ra

El marco de una funcion, desde $fp hacia arriba, es:

    [ registro de activacion (params, locales, temporales) | $s guardados | $fp viejo | $ra ] [ argumentos ]
      0($fp)                                                                                  F($fp)
"""

from ir import tac
from ir.tac import is_temp
from semantic import FloatType, StringType, BooleanType, IntegerType, ClassType, ArrayType, FunctionType, ThisSlot
from semantic.types_system import Type, INTEGER, FLOAT, STRING, BOOLEAN, NULL, VOID

from . import runtime
from .liveness import FunctionFlow
from .registers import RegisterAllocator, CALLEE_SAVED


class CodeGenError(Exception):
    """Construccion valida en el TAC que el backend no sabe traducir."""


class _Marker(Type):
    def __init__(self, name):
        self._name = name

    def __eq__(self, other):
        return self is other

    def __hash__(self):
        return id(self)

    @property
    def name(self):
        return self._name


VTABLE = _Marker("<vtable>")  # valor de `o.vtable`
CODE = _Marker("<metodo>")  # direccion de un metodo leida de la vtable

ARITHMETIC = {"+", "-", "*", "/", "%"}
RELATIONAL = {"<", "<=", ">", ">="}
EQUALITY = {"==", "!="}

INT_COMPARE = {"<": "slt", "<=": "sle", ">": "sgt", ">=": "sge", "==": "seq", "!=": "sne"}
# (instruccion, invertir operandos, invertir resultado) para comparar floats
FLOAT_COMPARE = {
    "<": ("c.lt.s", False, False), "<=": ("c.le.s", False, False),
    ">": ("c.lt.s", True, False), ">=": ("c.le.s", True, False),
    "==": ("c.eq.s", False, False), "!=": ("c.eq.s", False, True),
}


def function_label(label: str) -> str:
    """Etiqueta MIPS de una funcion del TAC ('Animal.hablar' -> 'fn_Animal__hablar')."""
    return "main" if label == "main" else "fn_" + label.replace(".", "__")


def literal_type(operand: str):
    if operand.startswith('"'):
        return STRING
    if operand in ("true", "false"):
        return BOOLEAN
    if operand == "null":
        return NULL
    if operand.lstrip("-").replace(".", "", 1).isdigit():
        return FLOAT if "." in operand else INTEGER
    return None


class MIPSGenerator:
    def __init__(self, program, generator, analyzer):
        self.program = program
        self.frames = generator.frames
        self.function_symbols = generator.function_symbols
        self.names = generator.names
        self.classes = {c.name: c for c in generator.classes}
        self.globals_size = analyzer.globals.size
        self.strings: dict[str, str] = {}  # literal -> etiqueta en .data
        self.floats: dict[str, str] = {}
        self._local_labels = 0
        # funcion (etiqueta) cuyo registro de activacion contiene a cada variable
        self.owner = {id(s): label for label, frame in self.frames.items() for s in frame.symbols}
        # variables locales que lee o escribe una funcion anidada (ver _find_captured)
        self.captured: set[int] = set()

    # --- anidamiento y enlaces de acceso (access links) ------------------------

    def _enclosing(self, label: str):
        """Etiqueta de la funcion que contiene a `label` (None si no es anidada)."""
        symbol = self.function_symbols.get(label)
        outer = symbol.enclosing_function if symbol is not None else None
        return outer.label if outer is not None else None

    def _depth(self, label: str) -> int:
        symbol = self.function_symbols.get(label)
        return symbol.nesting_depth if symbol is not None else 0

    def _has_link(self, label: str) -> bool:
        """Una funcion anidada recibe un enlace de acceso al marco de la que la contiene."""
        return self._enclosing(label) is not None

    def _link_offset(self, label: str) -> int:
        """Offset (desde $fp) donde la funcion guarda su enlace de acceso: justo despues
        de su registro de activacion, que el TAC ya dimensiono."""
        return self.frames[label].total_size

    def _load_link(self, hops: int) -> str:
        """Deja en $k1 el $fp del marco `hops` niveles hacia afuera siguiendo la cadena de enlaces."""
        label = self.label
        self._emit(f"lw    $k1, {self._link_offset(label)}($fp)   # enlace de acceso")
        for _ in range(hops - 1):
            label = self._enclosing(label)
            self._emit(f"lw    $k1, {self._link_offset(label)}($k1)")
        return "$k1"

    def _hops(self, symbol) -> int:
        """Niveles que hay que subir por la cadena de enlaces para llegar al marco de `symbol`
        (0 si es de la funcion actual)."""
        owner = self.owner.get(id(symbol), self.label)
        if owner == self.label:
            return 0
        hops, label = 0, self.label
        while label is not None and label != owner:
            label = self._enclosing(label)
            hops += 1
        if label is None:
            raise CodeGenError(f"'{symbol.name}' no pertenece a una funcion que contenga a {self.label}")
        return hops

    def _find_captured(self, functions):
        """Marca las variables locales que usa una funcion anidada: una llamada puede
        cambiarlas, asi que no se pueden mantener en un registro a traves de ella."""
        for label, code in functions:
            for quad in code:
                for operand in (quad.arg1, quad.arg2, quad.result):
                    if not isinstance(operand, str) or is_temp(operand) or literal_type(operand):
                        continue
                    symbol = self._lookup(label, operand)
                    if symbol is not None and symbol.storage != "global" \
                            and self.owner.get(id(symbol), label) != label:
                        self.captured.add(id(symbol))

    # ------------------------------------------------------------------
    # programa completo
    # ------------------------------------------------------------------

    def generate(self) -> str:
        functions, current = [], None
        for quad in self.program:
            if quad.op == tac.FUNC_BEGIN:
                current = (quad.arg1, [])
            elif quad.op == tac.FUNC_END:
                functions.append(current)
                current = None
            else:
                current[1].append(quad)

        # main va primero: MARS empieza a ejecutar en la primera instruccion de .text
        functions.sort(key=lambda f: f[0] != "main")
        self._find_captured(functions)
        text = []
        for label, code in functions:
            text += self._function(label, code)

        out = [".data", "        .align 2", f"__globals:      .space {max(self.globals_size, 4)}"]
        for class_symbol in self.classes.values():
            methods = [function_label(m.label) for m in class_symbol.vtable()] or ["0"]
            out.append(f"__vt_{class_symbol.name}: .word {', '.join(methods)}")
        for literal, label in self.strings.items():
            out.append(f"{label}: .asciiz {literal}")
        out.append("        .align 2")
        for literal, label in self.floats.items():
            out.append(f"{label}: .float {literal}")
        out += runtime.DATA.splitlines()
        out += ["", ".text", ".globl main"]
        out += text
        out += runtime.TEXT.splitlines()
        return "\n".join(out) + "\n"

    # ------------------------------------------------------------------
    # una funcion
    # ------------------------------------------------------------------

    def _function(self, label: str, code: list) -> list[str]:
        self.label = label
        self.frame = self.frames[label]
        self.symbol = self.function_symbols.get(label)
        self.temp_types: dict[str, Type] = {}
        self.code = code
        self.flow = FunctionFlow(code)
        self.has_try = any(q.op == tac.TRY_BEGIN for q in code)
        self.exit_label = "__main_exit" if label == "main" else f"ret_{function_label(label)}"
        self.body: list[str] = []
        self.alloc = RegisterAllocator(self.flow, self._home, self._is_float, self._is_shared, self._emit)
        self.call_of_param = self._match_params(code)

        for i, quad in enumerate(code):
            block = self.flow.block_of[i]
            self.alloc.begin_instruction(i)
            self.body.append(f"        # {quad}" if quad.op != tac.LABEL else f"{quad.result}:")
            if quad.op in (tac.GOTO, tac.IF, tac.IF_FALSE, tac.RETURN):
                # los saltos guardan los valores vivos antes de saltar (fin de bloque)
                getattr(self, "_t_" + quad.op.replace("False", "_false"))(quad, block)
                self.alloc.forget_all()
                continue
            if quad.op != tac.LABEL:
                getattr(self, "_t_" + quad.op.replace("=", "assign"))(quad)
            self.alloc.release_dead()
            if i == block.end - 1:
                self.alloc.end_block(block)

        return self._prologue() + self.body + self._epilogue()

    def _match_params(self, code):
        """param -> (call, posicion): los param de una llamada se emiten justo antes del call."""
        matches = {}
        for i, quad in enumerate(code):
            if quad.op == tac.CALL:
                count = int(quad.arg2)
                for position in range(count):
                    matches[i - count + position] = (quad, position)
        return matches

    def _saved_base(self) -> int:
        """Offset del area de $s guardados: despues del registro de activacion y del enlace."""
        return self.frame.total_size + (4 if self._has_link(self.label) else 0)

    def _frame_size(self) -> int:
        size = self._saved_base() + 4 * len(self._saved_registers()) + 8
        return (size + 7) // 8 * 8

    def _saved_registers(self) -> list[str]:
        return [r for r in CALLEE_SAVED if r in self.alloc.used_saved]

    def _prologue(self) -> list[str]:
        name = function_label(self.label)
        if self.label == "main":
            return [
                "main:",
                "        la    $gp, __globals",
                f"        addiu $sp, $sp, -{max(self.frame.total_size, 4)}",
                "        move  $fp, $sp",
            ]
        size, base = self._frame_size(), self._saved_base()
        lines = [f"{name}:", f"        addiu $sp, $sp, -{size}",
                 f"        sw    $ra, {size - 4}($sp)", f"        sw    $fp, {size - 8}($sp)"]
        for j, reg in enumerate(self._saved_registers()):
            store = "swc1" if reg.startswith("$f") else "sw"
            lines.append(f"        {store:<5} {reg}, {base + 4 * j}($sp)")
        lines.append("        move  $fp, $sp")
        # el enlace de acceso es lo ultimo que apila el llamador: queda en F($fp)
        link = 4 if self._has_link(self.label) else 0
        if link:
            lines.append(f"        lw    $a2, {size}($fp)   # enlace de acceso")
            lines.append(f"        sw    $a2, {self._link_offset(self.label)}($fp)")
        params = self.frame.params
        for i, param in enumerate(params):
            incoming = size + link + 4 * (len(params) - 1 - i)
            lines.append(f"        lw    $a2, {incoming}($fp)   # argumento {param.name}")
            lines.append(f"        sw    $a2, {param.offset}($fp)")
        return lines

    def _epilogue(self) -> list[str]:
        if self.label == "main":
            return ["__main_exit:", "        li    $v0, 10", "        syscall", ""]
        size, base = self._frame_size(), self._saved_base()
        lines = [f"{self.exit_label}:"]
        for j, reg in enumerate(self._saved_registers()):
            load = "lwc1" if reg.startswith("$f") else "lw"
            lines.append(f"        {load:<5} {reg}, {base + 4 * j}($fp)")
        lines += [
            f"        lw    $ra, {size - 4}($fp)",
            "        move  $sp, $fp",
            f"        lw    $fp, {size - 8}($sp)",
            f"        addiu $sp, $sp, {size}",
            "        jr    $ra",
            "",
        ]
        return lines

    # ------------------------------------------------------------------
    # operandos: ubicacion, tipo y registros
    # ------------------------------------------------------------------

    def _emit(self, line: str):
        self.body.append("        " + line)

    def _new_label(self, hint: str) -> str:
        self._local_labels += 1
        return f"__{hint}_{self._local_labels}"

    def _symbol(self, operand: str):
        if operand == "this":
            this = self.frame.params[0] if self.frame.params else None
            if not isinstance(this, ThisSlot):
                raise CodeGenError(f"'this' fuera de un metodo en {self.label}")
            return this
        symbol = self._lookup(self.label, operand)
        if symbol is None:
            raise CodeGenError(f"operando desconocido '{operand}' en {self.label}")
        return symbol

    def _lookup(self, label: str, operand: str):
        """Simbolo de `operand` visto desde la funcion `label`: primero sus propios nombres,
        luego los de las funciones que la contienen (closures) y al final los globales."""
        current = label
        while current is not None:
            symbol = self.names.get(current, {}).get(operand)
            if symbol is not None:
                return symbol
            current = self._enclosing(current)
        return self.names["global"].get(operand)

    def _home(self, operand: str) -> str:
        if is_temp(operand):
            return f"{self.frame.size + 8 * (int(operand[1:]) - 1)}($fp)"
        symbol = self._symbol(operand)
        if symbol.storage == "global":
            return f"{symbol.offset}($gp)"
        hops = self._hops(symbol)
        if hops:
            # variable de una funcion externa: se sigue la cadena de enlaces de acceso
            return f"{symbol.offset}({self._load_link(hops)})"
        return f"{symbol.offset}($fp)"

    def _is_shared(self, operand: str) -> bool:
        """Valor que una llamada puede modificar: globales, variables de una funcion
        externa y locales capturadas por una funcion anidada. No se conservan en un
        registro a traves de una llamada."""
        if is_temp(operand) or operand == "this":
            return False
        symbol = self._symbol(operand)
        return symbol.storage == "global" or id(symbol) in self.captured or self._hops(symbol) > 0

    def _type(self, operand: str):
        if is_temp(operand):
            return self.temp_types.get(operand)
        literal = literal_type(operand)
        if literal is not None:
            return literal
        return self._symbol(operand).type

    def _is_float(self, operand: str) -> bool:
        return isinstance(self._type(operand), FloatType)

    def _string_label(self, literal: str) -> str:
        if literal not in self.strings:
            self.strings[literal] = f"__str_{len(self.strings)}"
        return self.strings[literal]

    def _read(self, operand: str, scratch: str) -> str:
        """Registro entero con el valor de `operand` (los literales se cargan en `scratch`)."""
        literal = literal_type(operand)
        if literal is None:
            return self.alloc.get_reg(operand)
        if literal == STRING:
            self._emit(f"la    {scratch}, {self._string_label(operand)}")
        elif literal == FLOAT:
            raise CodeGenError(f"float '{operand}' usado como entero")
        else:
            value = {"true": "1", "false": "0", "null": "0"}.get(operand, operand)
            self._emit(f"li    {scratch}, {value}")
        return scratch

    def _read_float(self, operand: str, scratch: str) -> str:
        """Registro float con el valor de `operand`; un entero se convierte (promocion)."""
        if literal_type(operand) == FLOAT:
            if operand not in self.floats:
                self.floats[operand] = f"__flt_{len(self.floats)}"
            self._emit(f"l.s   {scratch}, {self.floats[operand]}")
            return scratch
        if self._is_float(operand):
            return self.alloc.get_reg(operand)
        reg = self._read(operand, "$v1")
        self._emit(f"mtc1  {reg}, {scratch}")
        self._emit(f"cvt.s.w {scratch}, {scratch}")
        return scratch

    def _write(self, operand: str, type_=None) -> str:
        if is_temp(operand):
            self.temp_types[operand] = type_
        return self.alloc.get_reg(operand, for_write=True)

    def _move_into(self, target: str, value: str, target_type):
        """target = value, convirtiendo integer -> float si el destino es float."""
        if isinstance(target_type, FloatType):
            src = self._read_float(value, "$f2")
            dst = self._write(target, target_type)
            if dst != src:
                self._emit(f"mov.s {dst}, {src}")
        else:
            src = self._read(value, "$a2")
            dst = self._write(target, target_type)
            if dst != src:
                self._emit(f"move  {dst}, {src}")

    def _guard(self):
        """Antes de una instruccion que puede lanzar un error: si la funcion
        tiene try, los valores vivos deben estar en memoria para el catch."""
        if self.has_try:
            self.alloc.store_live()

    # ------------------------------------------------------------------
    # traduccion de cada instruccion
    # ------------------------------------------------------------------

    def _t_assign(self, quad):
        target_type = self._type(quad.arg1) if is_temp(quad.result) else self._type(quad.result)
        self._move_into(quad.result, quad.arg1, target_type)

    def _t_binary(self, quad):
        op, left, right = quad.operator, quad.arg1, quad.arg2
        lt, rt = self._type(left), self._type(right)
        is_string = isinstance(lt, StringType) and isinstance(rt, StringType)
        is_float = isinstance(lt, FloatType) or isinstance(rt, FloatType)

        if op in ARITHMETIC:
            if is_string:
                self._runtime_call("__concat", quad.result, STRING, left, right)
            elif is_float:
                self._float_arithmetic(op, quad.result, left, right)
            else:
                self._int_arithmetic(op, quad.result, left, right)
            return

        if op in EQUALITY and is_string:
            self._runtime_call("__streq", quad.result, BOOLEAN, left, right)
            if op == "!=":
                reg = self.alloc.get_reg(quad.result, for_write=True)
                self._emit(f"xori  {reg}, {reg}, 1")
            return

        if is_float:
            instruction, swap, negate = FLOAT_COMPARE[op]
            a, b = self._read_float(left, "$f2"), self._read_float(right, "$f3")
            if swap:
                a, b = b, a
            dst = self._write(quad.result, BOOLEAN)
            done = self._new_label("fcmp")
            self._emit(f"{instruction} {a}, {b}")
            self._emit(f"li    {dst}, {0 if negate else 1}")
            self._emit(f"bc1t  {done}")
            self._emit(f"li    {dst}, {1 if negate else 0}")
            self.body.append(f"{done}:")
            return

        a, b = self._read(left, "$a2"), self._read(right, "$a3")
        dst = self._write(quad.result, BOOLEAN)
        self._emit(f"{INT_COMPARE[op]}   {dst}, {a}, {b}")

    def _int_arithmetic(self, op, result, left, right):
        a = self._read(left, "$a2")
        small = literal_type(right) == INTEGER and -32768 <= int(right) <= 32767
        if op in "+-" and small:
            dst = self._write(result, INTEGER)
            self._emit(f"addiu {dst}, {a}, {int(right) if op == '+' else -int(right)}")
            return
        b = self._read(right, "$a3")
        if op in "/%":
            self._guard()
            self._emit(f"beqz  {b}, __err_div")
            self._emit(f"div   {a}, {b}")
            dst = self._write(result, INTEGER)
            self._emit(f"{'mflo' if op == '/' else 'mfhi'}  {dst}")
            return
        dst = self._write(result, INTEGER)
        instruction = {"+": "addu", "-": "subu", "*": "mul"}[op]
        self._emit(f"{instruction}  {dst}, {a}, {b}")

    def _float_arithmetic(self, op, result, left, right):
        a, b = self._read_float(left, "$f2"), self._read_float(right, "$f3")
        dst = self._write(result, FLOAT)
        if op == "%":  # a - trunc(a / b) * b
            self._emit(f"div.s $f1, {a}, {b}")
            self._emit("trunc.w.s $f1, $f1")
            self._emit("cvt.s.w $f1, $f1")
            self._emit(f"mul.s $f1, $f1, {b}")
            self._emit(f"sub.s {dst}, {a}, $f1")
            return
        instruction = {"+": "add.s", "-": "sub.s", "*": "mul.s", "/": "div.s"}[op]
        self._emit(f"{instruction} {dst}, {a}, {b}")

    def _runtime_call(self, routine, result, result_type, left, right):
        a, b = self._read(left, "$a2"), self._read(right, "$a3")
        self._emit(f"move  $a0, {a}")
        self._emit(f"move  $a1, {b}")
        self._emit(f"jal   {routine}")
        dst = self._write(result, result_type)
        self._emit(f"move  {dst}, $v0")

    def _t_unary(self, quad):
        if quad.operator == "!":
            src = self._read(quad.arg1, "$a2")
            dst = self._write(quad.result, BOOLEAN)
            self._emit(f"xori  {dst}, {src}, 1")
        elif self._is_float(quad.arg1):
            src = self._read_float(quad.arg1, "$f2")
            dst = self._write(quad.result, FLOAT)
            self._emit(f"neg.s {dst}, {src}")
        else:
            src = self._read(quad.arg1, "$a2")
            dst = self._write(quad.result, self._type(quad.arg1))
            self._emit(f"subu  {dst}, $zero, {src}")

    # --- control de flujo -------------------------------------------------

    def _t_goto(self, quad, block):
        self.alloc.end_block(block)
        self._emit(f"j     {quad.result}")

    def _t_if(self, quad, block, branch="bnez"):
        reg = self._read(quad.arg1, "$a2")
        self.alloc.end_block(block)  # solo guarda en memoria, no cambia `reg`
        self._emit(f"{branch}  {reg}, {quad.result}")

    def _t_if_false(self, quad, block):
        self._t_if(quad, block, "beqz")

    def _t_return(self, quad, block):
        if quad.arg1 is not None:
            return_type = self.symbol.return_type if self.symbol is not None else None
            if isinstance(return_type, FloatType) or self._is_float(quad.arg1):
                self._emit(f"mov.s $f0, {self._read_float(quad.arg1, '$f2')}")
            else:
                self._emit(f"move  $v0, {self._read(quad.arg1, '$a2')}")
        self.alloc.end_block(block)
        self._emit(f"j     {self.exit_label}")

    # --- llamadas ---------------------------------------------------------

    def _param_types(self, call) -> list:
        if call.arg1 in self.frames:
            return [p.type for p in self.frames[call.arg1].params]
        if isinstance(call.type, FunctionType):
            return [None] + list(call.type.param_types)
        return []

    def _t_param(self, quad):
        call, position = self.call_of_param[self.alloc.position]
        types = self._param_types(call)
        expected = types[position] if position < len(types) else None
        self._emit("addiu $sp, $sp, -4")
        if isinstance(expected, FloatType) or self._is_float(quad.arg1):
            self._emit(f"swc1  {self._read_float(quad.arg1, '$f2')}, 0($sp)")
        else:
            self._emit(f"sw    {self._read(quad.arg1, '$a2')}, 0($sp)")

    def _t_call(self, quad):
        if quad.arg1 in self.frames:
            symbol = self.function_symbols.get(quad.arg1)
            return_type = symbol.return_type if symbol is not None else VOID
            target = None
        elif is_temp(quad.arg1):
            return_type = quad.type.return_type if isinstance(quad.type, FunctionType) else None
            target = self._read(quad.arg1, "$a2")
            self._emit(f"move  $v1, {target}")
        else:
            raise CodeGenError(f"llamada a '{quad.arg1}', que no es una funcion conocida")

        self.alloc.before_call()
        pushed = int(quad.arg2)
        if target is None and self._has_link(quad.arg1):
            self._push_link(quad.arg1)
            pushed += 1
        self._emit("jalr  $v1" if target is not None else f"jal   {function_label(quad.arg1)}")
        if pushed:
            self._emit(f"addiu $sp, $sp, {4 * pushed}")
        if quad.result is not None:
            dst = self._write(quad.result, return_type)
            self._emit(f"mov.s {dst}, $f0" if isinstance(return_type, FloatType) else f"move  {dst}, $v0")

    def _push_link(self, callee: str):
        """Apila el enlace de acceso de `callee`: el $fp del marco de la funcion que lo contiene.

        Si el llamador es esa funcion, es su propio $fp. Si no (recursion, llamada
        a una funcion hermana o desde mas adentro), se sube por la cadena de
        enlaces la diferencia de profundidades + 1.
        """
        hops = self._depth(self.label) - self._depth(callee) + 1
        link = self._load_link(hops) if hops > 0 else "$fp"
        self._emit("addiu $sp, $sp, -4")
        self._emit(f"sw    {link}, 0($sp)   # enlace de acceso de {callee}")

    # --- objetos ----------------------------------------------------------

    def _field(self, obj: str, name: str):
        class_type = self._type(obj)
        class_symbol = getattr(class_type, "class_symbol", None)
        field = class_symbol.resolve_member(name) if class_symbol is not None else None
        if field is None or field.offset is None:
            raise CodeGenError(f"no se encontro el campo '{name}' de '{obj}'")
        return field

    def _t_new(self, quad):
        class_symbol = self.classes[quad.arg1]
        self._emit(f"li    $a0, {quad.arg2}")
        self._emit("li    $v0, 9")
        self._emit("syscall")
        self._emit(f"la    $v1, __vt_{class_symbol.name}")
        self._emit("sw    $v1, 0($v0)")
        dst = self._write(quad.result, class_symbol.type)
        self._emit(f"move  {dst}, $v0")

    def _t_load_field(self, quad):
        obj = self._read(quad.arg1, "$a2")
        if quad.arg2 == "vtable":
            # llamar un metodo sobre null es un error en tiempo de ejecucion, no un fallo de MARS
            self._guard()
            self._emit(f"beqz  {obj}, __err_null")
            dst = self._write(quad.result, VTABLE)
            self._emit(f"lw    {dst}, 0({obj})")
            return
        field = self._field(quad.arg1, quad.arg2)
        self._guard()
        self._emit(f"beqz  {obj}, __err_null")
        dst = self._write(quad.result, field.type)
        load = "lwc1" if isinstance(field.type, FloatType) else "lw"
        self._emit(f"{load}  {dst}, {field.offset}({obj})")

    def _t_store_field(self, quad):
        field = self._field(quad.result, quad.arg1)
        obj = self._read(quad.result, "$a2")
        if isinstance(field.type, FloatType):
            value, store = self._read_float(quad.arg2, "$f2"), "swc1"
        else:
            value, store = self._read(quad.arg2, "$a3"), "sw"
        self._guard()
        self._emit(f"beqz  {obj}, __err_null")
        self._emit(f"{store}  {value}, {field.offset}({obj})")

    # --- arreglos: [ longitud | elemento 0 | elemento 1 | ... ], 4 bytes cada uno

    def _t_new_array(self, quad):
        length = int(quad.arg1)
        self._emit(f"li    $a0, {4 + 4 * length}")
        self._emit("li    $v0, 9")
        self._emit("syscall")
        self._emit(f"li    $v1, {length}")
        self._emit("sw    $v1, 0($v0)")
        dst = self._write(quad.result, quad.type)
        self._emit(f"move  {dst}, $v0")

    def _element_address(self, array: str, index: str):
        """Deja en $v1 la direccion del elemento (menos 4), verificando null y limites."""
        self._emit(f"beqz  {array}, __err_null")
        self._emit(f"lw    $v1, 0({array})")
        self._emit(f"sltu  $v1, {index}, $v1")  # sin signo: un indice negativo tambien falla
        self._emit("beqz  $v1, __err_index")
        self._emit(f"sll   $v1, {index}, 2")
        self._emit(f"addu  $v1, $v1, {array}")

    def _t_load_index(self, quad):
        if self._type(quad.arg1) is VTABLE:
            table = self._read(quad.arg1, "$a2")
            dst = self._write(quad.result, CODE)
            self._emit(f"lw    {dst}, {4 * int(quad.arg2)}({table})")
            return
        element = getattr(self._type(quad.arg1), "element_type", None)
        self._guard()
        array, index = self._read(quad.arg1, "$a2"), self._read(quad.arg2, "$a3")
        self._element_address(array, index)
        target_type = element if is_temp(quad.result) else self._type(quad.result)
        dst = self._write(quad.result, target_type)
        self._emit(f"{'lwc1' if isinstance(target_type, FloatType) else 'lw'}  {dst}, 4($v1)")

    def _t_store_index(self, quad):
        element = getattr(self._type(quad.result), "element_type", None)
        self._guard()
        array, index = self._read(quad.result, "$a2"), self._read(quad.arg1, "$a3")
        if isinstance(element, FloatType):
            value, store = self._read_float(quad.arg2, "$f2"), "swc1"
        else:
            value, store = self._read(quad.arg2, "$a1"), "sw"
        self._element_address(array, index)
        self._emit(f"{store}  {value}, 4($v1)")

    def _t_len(self, quad):
        array = self._read(quad.arg1, "$a2")
        self._guard()
        self._emit(f"beqz  {array}, __err_null")
        dst = self._write(quad.result, INTEGER)
        self._emit(f"lw    {dst}, 0({array})")

    # --- print ------------------------------------------------------------

    def _t_print(self, quad):
        value_type = self._type(quad.arg1)
        if isinstance(value_type, FloatType):
            self._emit(f"mov.s $f12, {self._read_float(quad.arg1, '$f2')}")
            self._emit("li    $v0, 2")
            self._emit("syscall")
        else:
            self._emit(f"move  $a0, {self._read(quad.arg1, '$a2')}")
            if isinstance(value_type, StringType):
                self._emit("jal   __print_str")
            elif isinstance(value_type, BooleanType):
                self._emit("jal   __print_bool")
            else:
                self._emit("li    $v0, 1")
                self._emit("syscall")
        self._emit("li    $a0, 10")
        self._emit("li    $v0, 11")
        self._emit("syscall")

    # --- try / catch ------------------------------------------------------

    def _t_try_begin(self, quad):
        """Apila (direccion del catch, $sp, $fp) en la pila de manejadores."""
        self._emit("lw    $a1, __handler_sp")
        self._emit(f"la    $v1, {quad.result}")
        self._emit("sw    $v1, 0($a1)")
        self._emit("sw    $sp, 4($a1)")
        self._emit("sw    $fp, 8($a1)")
        self._emit("addiu $a1, $a1, 12")
        self._emit("sw    $a1, __handler_sp")

    def _t_try_end(self, quad):
        self._emit("lw    $a1, __handler_sp")
        self._emit("addiu $a1, $a1, -12")
        self._emit("sw    $a1, __handler_sp")

    def _t_catch(self, quad):
        dst = self._write(quad.result, STRING)
        self._emit(f"lw    {dst}, __exception")


def generate_mips(program, generator, analyzer) -> str:
    return MIPSGenerator(program, generator, analyzer).generate()
