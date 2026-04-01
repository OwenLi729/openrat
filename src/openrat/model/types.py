from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Any


@dataclass
class Message:
    role: str
    content: str


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Mapping[str, Any]


@dataclass
class ModelResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    stop_reason: str | None = None
    raw: Mapping[str, Any] | None = None


@dataclass
class ModelConfig:
    provider: str
    api_key: str | None = None
    base_url: str | None = None
    model_name: str | None = None
