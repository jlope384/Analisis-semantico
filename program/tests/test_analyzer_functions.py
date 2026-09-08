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


# --- funciones anidadas y closures -----------------------------------


def test_nested_function_captures_variable_from_enclosing_scope():
    analyzer = analyze("""
        function externa(a: integer): integer {
            let base: integer = a * 2;
            function interna(b: integer): integer {
                return base + b;
            }
            return interna(3);
        }
    """)

    assert analyzer.errors == []


def test_nested_function_captures_parameter_of_enclosing_function():
    analyzer = analyze("""
        function externa(a: integer): integer {
            function interna(): integer {
                return a;
            }
            return interna();
        }
    """)

    assert analyzer.errors == []


def test_nested_function_is_not_visible_outside_its_enclosing_function():
    analyzer = analyze("""
        function externa(): integer {
            function interna(): integer { return 1; }
            return interna();
        }
        let x: integer = interna();
    """)

    assert len(analyzer.errors) == 1
    assert "interna" in messages(analyzer)[0]
    assert "no declarada" in messages(analyzer)[0]


def test_nested_function_argument_type_is_validated():
    analyzer = analyze("""
        function externa(): integer {
            function interna(b: integer): integer { return b; }
            return interna("no soy entero");
        }
    """)

    assert len(analyzer.errors) == 1
    assert "argumento" in messages(analyzer)[0]
