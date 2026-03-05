from .adapters.oai_adapter import OpenAICompatibleAdapter
from .adapters.claude_adapter import ClaudeAdapter
from .adapters.gemini_adapter import GeminiAdapter


class ModelFactory:

    @staticmethod
    def create(config: dict):

        provider = config["provider"]

        if provider == "openai_compatible":
            return OpenAICompatibleAdapter(
                base_url=config.get("base_url"),
                api_key=config.get("api_key"),
                model_name=config.get("model_name"),
            )

        if provider == "claude":
            return ClaudeAdapter(
                api_key=config.get("api_key"),
                model_name=config.get("model_name"),
            )

        if provider == "gemini":
            return GeminiAdapter(
                api_key=config.get("api_key"),
                model_name=config.get("model_name"),
            )

        raise ValueError("Unsupported provider")