"""Tool registry for openrat.tools."""

from collections.abc import Callable, Mapping
from typing import Any

from openrat.core.errors import UserInputError
from openrat.core.protocols import SessionProtocol


class ToolRegistry:
    """Registry for named tools callable by LLM agents.
    
    Tools are callables that accept a dict of arguments and return a dict result.
    """
    def __init__(self, session: SessionProtocol | None = None) -> None:
        self._tools: dict[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]] = {}
        self._capabilities: dict[str, str] = {}
        self._session = session

    def register(
        self,
        name: str,
        tool: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        capability: str | None = None,
    ) -> None:
        """Register a callable tool under `name`."""
        effective_capability = capability or getattr(tool, "capability", None)
        if not effective_capability:
            raise UserInputError(f"tool '{name}' must declare a required capability")

        self._tools[name] = tool
        self._capabilities[name] = str(effective_capability)

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

        capability = self._capabilities.get(name)
        if capability is None:
            raise UserInputError(f"tool '{name}' is missing capability metadata")

        if self._session is not None:
            self._session.authorize(
                capability,
                action=f"tool.execute:{name}",
                metadata={"tool": name},
            )

        return tool(arguments)
