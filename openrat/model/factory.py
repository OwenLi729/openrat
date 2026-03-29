from collections.abc import Mapping
from typing import Any

from .adapters.oai_adapter import OpenAICompatibleAdapter
from .adapters.claude_adapter import ClaudeAdapter
from .adapters.gemini_adapter import GeminiAdapter
from openrat.core.errors import UserInputError
from openrat.core.protocols import ModelAdapterProtocol


class ModelFactory:
    @staticmethod
    def create(cfg: Mapping[str, Any]) -> ModelAdapterProtocol:
        provider = cfg.get("provider")
        if provider == "openai_compatible":
            return OpenAICompatibleAdapter(base_url=cfg.get("base_url"), api_key=cfg.get("api_key"), model_name=cfg.get("model_name"))
        if provider == "claude":
            return ClaudeAdapter(api_key=cfg.get("api_key"), model_name=cfg.get("model_name"))
        if provider == "gemini":
            return GeminiAdapter(api_key=cfg.get("api_key"), model_name=cfg.get("model_name"))

        raise UserInputError(
            f"unknown provider: {provider}",
            hint="Supported providers: openai_compatible, claude, gemini",
        )
