"""Exportadores de la representacion visual del arbol sintactico.

Convierte un ParseTree de ANTLR en:
  - un dict serializable a JSON (usado por el servidor LSP para pintarlo
    en un panel de VS Code), y
  - un grafo Graphviz DOT (para generar una imagen sin depender de VS Code).

No conoce reglas semanticas, solo la forma del arbol que ya construyo ANTLR.
"""

from antlr4.tree.Tree import TerminalNode


def tree_to_dict(node, rule_names) -> dict:
    """Representa `node` (y sus hijos) como un dict con forma de arbol."""
    if isinstance(node, TerminalNode):
        symbol = node.getSymbol()
        return {
            "kind": "token",
            "label": node.getText(),
            "line": symbol.line if symbol else None,
            "column": symbol.column if symbol else None,
        }

    start = node.start
    return {
        "kind": "rule",
        "label": rule_names[node.getRuleIndex()],
        "line": start.line if start else None,
        "column": start.column if start else None,
        "children": [tree_to_dict(child, rule_names) for child in (node.children or [])],
    }


def tree_to_dot(node, rule_names) -> str:
    """Genera un grafo Graphviz DOT del arbol, para renderizar `dot -Tpng`."""
    lines = ["digraph ParseTree {", '  node [fontname="Helvetica"];']
    counter = [0]

    def visit(node) -> int:
        node_id = counter[0]
        counter[0] += 1

        if isinstance(node, TerminalNode):
            label = node.getText().replace("\\", "\\\\").replace('"', '\\"')
            lines.append(f'  n{node_id} [label="{label}", shape=ellipse, style=filled, fillcolor="#fff3bf"];')
            return node_id

        label = rule_names[node.getRuleIndex()]
        lines.append(f'  n{node_id} [label="{label}", shape=box, style=filled, fillcolor="#d0ebff"];')
        for child in node.children or []:
            child_id = visit(child)
            lines.append(f"  n{node_id} -> n{child_id};")
        return node_id

    visit(node)
    lines.append("}")
    return "\n".join(lines)
