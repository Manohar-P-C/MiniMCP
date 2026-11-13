"""Tests for the tool registry."""

import pytest

from minimcp.errors import JSONRPCError
from minimcp.registry import Registry, Tool
from minimcp.schema import generate_schema


@pytest.fixture
def registry():
    return Registry()


def test_successful_registration(registry):
    @registry.tool
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    assert registry.has("add")
    tool = registry.get("add")
    assert isinstance(tool, Tool)
    assert tool.name == "add"
    assert tool.description == "Add two numbers."
    assert tool.input_schema["type"] == "object"


def test_duplicate_registration(registry):
    @registry.tool
    def add(a: int, b: int) -> int:
        return a + b

    def add_again(a: int, b: int) -> int:
        return a + b

    with pytest.raises(ValueError, match="Duplicate tool registration"):
        registry.register(add_again, name="add")


def test_programmatic_registration(registry):
    def mul(a: int, b: int) -> int:
        return a * b

    registry.register(mul, name="multiply")
    assert registry.has("multiply")
    assert registry.execute("multiply", {"a": 3, "b": 4}) == 12


def test_tool_discovery(registry):
    @registry.tool
    def alpha(x: str) -> str:
        return x

    @registry.tool
    def beta(y: int) -> int:
        return y

    names = [t.name for t in registry.list_tools()]
    assert "alpha" in names
    assert "beta" in names
    assert names == sorted(names)


def test_tool_execution(registry):
    @registry.tool
    def greet(name: str, greeting: str = "Hello") -> str:
        return f"{greeting}, {name}!"

    result = registry.execute("greet", {"name": "Ada"})
    assert result == "Hello, Ada!"

    result = registry.execute("greet", {"name": "Ada", "greeting": "Hi"})
    assert result == "Hi, Ada!"


def test_unknown_tool(registry):
    with pytest.raises(KeyError, match="Unknown tool"):
        registry.execute("does_not_exist", {})


def test_argument_validation_missing_required(registry):
    @registry.tool
    def add(a: int, b: int) -> int:
        return a + b

    with pytest.raises(JSONRPCError) as exc:
        registry.execute("add", {"a": 1})
    assert exc.value.code == -32602


def test_argument_validation_unknown_parameter(registry):
    @registry.tool
    def add(a: int, b: int) -> int:
        return a + b

    with pytest.raises(JSONRPCError) as exc:
        registry.execute("add", {"a": 1, "b": 2, "zzz": 9})
    assert exc.value.code == -32602


def test_argument_validation_wrong_type(registry):
    @registry.tool
    def add(a: int, b: int) -> int:
        return a + b

    with pytest.raises(JSONRPCError) as exc:
        registry.execute("add", {"a": "x", "b": 2})
    assert exc.value.code == -32602
