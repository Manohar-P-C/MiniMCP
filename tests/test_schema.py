"""Tests for automatic JSON Schema generation from type hints."""

import pytest

from minimcp.schema import generate_schema, python_type_to_json_schema, validate_arguments
from minimcp.errors import JSONRPCError


def test_primitive_types():
    def fn(a: str, b: int, c: float, d: bool) -> None:
        pass

    schema = generate_schema(fn)
    props = schema["properties"]
    assert props["a"]["type"] == "string"
    assert props["b"]["type"] == "integer"
    assert props["c"]["type"] == "number"
    assert props["d"]["type"] == "boolean"
    assert schema["required"] == ["a", "b", "c", "d"]


def test_list_and_dict():
    def fn(items: list, mapping: dict, names: list[str], config: dict[str, int]) -> None:
        pass

    schema = generate_schema(fn)
    assert schema["properties"]["items"]["type"] == "array"
    assert schema["properties"]["mapping"]["type"] == "object"
    assert schema["properties"]["names"]["type"] == "array"
    assert schema["properties"]["names"]["items"] == {"type": "string"}
    assert schema["properties"]["config"]["type"] == "object"


def test_optional_parameters():
    def fn(required: int, optional: str = "default", flag: bool = True) -> None:
        pass

    schema = generate_schema(fn)
    assert "optional" not in schema["required"]
    assert "flag" not in schema["required"]
    assert schema["required"] == ["required"]
    assert schema["properties"]["optional"]["default"] == "default"
    assert schema["properties"]["flag"]["default"] is True


def test_required_parameter_detection():
    def fn(a: int, b: str = "x") -> None:
        pass

    schema = generate_schema(fn)
    assert schema["required"] == ["a"]


def test_optional_type_not_required():
    from typing import Optional

    def fn(required: int, maybe: Optional[str] = None) -> None:
        pass

    schema = generate_schema(fn)
    assert schema["required"] == ["required"]
    assert "maybe" not in schema["required"]


def test_default_values_recorded():
    def fn(count: int = 5, label: str = "item") -> None:
        pass

    schema = generate_schema(fn)
    assert schema["properties"]["count"]["default"] == 5
    assert schema["properties"]["label"]["default"] == "item"
    assert schema["required"] == []


def test_invalid_annotation_safe_fallback():
    # An annotation that cannot be mapped should not crash generation.
    def fn(data: object) -> None:
        pass

    schema = generate_schema(fn)
    assert schema["properties"]["data"] == {}


def test_validate_arguments_valid():
    schema = {
        "type": "object",
        "properties": {
            "a": {"type": "integer"},
            "b": {"type": "string"},
        },
        "required": ["a"],
        "additionalProperties": False,
    }
    result = validate_arguments(schema, {"a": 1, "b": "x"})
    assert result == {"a": 1, "b": "x"}


def test_validate_arguments_missing_required():
    schema = {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "required": ["a"],
        "additionalProperties": False,
    }
    with pytest.raises(JSONRPCError) as exc:
        validate_arguments(schema, {})
    assert exc.value.code == -32602


def test_validate_arguments_unknown_parameter():
    schema = {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "required": [],
        "additionalProperties": False,
    }
    with pytest.raises(JSONRPCError) as exc:
        validate_arguments(schema, {"a": 1, "b": 2})
    assert exc.value.code == -32602


def test_validate_arguments_wrong_type():
    schema = {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "required": ["a"],
        "additionalProperties": False,
    }
    with pytest.raises(JSONRPCError) as exc:
        validate_arguments(schema, {"a": "not an int"})
    assert exc.value.code == -32602


def test_validate_arguments_bool_not_integer():
    schema = {
        "type": "object",
        "properties": {"a": {"type": "integer"}},
        "required": ["a"],
        "additionalProperties": False,
    }
    # bool is a subclass of int in Python but must not pass as integer.
    with pytest.raises(JSONRPCError) as exc:
        validate_arguments(schema, {"a": True})
    assert exc.value.code == -32602
