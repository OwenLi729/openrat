from typing import Dict, Any

from .adapters.oai_adapter import OpenAICompatibleAdapter
from .adapters.claude_adapter import ClaudeAdapter
from .adapters.gemini_adapter import GeminiAdapter


class ModelFactory:
    @staticmethod
    def create(cfg: Dict[str, Any]):
        provider = cfg.get("provider")
        if provider == "openai_compatible":
            return OpenAICompatibleAdapter(base_url=cfg.get("base_url"), api_key=cfg.get("api_key"), model_name=cfg.get("model_name"))
        if provider == "claude":
            return ClaudeAdapter(api_key=cfg.get("api_key"), model_name=cfg.get("model_name"))
        if provider == "gemini":
            return GeminiAdapter(api_key=cfg.get("api_key"), model_name=cfg.get("model_name"))

        raise ValueError(f"unknown provider: {provider}")
