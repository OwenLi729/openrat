"""Canonical structural protocols (interfaces) for the Openrat framework.

The package-root ``openrat.protocols`` module re-exports everything from
here for backward compatibility.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Protocol, Sequence

if TYPE_CHECKING:
    from openrat.model.types import Message, ModelResponse


JSONLike = Mapping[str, Any]


class SessionProtocol(Protocol):
    def authorize(
        self,
        capability: str,
        dry_run: bool = False,
        *,
        action: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> bool: ...


class ToolProtocol(Protocol):
    capability: str

    def run(self, payload: Any, session: SessionProtocol) -> Mapping[str, Any]: ...


class ExecutorProtocol(Protocol):
    def execute(self, payload: Mapping[str, Any]) -> Mapping[str, Any]: ...


class RegisteredToolCallable(Protocol):
    def __call__(self, arguments: Mapping[str, Any]) -> Mapping[str, Any]: ...


class ToolRegistryProtocol(Protocol):
    def register(
        self,
        name: str,
        tool: RegisteredToolCallable,
        capability: str | None = None,
        *,
        trusted: bool = False,
    ) -> None: ...
    def get(self, name: str) -> RegisteredToolCallable | None: ...
    def list(self) -> list[str]: ...
    def execute(self, name: str, arguments: Mapping[str, Any]) -> Mapping[str, Any]: ...


class ModelAdapterProtocol(Protocol):
    provider: str

    def generate(
        self,
        messages: Sequence["Message"],
        tools: Sequence[Mapping[str, Any]] | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> "ModelResponse": ...


__all__ = [
    "JSONLike",
    "SessionProtocol",
    "ToolProtocol",
    "ExecutorProtocol",
    "RegisteredToolCallable",
    "ToolRegistryProtocol",
    "ModelAdapterProtocol",
]
