from abc import ABC, abstractmethod

from typing import List, Optional

from ..types import Message, ModelResponse, ToolCall


class BaseModelAdapter(ABC):
    """Abstract adapter that normalizes different model providers."""

    provider: str

    @abstractmethod
    def generate(
        self,
        messages: List[Message],
        tools: Optional[list] = None,
        config: Optional[dict] = None,
    ) -> ModelResponse:
        raise NotImplementedError()
