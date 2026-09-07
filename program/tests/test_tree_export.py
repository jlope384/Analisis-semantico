from antlr4 import InputStream, CommonTokenStream

from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from tree_export import tree_to_dict, tree_to_dot


def parse(source: str):
    lexer = CompiscriptLexer(InputStream(source))
    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)
    tree = parser.program()
    return tree, parser.ruleNames


def test_tree_to_dict_has_expected_shape():
    tree, rule_names = parse("let x: integer = 1;")

    result = tree_to_dict(tree, rule_names)

    assert result["kind"] == "rule"
    assert result["label"] == "program"
    assert len(result["children"]) >= 1


def test_tree_to_dict_terminal_nodes_carry_position():
    tree, rule_names = parse("let x: integer = 1;")

    result = tree_to_dict(tree, rule_names)

    def find_tokens(node):
        if node["kind"] == "token":
            yield node
        else:
            for child in node["children"]:
                yield from find_tokens(child)

    tokens = list(find_tokens(result))
    assert any(t["label"] == "x" for t in tokens)
    assert all(t["line"] is not None for t in tokens)


def test_tree_to_dot_produces_valid_graph_structure():
    tree, rule_names = parse("let x: integer = 1;")

    dot = tree_to_dot(tree, rule_names)

    assert dot.startswith("digraph ParseTree {")
    assert dot.strip().endswith("}")
    assert "->" in dot
