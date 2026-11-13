"""Tool registry: decorator-based registration, discovery, and execution.

The registry is independent of Flask and the HTTP transport. It owns the set of
registered tools, their JSON Schemas, and argument validation/execution.
"""

from . import errors
from .schema import generate_schema, validate_arguments


class Tool:
    """A single registered tool with name, function, description, and schema."""

    def __init__(self, name, func, description=None, input_schema=None):
        self.name = name
        self.func = func
        self.description = description or (func.__doc__ or "").strip()
        self.input_schema = input_schema or generate_schema(func)

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

    def execute(self, arguments):
        """Validate arguments and run the tool. Returns the raw result."""
        validate_arguments(self.input_schema, arguments)
        return self.func(**arguments)


class Registry:
    """Register, discover, and execute tools by name."""

    def __init__(self):
        self._tools = {}

    def tool(self, func=None, *, name=None, description=None, input_schema=None):
        """Decorator factory for registering a tool.

        Supports both:
            @registry.tool
            def foo(...): ...

            @registry.tool(name="custom")
            def foo(...): ...
        """

        def decorator(f):
            tool_name = name or f.__name__
            if tool_name in self._tools:
                raise ValueError(f"Duplicate tool registration: {tool_name}")
            self._tools[tool_name] = Tool(tool_name, f, description, input_schema)
            return f

        if func is not None:
            return decorator(func)
        return decorator

    def register(self, func, *, name=None, description=None, input_schema=None):
        """Programmatic registration (non-decorator entry point)."""
        tool_name = name or func.__name__
        if tool_name in self._tools:
            raise ValueError(f"Duplicate tool registration: {tool_name}")
        self._tools[tool_name] = Tool(tool_name, func, description, input_schema)
        return func

    def get(self, name):
        return self._tools.get(name)

    def has(self, name):
        return name in self._tools

    def list_tools(self):
        return [self._tools[name] for name in sorted(self._tools)]

    def execute(self, name, arguments):
        """Look up a tool, validate arguments, and execute it.

        Raises KeyError for unknown tools and JSONRPCError for invalid args.
        """
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Unknown tool: {name}")
        return tool.execute(arguments)
