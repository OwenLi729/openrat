
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class Message:
    role: str
    content: str


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ModelResponse:
    content: Optional[str]
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


@dataclass
class ModelConfig:
    provider: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    model_name: Optional[str] = None