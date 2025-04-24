from dataclasses import dataclass

@dataclass
class LLMModelConfig:
    model_name: str
    api_key: str
    temperature: float = 0.7
    max_tokens: int = 2000

