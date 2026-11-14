"""Bloques basicos, vida de los temporales e informacion de siguiente uso.

Es el analisis que necesita `getReg()` (ver registers.py) para decidir que
registro liberar o reutilizar:

1. Se parte el cuerpo de una funcion en bloques basicos. Un bloque empieza
   en la primera instruccion, en cada etiqueta y despues de cada salto o
   `return`.
2. Se arma el grafo de flujo: un bloque sigue al que salta a su etiqueta y,
   si no termina en `goto`/`return`, al bloque siguiente. Dentro de un
   `try`, cualquier instruccion puede saltar al manejador, asi que los
   bloques del try tambien tienen como sucesor al bloque del `catch`.
3. Se calcula que temporales estan vivos al salir de cada bloque
   (analisis de flujo hacia atras, iterado hasta un punto fijo).
4. Dentro de cada bloque se recorre de abajo hacia arriba para saber, en
   cada instruccion, cual es el siguiente uso de cada operando.

Solo los temporales se analizan entre bloques. Las variables del programa
se consideran siempre vivas al salir de un bloque, porque su valor debe
quedar en memoria (otra funcion o un manejador de errores puede leerla).
"""

from ir import tac
from ir.tac import Quad, is_temp

# Siguiente uso de un valor que no se vuelve a usar dentro del bloque pero
# sigue vivo al salir de el (una variable, o un temporal vivo a la salida).
LIVE_OUT = float("inf")

_JUMPS = (tac.GOTO, tac.IF, tac.IF_FALSE)
_ENDS_BLOCK = (tac.GOTO, tac.IF, tac.IF_FALSE, tac.RETURN)


def uses_and_def(quad: Quad):
    """Operandos que la instruccion lee y el que escribe (o None)."""
    op = quad.op
    if op in (tac.ASSIGN, tac.UNARY, tac.LENGTH, tac.LOAD_FIELD):
        return [quad.arg1], quad.result
    if op in (tac.BINARY, tac.LOAD_INDEX):
        return [quad.arg1, quad.arg2], quad.result
    if op in (tac.IF, tac.IF_FALSE, tac.PARAM, tac.PRINT):
        return [quad.arg1], None
    if op == tac.RETURN:
        return ([quad.arg1] if quad.arg1 is not None else []), None
    if op == tac.CALL:
        # arg1 es una etiqueta, o un temporal con la direccion (llamada por vtable)
        return ([quad.arg1] if is_temp(quad.arg1) else []), quad.result
    if op == tac.STORE_INDEX:
        return [quad.result, quad.arg1, quad.arg2], None
    if op == tac.STORE_FIELD:
        return [quad.result, quad.arg2], None  # arg1 es el nombre del campo
    if op in (tac.NEW, tac.NEW_ARRAY, tac.CATCH):
        return [], quad.result
    return [], None


def is_variable(operand) -> bool:
    """Operandos con un lugar en memoria: temporales y variables (no literales ni etiquetas)."""
    if not isinstance(operand, str) or not operand:
        return False
    if operand[0] == '"' or operand[0] == "-" or operand[0].isdigit():
        return False
    return operand not in ("true", "false", "null")


class BasicBlock:
    def __init__(self, index: int, start: int, end: int):
        self.index = index
        self.start = start  # primera instruccion (indice en la funcion)
        self.end = end  # una despues de la ultima
        self.successors: list["BasicBlock"] = []
        self.use: set[str] = set()  # temporales leidos antes de escribirse en el bloque
        self.defs: set[str] = set()
        self.live_in: set[str] = set()
        self.live_out: set[str] = set()

    def __repr__(self):
        return f"B{self.index}[{self.start}:{self.end}]"


class FunctionFlow:
    """Bloques, grafo de flujo y siguiente uso de las instrucciones de una funcion."""

    def __init__(self, code: list[Quad]):
        self.code = code
        self.blocks = self._split_blocks()
        self.block_of = [None] * len(code)
        for block in self.blocks:
            for i in range(block.start, block.end):
                self.block_of[i] = block
        self._link_blocks()
        self._compute_liveness()
        # next_use[i][x]: indice del siguiente uso de x despues de la instruccion i,
        # LIVE_OUT si no se usa mas en el bloque pero sigue vivo, o ausente si esta muerto.
        self.next_use: list[dict] = [None] * len(code)
        for block in self.blocks:
            self._compute_next_use(block)

    # --- bloques y grafo ---------------------------------------------------

    def _split_blocks(self) -> list[BasicBlock]:
        leaders = {0} if self.code else set()
        for i, quad in enumerate(self.code):
            if quad.op == tac.LABEL:
                leaders.add(i)
            if quad.op in _ENDS_BLOCK and i + 1 < len(self.code):
                leaders.add(i + 1)
        starts = sorted(leaders)
        ends = starts[1:] + [len(self.code)]
        return [BasicBlock(n, s, e) for n, (s, e) in enumerate(zip(starts, ends))]

    def _link_blocks(self):
        label_block = {
            self.code[b.start].result: b for b in self.blocks if self.code[b.start].op == tac.LABEL
        }
        for n, block in enumerate(self.blocks):
            last = self.code[block.end - 1]
            if last.op in _JUMPS:
                block.successors.append(label_block[last.result])
            if last.op not in (tac.GOTO, tac.RETURN) and n + 1 < len(self.blocks):
                block.successors.append(self.blocks[n + 1])

        # Un error dentro de un try salta al manejador desde cualquier punto.
        for i, quad in enumerate(self.code):
            if quad.op != tac.TRY_BEGIN:
                continue
            handler = label_block[quad.result]
            for block in self.blocks[self.block_of[i].index:handler.index]:
                if handler not in block.successors:
                    block.successors.append(handler)

    # --- vida de los temporales entre bloques ------------------------------

    def _compute_liveness(self):
        for block in self.blocks:
            for quad in self.code[block.start:block.end]:
                uses, target = uses_and_def(quad)
                for operand in uses:
                    if is_temp(operand) and operand not in block.defs:
                        block.use.add(operand)
                if is_temp(target):
                    block.defs.add(target)

        changed = True
        while changed:
            changed = False
            for block in reversed(self.blocks):
                live_out = set().union(*(s.live_in for s in block.successors))
                live_in = block.use | (live_out - block.defs)
                if live_out != block.live_out or live_in != block.live_in:
                    block.live_out, block.live_in = live_out, live_in
                    changed = True

    # --- siguiente uso dentro de cada bloque -------------------------------

    def _compute_next_use(self, block: BasicBlock):
        # Estado al salir del bloque: las variables y los temporales vivos siguen vivos.
        table = {t: LIVE_OUT for t in block.live_out}
        for i in range(block.end - 1, block.start - 1, -1):
            self.next_use[i] = dict(table)
            uses, target = uses_and_def(self.code[i])
            if is_variable(target):
                if is_temp(target):
                    table.pop(target, None)
                else:
                    table[target] = LIVE_OUT  # una variable sigue viva aunque se reescriba
            for operand in uses:
                if is_variable(operand):
                    table[operand] = i

    def next_use_after(self, index: int, operand: str):
        """Siguiente uso de `operand` despues de la instruccion `index` (None si esta muerto)."""
        if not is_temp(operand):
            return self.next_use[index].get(operand, LIVE_OUT)
        return self.next_use[index].get(operand)

    def is_live_after(self, index: int, operand: str) -> bool:
        return self.next_use_after(index, operand) is not None

    def live_at_exit(self, block: BasicBlock, operand: str) -> bool:
        return not is_temp(operand) or operand in block.live_out
