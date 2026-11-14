"""Rutinas de soporte en ensamblador que se agregan a todo programa generado.

Solo usan los registros $a0-$a3, $v0 y $v1, asi que una llamada a ellas no
destruye los $t / $s donde el codigo generado guarda sus valores.

- `__concat`     $v0 = cadena nueva con $a0 seguido de $a1
- `__streq`      $v0 = 1 si las cadenas $a0 y $a1 son iguales
- `__print_str`  imprime la cadena $a0 ("null" si es 0)
- `__print_bool` imprime "true" o "false"
- `__raise`      lanza un error con el mensaje $a0: salta al manejador del
                 try mas reciente, o termina el programa si no hay ninguno
- `__err_index`, `__err_null`, `__err_div`: lanzan los errores en tiempo de ejecucion
"""

DATA = """\
__newline:      .asciiz "\\n"
__true:         .asciiz "true"
__false:        .asciiz "false"
__null:         .asciiz "null"
__empty:        .asciiz ""
__uncaught:     .asciiz "Error en tiempo de ejecucion: "
__msg_index:    .asciiz "indice fuera de rango"
__msg_null:     .asciiz "acceso a una referencia null"
__msg_div:      .asciiz "division entre cero"
                .align 2
__exception:    .word 0                 # mensaje del ultimo error lanzado
__handler_sp:   .word __handlers        # tope de la pila de manejadores de try
__handlers:     .space 768              # hasta 64 try anidados: (catch, $sp, $fp)
"""

TEXT = """\
# ---------------------------------------------------------------- runtime
__concat:                       # $v0 = $a0 + $a1
        bnez  $a0, __concat_a
        la    $a0, __empty
__concat_a:
        bnez  $a1, __concat_b
        la    $a1, __empty
__concat_b:
        li    $a2, 0            # longitud total
        move  $v1, $a0
__concat_len1:
        lb    $v0, 0($v1)
        beqz  $v0, __concat_len2_start
        addiu $a2, $a2, 1
        addiu $v1, $v1, 1
        j     __concat_len1
__concat_len2_start:
        move  $v1, $a1
__concat_len2:
        lb    $v0, 0($v1)
        beqz  $v0, __concat_alloc
        addiu $a2, $a2, 1
        addiu $v1, $v1, 1
        j     __concat_len2
__concat_alloc:
        move  $a3, $a0          # sbrk usa $a0
        addiu $a0, $a2, 1
        li    $v0, 9
        syscall                 # $v0 = buffer nuevo
        move  $a2, $v0
__concat_copy1:
        lb    $v1, 0($a3)
        beqz  $v1, __concat_copy2
        sb    $v1, 0($a2)
        addiu $a3, $a3, 1
        addiu $a2, $a2, 1
        j     __concat_copy1
__concat_copy2:
        lb    $v1, 0($a1)
        sb    $v1, 0($a2)
        beqz  $v1, __concat_end
        addiu $a1, $a1, 1
        addiu $a2, $a2, 1
        j     __concat_copy2
__concat_end:
        jr    $ra

__streq:                        # $v0 = ($a0 == $a1) por contenido
        li    $v0, 1
        beq   $a0, $a1, __streq_end
        li    $v0, 0
        beqz  $a0, __streq_end
        beqz  $a1, __streq_end
__streq_loop:
        lb    $a2, 0($a0)
        lb    $a3, 0($a1)
        bne   $a2, $a3, __streq_end
        li    $v0, 1
        beqz  $a2, __streq_end
        li    $v0, 0
        addiu $a0, $a0, 1
        addiu $a1, $a1, 1
        j     __streq_loop
__streq_end:
        jr    $ra

__print_str:
        bnez  $a0, __print_str_go
        la    $a0, __null
__print_str_go:
        li    $v0, 4
        syscall
        jr    $ra

__print_bool:
        la    $v1, __false
        beqz  $a0, __print_bool_go
        la    $v1, __true
__print_bool_go:
        move  $a0, $v1
        li    $v0, 4
        syscall
        jr    $ra

__err_index:
        la    $a0, __msg_index
        j     __raise
__err_null:
        la    $a0, __msg_null
        j     __raise
__err_div:
        la    $a0, __msg_div
        j     __raise

__raise:                        # $a0 = mensaje
        lw    $a1, __handler_sp
        la    $a2, __handlers
        beq   $a1, $a2, __raise_uncaught
        addiu $a1, $a1, -12     # saca el manejador mas reciente
        sw    $a1, __handler_sp
        sw    $a0, __exception
        lw    $sp, 4($a1)       # restaura la pila del try
        lw    $fp, 8($a1)
        lw    $a1, 0($a1)
        jr    $a1               # salta al catch
__raise_uncaught:
        move  $a1, $a0
        la    $a0, __uncaught
        li    $v0, 4
        syscall
        move  $a0, $a1
        li    $v0, 4
        syscall
        la    $a0, __newline
        li    $v0, 4
        syscall
        li    $a0, 1
        li    $v0, 17           # exit2 con codigo 1
        syscall
"""
