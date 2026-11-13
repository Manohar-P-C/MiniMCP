"""Automatic JSON Schema generation from Python type hints.

Maps Python type annotations (builtins and typing generics) to JSON Schema
(https://json-schema.org) objects and validates tool arguments against them.

Supported annotations:
    str        -> {"type": "string"}
    int        -> {"type": "integer"}
    float      -> {"type": "number"}
    bool       -> {"type": "boolean"}
    list[T]    -> {"type": "array", "items": {...}}
    dict[str, T] -> {"type": "object", "additionalProperties": {...}}
    Optional[T] / T | None -> schema of T (parameter not required)
    Union[A, B] -> {"anyOf": [{...}, {...}]}
    default values are recorded under "default"; parameters without defaults are
    required unless their type is Optional.

Unsupported annotations fall back to a permissive schema ({}) so validation does
not reject valid input; this is documented as a limitation.
"""

import inspect
import json
import typing
from typing import get_args, get_origin

from . import errors
from .errors import JSONRPCError

try:  # Python 3.10+ union syntax (int | str)
    from types import UnionType
except ImportError:  # pragma: no cover - fallback for older interpreters
    UnionType = None


PRIMITIVE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}

# Types whose default value cannot be serialized to JSON.
_NON_JSON_DEFAULTS = (inspect.Parameter.empty,)


def _is_optional(annotation):
    """Return True if the annotation is Optional[T] (Union[T, None])."""
    origin = get_origin(annotation)
    if origin is not typing.Union and origin is not UnionType:
        return False
    args = get_args(annotation)
    return any(a is type(None) for a in args)


def _non_none_args(annotation):
    """Return Union args with NoneType removed."""
    return [a for a in get_args(annotation) if a is not type(None)]


def _items_or_additional(annotation, container):
    """Resolve the item/additionalProperties schema for generic containers."""
    args = get_args(annotation)
    if not args:
        return {}
    return python_type_to_json_schema(args[0])


def python_type_to_json_schema(annotation):
    """Convert a single Python annotation to a JSON Schema fragment."""
    origin = get_origin(annotation)

    # Optional[T] / T | None  -> schema of T (nullability is implicit in JSON Schema)
    if _is_optional(annotation):
        non_none = _non_none_args(annotation)
        if len(non_none) == 1:
            return python_type_to_json_schema(non_none[0])
        return {"anyOf": [python_type_to_json_schema(a) for a in non_none]}

    # Union[A, B] / A | B
    if origin is typing.Union or origin is UnionType:
        return {"anyOf": [python_type_to_json_schema(a) for a in get_args(annotation)]}

    # list[T] / List[T]
    if origin is list or origin is typing.List:
        return {"type": "array", "items": _items_or_additional(annotation, "list")}

    # dict[str, T] / Dict[str, T]
    if origin is dict or origin is typing.Dict:
        args = get_args(annotation)
        value_schema = python_type_to_json_schema(args[1]) if len(args) == 2 else {}
        return {"type": "object", "additionalProperties": value_schema}

    # Direct builtin types
    if annotation in PRIMITIVE_MAP:
        return {"type": PRIMITIVE_MAP[annotation]}

    # Unsupported annotation: permissive fallback.
    return {}


def generate_schema(func):
    """Build a JSON Schema object describing a callable's parameters.

    Returns a dict of the form:
        {"type": "object", "properties": {...}, "required": [...],
         "additionalProperties": False}
    """
    signature = inspect.signature(func)
    properties = {}
    required = []

    for name, param in signature.parameters.items():
        # Skip variadic positional / keyword arguments.
        if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue

        annotation = param.annotation
        if annotation is param.empty:
            annotation = str

        properties[name] = python_type_to_json_schema(annotation)

        if param.default is not param.empty:
            # JSON-serialize the default when possible.
            try:
                json.dumps(param.default)
                properties[name]["default"] = param.default
            except (TypeError, ValueError):
                properties[name]["default"] = str(param.default)
        else:
            # No default -> required unless the type is Optional.
            if not _is_optional(annotation):
                required.append(name)

    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def _check_type(value, type_schema):
    """Return True if value matches the JSON Schema type fragment."""
    if not isinstance(type_schema, dict):
        return True
    # anyOf: value must match at least one subschema.
    if "anyOf" in type_schema:
        return any(_check_type(value, sub) for sub in type_schema["anyOf"])

    expected = type_schema.get("type")
    if expected is None:
        return True

    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    # bool is a subclass of int; check bool first.
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "array":
        return isinstance(value, list)
    if expected == "object":
        return isinstance(value, dict)
    return True


def validate_arguments(schema, arguments):
    """Validate a dict of arguments against a generated JSON Schema.

    Raises JSONRPCError(INVALID_PARAMS) on any violation.
    Returns the validated arguments dict.
    """
    if not isinstance(arguments, dict):
        raise JSONRPCError(
            errors.INVALID_PARAMS,
            "arguments must be an object",
        )

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Reject parameters not declared in the schema.
    for key in arguments:
        if key not in properties:
            raise JSONRPCError(
                errors.INVALID_PARAMS,
                f"Unknown parameter: {key}",
            )

    # Required parameters must be present.
    for key in required:
        if key not in arguments:
            raise JSONRPCError(
                errors.INVALID_PARAMS,
                f"Missing required parameter: {key}",
            )

    # Type-check supplied parameters.
    for key, value in arguments.items():
        if key not in properties:
            continue
        if not _check_type(value, properties[key]):
            expected = properties[key].get("type", "any")
            raise JSONRPCError(
                errors.INVALID_PARAMS,
                f"Invalid type for parameter '{key}': expected {expected}",
            )

    return arguments
