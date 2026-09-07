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


def test_switch_case_with_incompatible_type_is_reported():
    analyzer = analyze("""
        let x: integer = 1;
        switch (x) {
            case 1:
                print(1);
            case "dos":
                print(2);
        }
    """)

    assert len(analyzer.errors) == 1
    assert "case" in messages(analyzer)[0]


def test_switch_case_with_compatible_type_is_allowed():
    analyzer = analyze("""
        let x: integer = 1;
        switch (x) {
            case 1:
                print(1);
            case 2:
                print(2);
            default:
                print(0);
        }
    """)

    assert analyzer.errors == []


def test_break_inside_switch_case_is_allowed():
    analyzer = analyze("""
        let x: integer = 1;
        switch (x) {
            case 1:
                break;
            default:
                print(0);
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


def test_code_after_return_is_unreachable():
    analyzer = analyze("""
        function f(): integer {
            return 1;
            print(2);
        }
    """)

    assert len(analyzer.errors) == 1
    assert "inalcanzable" in messages(analyzer)[0]


def test_code_after_break_is_unreachable():
    analyzer = analyze("""
        while (true) {
            break;
            print(1);
        }
    """)

    assert len(analyzer.errors) == 1
    assert "inalcanzable" in messages(analyzer)[0]


def test_code_after_continue_in_switch_case_is_unreachable():
    analyzer = analyze("""
        let x: integer = 1;
        switch (x) {
            case 1:
                break;
                print(1);
        }
    """)

    assert len(analyzer.errors) == 1
    assert "inalcanzable" in messages(analyzer)[0]


def test_return_as_last_statement_is_not_flagged():
    analyzer = analyze("""
        function f(): integer {
            if (true) {
                return 1;
            }
            return 2;
        }
    """)

    assert analyzer.errors == []
