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


def test_arithmetic_between_incompatible_types_is_reported():
    analyzer = analyze('let x: integer = 1 + "hola";')

    assert len(analyzer.errors) == 1
    assert "+" in messages(analyzer)[0]


def test_string_concatenation_is_allowed():
    analyzer = analyze('let saludo: string = "hola " + "mundo";')

    assert analyzer.errors == []


def test_variable_declaration_type_mismatch_is_reported():
    analyzer = analyze('let x: integer = "no soy un entero";')

    assert len(analyzer.errors) == 1
    assert "x" in messages(analyzer)[0]


def test_variable_declaration_type_inferred_from_initializer():
    analyzer = analyze("""
        let x = 5;
        let y: integer = x + 1;
    """)

    assert analyzer.errors == []


def test_assignment_type_mismatch_is_reported():
    analyzer = analyze("""
        let x: integer = 1;
        x = "texto";
    """)

    assert len(analyzer.errors) == 1
    assert "x" in messages(analyzer)[0]


def test_reassigning_constant_is_reported():
    analyzer = analyze("""
        const PI: integer = 3;
        PI = 4;
    """)

    assert len(analyzer.errors) == 1
    assert "constante" in messages(analyzer)[0]


def test_if_condition_must_be_boolean():
    analyzer = analyze("""
        if (1 + 1) {
            print(1);
        }
    """)

    assert len(analyzer.errors) == 1
    assert "if" in messages(analyzer)[0]


def test_if_condition_boolean_is_allowed():
    analyzer = analyze("""
        let x: integer = 5;
        if (x > 3) {
            print(x);
        }
    """)

    assert analyzer.errors == []


def test_while_condition_must_be_boolean():
    analyzer = analyze("""
        while ("texto") {
            print(1);
        }
    """)

    assert len(analyzer.errors) == 1
    assert "while" in messages(analyzer)[0]


def test_for_condition_must_be_boolean():
    analyzer = analyze("""
        for (let i: integer = 0; i; i = i + 1) {
            print(i);
        }
    """)

    assert len(analyzer.errors) == 1
    assert "for" in messages(analyzer)[0]


def test_for_condition_boolean_is_allowed():
    analyzer = analyze("""
        for (let i: integer = 0; i < 3; i = i + 1) {
            print(i);
        }
    """)

    assert analyzer.errors == []


def test_for_without_condition_is_allowed():
    analyzer = analyze("""
        for (let i: integer = 0; ; i = i + 1) {
            print(i);
            break;
        }
    """)

    assert analyzer.errors == []


def test_logical_operator_requires_boolean_operands():
    analyzer = analyze("let x: boolean = 1 && true;")

    assert len(analyzer.errors) == 1
    assert "&&" in messages(analyzer)[0]


def test_relational_operator_requires_numeric_operands():
    analyzer = analyze('let x: boolean = "a" < "b";')

    assert len(analyzer.errors) == 1


def test_unary_minus_requires_numeric_operand():
    analyzer = analyze('let x: integer = -"hola";')

    assert len(analyzer.errors) == 1
    assert "-" in messages(analyzer)[0]


def test_unary_not_requires_boolean_operand():
    analyzer = analyze("let x: boolean = !5;")

    assert len(analyzer.errors) == 1
    assert "!" in messages(analyzer)[0]


def test_ternary_with_incompatible_branches_is_reported():
    analyzer = analyze('let x = true ? 1 : "dos";')

    assert len(analyzer.errors) == 1
    assert "ternario" in messages(analyzer)[0]


def test_ternary_with_compatible_branches_is_allowed():
    analyzer = analyze("let x: integer = true ? 1 : 2;")

    assert analyzer.errors == []


def test_array_literal_with_mixed_types_is_reported():
    analyzer = analyze('let x = [1, "dos", 3];')

    assert len(analyzer.errors) == 1
    assert "arreglo" in messages(analyzer)[0]


def test_indexing_with_non_integer_is_reported():
    analyzer = analyze("""
        let nums: integer[] = [1, 2, 3];
        let x: integer = nums[true];
    """)

    assert len(analyzer.errors) == 1
    assert "indice" in messages(analyzer)[0]


def test_indexing_array_returns_element_type():
    analyzer = analyze("""
        let nums: integer[] = [1, 2, 3];
        let x: integer = nums[0];
    """)

    assert analyzer.errors == []


def test_function_call_with_wrong_argument_count_is_reported():
    analyzer = analyze("""
        function suma(a: integer, b: integer): integer {
            return a + b;
        }
        let x: integer = suma(1);
    """)

    assert len(analyzer.errors) == 1
    assert "argumento" in messages(analyzer)[0]


def test_function_call_with_wrong_argument_type_is_reported():
    analyzer = analyze("""
        function suma(a: integer, b: integer): integer {
            return a + b;
        }
        let x: integer = suma(1, "dos");
    """)

    assert len(analyzer.errors) == 1
    assert "argumento" in messages(analyzer)[0]


def test_function_call_with_correct_arguments_is_allowed():
    analyzer = analyze("""
        function suma(a: integer, b: integer): integer {
            return a + b;
        }
        let x: integer = suma(1, 2);
    """)

    assert analyzer.errors == []


def test_return_type_mismatch_is_reported():
    analyzer = analyze("""
        function nombre(): string {
            return 5;
        }
    """)

    assert len(analyzer.errors) == 1
    assert "nombre" in messages(analyzer)[0]


def test_class_field_assignment_type_mismatch_is_reported():
    analyzer = analyze("""
        class Persona {
            let edad: integer;
        }
        let p: Persona = new Persona();
        p.edad = "no es un entero";
    """)

    assert len(analyzer.errors) == 1
    assert "edad" in messages(analyzer)[0]


def test_class_field_assignment_with_correct_type_is_allowed():
    analyzer = analyze("""
        class Persona {
            let edad: integer;
        }
        let p: Persona = new Persona();
        p.edad = 30;
    """)

    assert analyzer.errors == []


def test_subclass_instance_is_assignable_to_superclass_variable():
    analyzer = analyze("""
        class Animal {
            let nombre: string;
        }
        class Perro : Animal {
        }
        let a: Animal = new Perro();
    """)

    assert analyzer.errors == []


def test_constructor_can_assign_field_via_this():
    analyzer = analyze("""
        class Animal {
            let nombre: string;

            function constructor(nombre: string) {
                this.nombre = nombre;
            }
        }
    """)

    assert analyzer.errors == []


def test_method_can_use_field_declared_after_it_in_source():
    analyzer = analyze("""
        class Animal {
            function nombreEnMayusculas(): string {
                return this.nombre;
            }

            let nombre: string;
        }
    """)

    assert analyzer.errors == []


def test_method_can_call_sibling_method_declared_later_in_source():
    analyzer = analyze("""
        class Animal {
            function saludar(): string {
                return this.ruido();
            }

            function ruido(): string {
                return "...";
            }
        }
    """)

    assert analyzer.errors == []


def test_inherited_field_is_accessible_through_subclass_instance():
    analyzer = analyze("""
        class Animal {
            let nombre: string;
        }
        class Perro : Animal {
        }
        let p: Perro = new Perro();
        p.nombre = "Firulais";
    """)

    assert analyzer.errors == []
