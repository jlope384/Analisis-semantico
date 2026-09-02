"""Representacion de tipos del sistema de tipos de Compiscript."""


class Type:
    def __eq__(self, other):
        return isinstance(other, self.__class__)

    def __hash__(self):
        return hash(self.__class__)

    def __repr__(self):
        return self.name

    @property
    def name(self):
        return self.__class__.__name__


class IntegerType(Type):
    @property
    def name(self):
        return "integer"


class FloatType(Type):
    @property
    def name(self):
        return "float"


class StringType(Type):
    @property
    def name(self):
        return "string"


class BooleanType(Type):
    @property
    def name(self):
        return "boolean"


class NullType(Type):
    @property
    def name(self):
        return "null"


class VoidType(Type):
    """Tipo de retorno de funciones que no declaran tipo de retorno."""

    @property
    def name(self):
        return "void"


class ErrorType(Type):
    """Tipo comodin usado tras un error ya reportado, para evitar cascadas."""

    @property
    def name(self):
        return "<error>"


class ArrayType(Type):
    def __init__(self, element_type: Type):
        self.element_type = element_type

    def __eq__(self, other):
        return isinstance(other, ArrayType) and self.element_type == other.element_type

    def __hash__(self):
        return hash(("array", self.element_type))

    @property
    def name(self):
        return f"{self.element_type.name}[]"


class ClassType(Type):
    def __init__(self, class_name: str, class_symbol=None):
        self.class_name = class_name
        self.class_symbol = class_symbol

    def __eq__(self, other):
        return isinstance(other, ClassType) and self.class_name == other.class_name

    def __hash__(self):
        return hash(("class", self.class_name))

    @property
    def name(self):
        return self.class_name

    def is_subclass_of(self, other: "ClassType") -> bool:
        symbol = self.class_symbol
        while symbol is not None:
            if symbol.name == other.class_name:
                return True
            symbol = symbol.superclass
        return False


class FunctionType(Type):
    def __init__(self, param_types, return_type: Type):
        self.param_types = list(param_types)
        self.return_type = return_type

    def __eq__(self, other):
        return (
            isinstance(other, FunctionType)
            and self.param_types == other.param_types
            and self.return_type == other.return_type
        )

    def __hash__(self):
        return hash(("function", tuple(self.param_types), self.return_type))

    @property
    def name(self):
        params = ", ".join(t.name for t in self.param_types)
        return f"({params}) => {self.return_type.name}"


INTEGER = IntegerType()
FLOAT = FloatType()
STRING = StringType()
BOOLEAN = BooleanType()
NULL = NullType()
VOID = VoidType()
ERROR = ErrorType()


def is_numeric(t: Type) -> bool:
    return isinstance(t, (IntegerType, FloatType))


def is_error(t: Type) -> bool:
    return isinstance(t, ErrorType)
