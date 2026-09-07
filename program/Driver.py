import json
import sys

from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from antlr4.error.ErrorListener import ErrorListener

from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from analyzer import SemanticAnalyzer
from tree_export import tree_to_dict, tree_to_dot


class SyntaxErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"Error de sintaxis (linea {line}:{column}): {msg}")


def main(path: str, tree_output: str = None) -> int:
    input_stream = FileStream(path, encoding="utf-8")

    lexer = CompiscriptLexer(input_stream)
    error_listener = SyntaxErrorListener()
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)

    tokens = CommonTokenStream(lexer)

    parser = CompiscriptParser(tokens)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    tree = parser.program()

    if tree_output is not None:
        if tree_output.endswith(".dot"):
            content = tree_to_dot(tree, parser.ruleNames)
        else:
            content = json.dumps(tree_to_dict(tree, parser.ruleNames), ensure_ascii=False, indent=2)
        with open(tree_output, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Arbol sintactico escrito en '{tree_output}'")

    if error_listener.errors:
        for error in error_listener.errors:
            print(error)
        return 1

    analyzer = SemanticAnalyzer()
    ParseTreeWalker.DEFAULT.walk(analyzer, tree)

    if analyzer.errors:
        for error in analyzer.errors:
            print(error)
        return 1

    return 0


if __name__ == "__main__":
    if len(sys.argv) not in (2, 4) or (len(sys.argv) == 4 and sys.argv[2] != "--tree"):
        print("Uso: python3 Driver.py <archivo.cps> [--tree <salida.json|salida.dot>]")
        sys.exit(2)

    tree_arg = sys.argv[3] if len(sys.argv) == 4 else None
    sys.exit(main(sys.argv[1], tree_arg))
