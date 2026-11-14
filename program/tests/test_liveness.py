from compiler import compile_source
from codegen.liveness import FunctionFlow, LIVE_OUT
from ir import tac


def flow_of(source: str, label: str = "main") -> FunctionFlow:
    result = compile_source(source)
    assert result.errors == []
    code, inside = [], False
    for quad in result.tac:
        if quad.op == tac.FUNC_BEGIN:
            inside = quad.arg1 == label
        elif quad.op == tac.FUNC_END:
            inside = False
        elif inside:
            code.append(quad)
    return FunctionFlow(code)


def test_straight_line_code_is_a_single_block():
    flow = flow_of("let a: integer = 1; let b: integer = a + 2; print(b);")
    assert len(flow.blocks) == 1


def test_labels_and_jumps_split_blocks_and_link_successors():
    flow = flow_of("let a: integer = 0; while (a < 3) { a = a + 1; }")
    # [a = 0] [L1: t1 = a < 3; ifFalse] [a = a + 1; goto L1] [L2:]
    assert len(flow.blocks) == 4
    entry, header, body, exit_ = flow.blocks
    assert entry.successors == [header]
    assert set(header.successors) == {body, exit_}
    assert body.successors == [header]


def test_temporary_dies_after_its_single_use():
    flow = flow_of("let a: integer = 1; let c: integer = (a * 2) + 3; print(c);")
    code = [str(q) for q in flow.code]
    product = code.index("t1 = a * 2")
    assert flow.next_use_after(product, "t1") == product + 1
    # 't1 = t1 + 3' consume t1 y lo vuelve a definir: el nuevo valor se usa en 'c = t1'
    assert flow.next_use_after(product + 1, "t1") == code.index("c = t1")
    last_use = code.index("c = t1")
    assert flow.next_use_after(last_use, "t1") is None


def test_variables_are_always_live_at_block_exit():
    flow = flow_of("let a: integer = 1; a = 2;")
    assert flow.next_use_after(len(flow.code) - 1, "a") == LIVE_OUT


def test_foreach_index_temporary_is_live_across_the_loop():
    flow = flow_of("let xs: integer[] = [1, 2]; foreach (x in xs) { print(x); }")
    header = next(b for b in flow.blocks if flow.code[b.start].op == tac.LABEL)
    # el indice y la longitud se usan en cada vuelta
    assert {"t1", "t2"} <= header.live_in


def test_try_blocks_flow_into_their_handler():
    flow = flow_of("""
        let xs: integer[] = [1];
        try { print(xs[3]); } catch (err) { print(err); }
    """)
    handler = next(b for b in flow.blocks if flow.code[b.start + 1].op == tac.CATCH)
    try_block = flow.block_of[next(i for i, q in enumerate(flow.code) if q.op == tac.TRY_BEGIN)]
    assert handler in try_block.successors
