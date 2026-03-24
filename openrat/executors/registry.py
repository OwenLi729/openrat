from collections.abc import Mapping
from .base_executor import BaseExecutor


class ExecutorRegistry:
    """Registry for pre-registered executors. No dynamic creation allowed."""

    def __init__(self) -> None:
        self._backends: dict[str, BaseExecutor] = {}

    def register(self, name: str, backend: BaseExecutor) -> None:
        if name in self._backends:
            raise KeyError(f"executor '{name}' already registered")
        self._backends[name] = backend

    def get(self, name: str) -> BaseExecutor:
        try:
            return self._backends[name]
        except KeyError:
            raise KeyError(f"executor '{name}' not found")

    def list(self) -> list[str]:
        return list(self._backends.keys())

    def clear(self) -> None:
        self._backends.clear()
