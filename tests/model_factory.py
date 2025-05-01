from core.llm.model_config import LLMModelConfig
from tests.test_settings import TestSettings
from .llm import LiteLLMWrapper


def get_model_for_experiment(model_name: str) -> LiteLLMWrapper:
    """
    Factory to create LiteLLMWrapper based on model_name.
    Automatically resolves which API key to use.
    Raises ValueError if API key is missing.
    """
    test_settings = TestSettings()

    if model_name.startswith("gpt-") or model_name.startswith("openai/"):
        api_key = test_settings.openai_api_key
        provider = "OpenAI"
    elif model_name.startswith("gemini/") or model_name.startswith("vertex_ai/"):
        api_key = test_settings.gemini_api_key
        provider = "Gemini"
    elif model_name.startswith("together_ai/"):
        api_key = test_settings.together_ai_api_key
        provider = "TogetherAI"
    else:
        raise ValueError(f"Unsupported model provider for model_name='{model_name}'")

    if not api_key:
        raise ValueError(f"API key for {provider} is not defined.")

    model_cfg = LLMModelConfig(model_name=model_name, api_key=api_key)
    return LiteLLMWrapper(model_cfg=model_cfg)

