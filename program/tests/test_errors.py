from semantic import SemanticError


def test_semantic_error_stores_position_and_message():
    error = SemanticError(3, 7, "variable 'x' no declarada")

    assert error.line == 3
    assert error.column == 7
    assert "no declarada" in error.message


def test_semantic_error_str_includes_position():
    error = SemanticError(10, 2, "algo salio mal")

    text = str(error)

    assert "10:2" in text
    assert "algo salio mal" in text
