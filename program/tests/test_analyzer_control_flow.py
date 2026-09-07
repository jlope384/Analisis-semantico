from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker

from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from analyzer import SemanticAnalyzer


def analyze(source: str) -> SemanticAnalyzer:
    lexer = CompiscriptLexer(InputStream(source))
    tokens = CommonTokenStream(lexer)
    parser = CompiscriptParser(tokens)
    tree = parser.program()

    analyzer = SemanticAnalyzer()
    ParseTreeWalker.DEFAULT.walk(analyzer, tree)
    return analyzer


def messages(analyzer: SemanticAnalyzer):
    return [e.message for e in analyzer.errors]


def test_break_outside_loop_is_reported():
    analyzer = analyze("break;")

    assert len(analyzer.errors) == 1
    assert "break" in messages(analyzer)[0]


def test_continue_outside_loop_is_reported():
    analyzer = analyze("continue;")

    assert len(analyzer.errors) == 1
    assert "continue" in messages(analyzer)[0]


def test_break_inside_while_is_allowed():
    analyzer = analyze("""
        while (true) {
            break;
        }
    """)

    assert analyzer.errors == []


def test_continue_inside_do_while_is_allowed():
    analyzer = analyze("""
        do {
            continue;
        } while (true);
    """)

    assert analyzer.errors == []


def test_break_inside_foreach_is_allowed():
    analyzer = analyze("""
        let notas: integer[] = [1, 2, 3];
        foreach (nota in notas) {
            break;
        }
    """)

    assert analyzer.errors == []


def test_continue_outside_loop_inside_function_is_reported():
    analyzer = analyze("""
        function f(): integer {
            continue;
            return 1;
        }
    """)

    assert any("continue" in m for m in messages(analyzer))
