"""Tool registry for openrat.tools."""

from collections.abc import Callable, Mapping
from typing import Any

from openrat.errors import UserInputError


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]] = {}

    def register(self, name: str, tool: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> None:
        """Register a callable tool under `name`."""
        self._tools[name] = tool

    def get(self, name: str) -> Callable[[Mapping[str, Any]], Mapping[str, Any]] | None:
        return self._tools.get(name)

    def list(self) -> list[str]:
        return list(self._tools.keys())

    def execute(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]:
        """Look up tool by name and call it with arguments dict."""
        tool = self._tools.get(name)
        if tool is None:
            # Unknown tool is UserInputError; if you treat model hallucinated tool names as internal integration faults, InternalError might be preferred.
            raise UserInputError(f"tool '{name}' not found in registry")
        return tool(arguments)
