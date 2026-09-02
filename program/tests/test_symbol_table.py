import pytest

from semantic import (
    SymbolTable,
    ScopeKind,
    VariableSymbol,
    ParameterSymbol,
    FunctionSymbol,
    ClassSymbol,
    DuplicateSymbolError,
    INTEGER,
    STRING,
    BOOLEAN,
    VOID,
)


def test_define_and_resolve_in_same_scope():
    table = SymbolTable()
    table.define(VariableSymbol("x", INTEGER))

    resolved = table.resolve("x")

    assert resolved is not None
    assert resolved.name == "x"
    assert resolved.type == INTEGER


def test_resolve_undefined_returns_none():
    table = SymbolTable()

    assert table.resolve("no_existe") is None


def test_duplicate_definition_in_same_scope_raises():
    table = SymbolTable()
    table.define(VariableSymbol("x", INTEGER))

    with pytest.raises(DuplicateSymbolError):
        table.define(VariableSymbol("x", STRING))


def test_resolve_from_nested_block_scope_sees_outer_variable():
    table = SymbolTable()
    table.define(VariableSymbol("global_var", INTEGER))

    table.enter_scope(ScopeKind.BLOCK)
    resolved = table.resolve("global_var")

    assert resolved is not None
    assert resolved.name == "global_var"


def test_shadowing_in_nested_scope_does_not_raise_and_hides_outer():
    table = SymbolTable()
    table.define(VariableSymbol("x", INTEGER))

    table.enter_scope(ScopeKind.BLOCK)
    table.define(VariableSymbol("x", STRING))  # no debe lanzar: es otro ambito

    inner = table.resolve("x")
    assert inner.type == STRING

    table.exit_scope()
    outer = table.resolve("x")
    assert outer.type == INTEGER


def test_variables_go_out_of_scope_after_exiting_block():
    table = SymbolTable()

    table.enter_scope(ScopeKind.BLOCK)
    table.define(VariableSymbol("local", BOOLEAN))
    assert table.resolve("local") is not None

    table.exit_scope()
    assert table.resolve("local") is None


def test_resolve_local_only_checks_current_scope():
    table = SymbolTable()
    table.define(VariableSymbol("x", INTEGER))

    table.enter_scope(ScopeKind.BLOCK)

    assert table.resolve("x") is not None  # visible por herencia de ambito
    assert table.resolve_local("x") is None  # pero no esta definida localmente


def test_exit_global_scope_raises():
    table = SymbolTable()

    with pytest.raises(RuntimeError):
        table.exit_scope()


def test_nearest_enclosing_function_scope():
    table = SymbolTable()
    function_scope = table.enter_scope(ScopeKind.FUNCTION)
    table.enter_scope(ScopeKind.BLOCK)
    table.enter_scope(ScopeKind.BLOCK)

    found = table.current_scope.nearest_enclosing(ScopeKind.FUNCTION)

    assert found is function_scope


def test_is_inside_returns_false_when_no_enclosing_loop_or_function():
    table = SymbolTable()
    table.enter_scope(ScopeKind.BLOCK)

    assert table.current_scope.is_inside(ScopeKind.FUNCTION) is False


def test_function_symbol_stores_param_types_and_return_type():
    param_a = ParameterSymbol("a", INTEGER)
    param_b = ParameterSymbol("b", INTEGER)
    func = FunctionSymbol("suma", [INTEGER, INTEGER], INTEGER, params=[param_a, param_b])

    assert func.param_types == [INTEGER, INTEGER]
    assert func.return_type == INTEGER
    assert func.params == [param_a, param_b]


def test_class_symbol_resolves_own_field_and_method():
    animal = ClassSymbol("Animal")
    animal.define_field(VariableSymbol("nombre", STRING))
    animal.define_method(FunctionSymbol("hablar", [], STRING))

    assert animal.resolve_member("nombre").name == "nombre"
    assert animal.resolve_member("hablar").name == "hablar"
    assert animal.resolve_member("no_existe") is None


def test_class_symbol_resolves_inherited_member_through_superclass():
    animal = ClassSymbol("Animal")
    animal.define_field(VariableSymbol("nombre", STRING))

    perro = ClassSymbol("Perro", superclass=animal)
    perro.define_method(FunctionSymbol("ladrar", [], VOID))

    assert perro.resolve_member("nombre") is not None  # heredado
    assert perro.resolve_member("ladrar") is not None  # propio


def test_class_symbol_duplicate_field_and_method_names_raise():
    clase = ClassSymbol("Foo")
    clase.define_field(VariableSymbol("x", INTEGER))

    with pytest.raises(DuplicateSymbolError):
        clase.define_method(FunctionSymbol("x", [], VOID))
