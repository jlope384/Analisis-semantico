"""Representacion de errores semanticos, agnostica de ANTLR.

El visitor/listener que recorre el arbol es quien construye estas
instancias a partir de la posicion (linea, columna) de cada nodo.
"""


class SemanticError:
    def __init__(self, line: int, column: int, message: str):
        self.line = line
        self.column = column
        self.message = message

    def __repr__(self):
        return f"SemanticError({self.line}:{self.column}, {self.message!r})"

    def __str__(self):
        return f"Error semantico (linea {self.line}:{self.column}): {self.message}"
