"""Asignacion de registros: descriptores de registro/direccion y `getReg()`.

Cada valor del TAC (temporal o variable) tiene un lugar en memoria: los
temporales y las variables locales en el registro de activacion (`off($fp)`)
y las globales en el segmento de datos (`off($gp)`). Los registros funcionan
como una cache de esos lugares:

- **Descriptor de registro**: que valor tiene cada registro.
- **Descriptor de direccion**: en que registro esta cada valor.
- **Sucio**: el registro tiene un valor mas nuevo que el de la memoria.

Se respetan las clases de registros de MIPS:

- `$t0-$t9` (caller-saved) guardan temporales del TAC. Una llamada los
  puede destruir, asi que antes de cada `jal` se guardan los que siguen vivos.
- `$s0-$s7` (callee-saved) guardan variables. La funcion que los usa los
  guarda en su prologo y los restaura en su epilogo, asi que una variable
  local en `$s` sobrevive a las llamadas sin recargarse.
- `$f4-$f11, $f16-$f19` y `$f20-$f31` son las mismas dos clases para float.

`getReg(x)` elige el registro de x en este orden:

1. Si x ya esta en un registro, ese.
2. Un registro libre de su clase.
3. Un registro cuyo valor ya no se usa (temporal muerto): se reutiliza sin
   guardarlo.
4. El registro cuyo valor se usa mas lejos en el futuro (segun el siguiente
   uso de liveness.py), prefiriendo uno limpio. Si esta sucio se guarda
   (spill) en su lugar de memoria antes de reutilizarlo.

Al final de cada bloque basico los valores sucios que siguen vivos se
guardan en memoria y se vacian los descriptores, porque el siguiente bloque
puede llegar desde varios lados con registros distintos.
"""

from ir.tac import is_temp
from .liveness import FunctionFlow, LIVE_OUT

INT_TEMP = [f"$t{i}" for i in range(10)]
INT_SAVED = [f"$s{i}" for i in range(8)]
FLOAT_TEMP = [f"$f{i}" for i in (4, 5, 6, 7, 8, 9, 10, 11, 16, 17, 18, 19)]
FLOAT_SAVED = [f"$f{i}" for i in range(20, 32)]

CALLER_SAVED = set(INT_TEMP) | set(FLOAT_TEMP)
CALLEE_SAVED = INT_SAVED + FLOAT_SAVED


class RegisterAllocator:
    def __init__(self, flow: FunctionFlow, home, is_float, is_shared, emit):
        """
        flow:      bloques y siguiente uso de la funcion.
        home(x):   lugar de x en memoria, p.ej. '12($fp)'.
        is_float(x):  si x va en un registro de punto flotante.
        is_shared(x): si una llamada puede modificar x (globales y variables
                      compartidas con funciones anidadas).
        emit(linea): agrega una instruccion MIPS.
        """
        self.flow = flow
        self.home = home
        self.is_float = is_float
        self.is_shared = is_shared
        self.emit = emit
        self.registers: dict[str, str] = {}  # descriptor de registro: reg -> valor
        self.location: dict[str, str] = {}  # descriptor de direccion: valor -> reg
        self.dirty: set[str] = set()
        self.position = 0  # instruccion del TAC que se esta traduciendo
        self.locked: set[str] = set()  # registros que usa la instruccion actual
        self.used_saved: set[str] = set()  # $s / $f20+ usados (los guarda el prologo)

    # --- clases de registros ------------------------------------------------

    def _pool(self, value: str) -> list[str]:
        if self.is_float(value):
            return FLOAT_TEMP if is_temp(value) else FLOAT_SAVED
        return INT_TEMP if is_temp(value) else INT_SAVED

    def _load_op(self, value: str) -> str:
        return "lwc1" if self.is_float(value) else "lw"

    def _store_op(self, value: str) -> str:
        return "swc1" if self.is_float(value) else "sw"

    # --- instruccion actual --------------------------------------------------

    def begin_instruction(self, index: int):
        self.position = index
        self.locked = set()

    def _next_use(self, value: str):
        return self.flow.next_use_after(self.position, value)

    # --- getReg ---------------------------------------------------------------

    def get_reg(self, value: str, for_write: bool = False) -> str:
        """Registro para leer (`for_write=False`) o escribir `value` en la instruccion actual."""
        reg = self.location.get(value)
        if reg is not None and for_write and reg not in self._pool(value):
            # El temporal se reutiliza con otro tipo (p.ej. float -> boolean en
            # `t1 = t1 < t2`): su valor anterior ya se leyo, se suelta ese registro.
            del self.registers[reg]
            del self.location[value]
            self.dirty.discard(value)
            reg = None
        if reg is None:
            reg = self._choose_register(value)
            self._bind(reg, value)
            if not for_write:
                self.emit(f"{self._load_op(value):<5} {reg}, {self.home(value)}")
        if for_write:
            self.dirty.add(value)
        self.locked.add(reg)
        return reg

    def _choose_register(self, value: str) -> str:
        pool = self._pool(value)
        for reg in pool:
            if reg not in self.registers:
                return reg

        candidates = [r for r in pool if r not in self.locked]
        if not candidates:
            raise RuntimeError("no hay registros disponibles para la instruccion")

        def cost(reg):
            held = self.registers[reg]
            next_use = self._next_use(held)
            if next_use is None:
                return (0, 0)  # valor muerto: se reutiliza sin guardarlo
            distance = LIVE_OUT if next_use == LIVE_OUT else next_use
            # prefiere el uso mas lejano y, a igual distancia, el que no hay que guardar
            return (1, -distance, held in self.dirty)

        victim = min(candidates, key=cost)
        self._evict(victim)
        return victim

    def _bind(self, reg: str, value: str):
        self.registers[reg] = value
        self.location[value] = reg
        if reg in CALLEE_SAVED:
            self.used_saved.add(reg)

    def _evict(self, reg: str):
        value = self.registers.pop(reg)
        del self.location[value]
        if value in self.dirty:
            self.dirty.discard(value)
            if self._next_use(value) is not None:
                self.emit(f"{self._store_op(value):<5} {reg}, {self.home(value)}  # spill {value}")

    # --- despues de cada instruccion -----------------------------------------

    def release_dead(self):
        """Libera los registros de temporales que ya no se usan despues de la instruccion actual."""
        for reg, value in list(self.registers.items()):
            if is_temp(value) and self._next_use(value) is None:
                del self.registers[reg]
                del self.location[value]
                self.dirty.discard(value)

    # --- puntos de sincronizacion con la memoria -------------------------------

    def _store_dirty(self, keep_if):
        for reg, value in list(self.registers.items()):
            if value in self.dirty and keep_if(value):
                self.emit(f"{self._store_op(value):<5} {reg}, {self.home(value)}")
                self.dirty.discard(value)

    def store_live(self):
        """Guarda en memoria los valores sucios que siguen vivos, sin soltar los registros.

        Se usa antes de una instruccion que puede lanzar un error dentro de un
        try: el manejador lee los valores desde memoria.
        """
        self._store_dirty(lambda v: self._next_use(v) is not None or not is_temp(v))

    def end_block(self, block):
        """Fin de bloque basico: guarda lo que sigue vivo y vacia los descriptores."""
        self._store_dirty(lambda v: self.flow.live_at_exit(block, v))
        self.registers.clear()
        self.location.clear()
        self.dirty.clear()

    def before_call(self):
        """Antes de `jal`: guarda los valores vivos y olvida los que la llamada puede cambiar.

        Los registros caller-saved ($t, $f4-$f19) los puede destruir la
        funcion llamada. Las variables globales y las que comparte con una
        funcion anidada (closures) las puede modificar, asi que tambien se
        recargan despues. Las demas locales en $s se quedan: el llamado las
        preserva.
        """
        self._store_dirty(lambda v: self._next_use(v) is not None or not is_temp(v))
        for reg, value in list(self.registers.items()):
            if reg in CALLER_SAVED or self.is_shared(value):
                del self.registers[reg]
                del self.location[value]

    def forget_all(self):
        self.registers.clear()
        self.location.clear()
        self.dirty.clear()
