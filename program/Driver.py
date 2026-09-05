import sys

from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from antlr4.error.ErrorListener import ErrorListener

from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from analyzer import SemanticAnalyzer


class SyntaxErrorListener(ErrorListener):
    def __init__(self):
        super().__init__()
        self.errors = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        self.errors.append(f"Error de sintaxis (linea {line}:{column}): {msg}")


def main(path: str) -> int:
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
    if len(sys.argv) != 2:
        print("Uso: python3 Driver.py <archivo.cps>")
        sys.exit(2)

    sys.exit(main(sys.argv[1]))
