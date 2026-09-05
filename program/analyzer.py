"""Puente entre el arbol de ANTLR y la tabla de simbolos.

`semantic/` es agnostico de ANTLR; este modulo si conoce el arbol y usa un
Listener para recorrerlo, resolviendo ambitos y declaraciones sobre una
SymbolTable.
"""

from CompiscriptListener import CompiscriptListener
from CompiscriptParser import CompiscriptParser

from semantic import (
    SymbolTable,
    ScopeKind,
    VariableSymbol,
    ParameterSymbol,
    FunctionSymbol,
    ClassSymbol,
    DuplicateSymbolError,
    SemanticError,
    INTEGER,
    STRING,
    BOOLEAN,
    VOID,
    ArrayType,
)


class SemanticAnalyzer(CompiscriptListener):
    def __init__(self):
        self.table = SymbolTable()
        self.errors: list[SemanticError] = []
        self.function_stack: list[FunctionSymbol] = []
        self.class_stack: list[ClassSymbol] = []

    # ------------------------------------------------------------------
    # utilidades
    # ------------------------------------------------------------------

    def _error(self, ctx, message: str):
        token = ctx.start
        self.errors.append(SemanticError(token.line, token.column, message))

    def _define(self, symbol, ctx, kind_desc: str):
        try:
            self.table.define(symbol)
        except DuplicateSymbolError:
            self._error(ctx, f"'{symbol.name}' ya fue declarado en este ambito ({kind_desc})")

    def _resolve_type(self, type_ctx: "CompiscriptParser.TypeContext"):
        if type_ctx is None:
            return None

        base_ctx = type_ctx.baseType()
        base_text = base_ctx.getText()
        if base_text == "integer":
            base = INTEGER
        elif base_text == "string":
            base = STRING
        elif base_text == "boolean":
            base = BOOLEAN
        else:
            symbol = self.table.resolve(base_text)
            if not isinstance(symbol, ClassSymbol):
                self._error(base_ctx, f"tipo desconocido '{base_text}'")
                return None
            base = symbol.type

        dims = (type_ctx.getChildCount() - 1) // 2
        result = base
        for _ in range(dims):
            result = ArrayType(result)
        return result

    # ------------------------------------------------------------------
    # bloques: cada uno abre su propio ambito
    # ------------------------------------------------------------------

    def enterBlock(self, ctx: CompiscriptParser.BlockContext):
        self.table.enter_scope(ScopeKind.BLOCK)

        parent = ctx.parentCtx
        if isinstance(parent, CompiscriptParser.TryCatchStatementContext) and parent.block(1) is ctx:
            name = parent.Identifier().getText()
            self._define(VariableSymbol(name, None, initialized=True), parent, "variable de catch")

    def exitBlock(self, ctx: CompiscriptParser.BlockContext):
        self.table.exit_scope()

    # ------------------------------------------------------------------
    # declaraciones de variables y constantes
    # ------------------------------------------------------------------

    def enterVariableDeclaration(self, ctx: CompiscriptParser.VariableDeclarationContext):
        name = ctx.Identifier().getText()
        declared_type = self._resolve_type(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else None
        symbol = VariableSymbol(name, declared_type, is_const=False, initialized=ctx.initializer() is not None)
        self._define(symbol, ctx, "variable")

    def enterConstantDeclaration(self, ctx: CompiscriptParser.ConstantDeclarationContext):
        name = ctx.Identifier().getText()
        declared_type = self._resolve_type(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else None
        symbol = VariableSymbol(name, declared_type, is_const=True, initialized=True)
        self._define(symbol, ctx, "constante")

    # ------------------------------------------------------------------
    # asignacion a un identificador simple (no propiedad)
    # ------------------------------------------------------------------

    def enterAssignment(self, ctx: CompiscriptParser.AssignmentContext):
        identifier = ctx.Identifier()
        if identifier is None:
            return  # asignacion a propiedad: se valida junto con clases
        text = identifier.getText()
        if self.table.resolve(text) is None:
            self._error(ctx, f"variable '{text}' no declarada")

    # ------------------------------------------------------------------
    # uso de identificadores dentro de expresiones
    # ------------------------------------------------------------------

    def exitIdentifierExpr(self, ctx: CompiscriptParser.IdentifierExprContext):
        text = ctx.Identifier().getText()
        if self.table.resolve(text) is None:
            self._error(ctx, f"variable '{text}' no declarada")

    def exitNewExpr(self, ctx: CompiscriptParser.NewExprContext):
        text = ctx.Identifier().getText()
        symbol = self.table.resolve(text)
        if not isinstance(symbol, ClassSymbol):
            self._error(ctx, f"clase '{text}' no declarada")

    # ------------------------------------------------------------------
    # funciones
    # ------------------------------------------------------------------

    def enterFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        name = ctx.Identifier().getText()
        return_type = self._resolve_type(ctx.type_()) if ctx.type_() else VOID

        params = []
        param_types = []
        if ctx.parameters():
            for param_ctx in ctx.parameters().parameter():
                p_name = param_ctx.Identifier().getText()
                p_type = self._resolve_type(param_ctx.type_()) if param_ctx.type_() else None
                params.append(ParameterSymbol(p_name, p_type))
                param_types.append(p_type)

        symbol = FunctionSymbol(name, param_types, return_type, params=params)
        if self.class_stack:
            symbol.owner_class = self.class_stack[-1]
        self._define(symbol, ctx, "funcion")

        scope = self.table.enter_scope(ScopeKind.FUNCTION, owner=symbol)
        symbol.scope = scope
        self.function_stack.append(symbol)

        for param in params:
            self._define(param, ctx, "parametro")

    def exitFunctionDeclaration(self, ctx: CompiscriptParser.FunctionDeclarationContext):
        self.table.exit_scope()
        self.function_stack.pop()

    # ------------------------------------------------------------------
    # clases
    # ------------------------------------------------------------------

    def enterClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext):
        identifiers = ctx.Identifier()
        name = identifiers[0].getText()

        superclass = None
        if len(identifiers) > 1:
            super_name = identifiers[1].getText()
            super_symbol = self.table.resolve(super_name)
            if not isinstance(super_symbol, ClassSymbol):
                self._error(ctx, f"clase base '{super_name}' no declarada")
            else:
                superclass = super_symbol

        symbol = ClassSymbol(name, superclass=superclass)
        self._define(symbol, ctx, "clase")

        scope = self.table.enter_scope(ScopeKind.CLASS, owner=symbol)
        symbol.scope = scope
        self.class_stack.append(symbol)

    def exitClassDeclaration(self, ctx: CompiscriptParser.ClassDeclarationContext):
        symbol = self.class_stack.pop()
        for member_name, member_symbol in self.table.current_scope.symbols.items():
            if isinstance(member_symbol, FunctionSymbol):
                member_symbol.owner_class = symbol
                symbol.methods[member_name] = member_symbol
            elif isinstance(member_symbol, VariableSymbol):
                symbol.fields[member_name] = member_symbol
        self.table.exit_scope()

    # ------------------------------------------------------------------
    # for / foreach: la variable de control vive en su propio ambito
    # ------------------------------------------------------------------

    def enterForStatement(self, ctx: CompiscriptParser.ForStatementContext):
        self.table.enter_scope(ScopeKind.BLOCK)

    def exitForStatement(self, ctx: CompiscriptParser.ForStatementContext):
        self.table.exit_scope()

    def enterForeachStatement(self, ctx: CompiscriptParser.ForeachStatementContext):
        self.table.enter_scope(ScopeKind.BLOCK)
        name = ctx.Identifier().getText()
        self._define(VariableSymbol(name, None, initialized=True), ctx, "variable de foreach")

    def exitForeachStatement(self, ctx: CompiscriptParser.ForeachStatementContext):
        self.table.exit_scope()
