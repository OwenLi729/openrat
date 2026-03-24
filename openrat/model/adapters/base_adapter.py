from abc import ABC, abstractmethod

from collections.abc import Mapping, Sequence
from typing import Any

from ..types import Message, ModelResponse, ToolCall


class BaseModelAdapter(ABC):
    """Abstract adapter that normalizes different model providers."""

    provider: str

    @abstractmethod
    def generate(
        self,
        messages: Sequence[Message],
        tools: Sequence[Mapping[str, Any]] | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> ModelResponse:
        raise NotImplementedError()
