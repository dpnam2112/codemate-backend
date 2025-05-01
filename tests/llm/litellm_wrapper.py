import backoff
import concurrent.futures
from pydantic import BaseModel
from core.llm import LLMModelConfig
from deepeval.models.base_model import DeepEvalBaseLLM
from litellm import acompletion, completion
from litellm.exceptions import RateLimitError
from typing import Optional, Type


class LiteLLMWrapper(DeepEvalBaseLLM):
    def __init__(self, model_cfg: LLMModelConfig):
        self.llm_cfg = model_cfg

    @backoff.on_exception(
        backoff.expo,
        RateLimitError,
        max_tries=10,
        jitter=backoff.full_jitter,
        base=3,
        factor=3
    )
    def generate(self, prompt: str) -> str:
        response = completion(
            model=self.llm_cfg.model_name,
            messages=[{"role": "user", "content": prompt}],
            api_key=self.llm_cfg.api_key
        )
        return response['choices'][0]['message']['content']

    @backoff.on_exception(
        backoff.expo,
        RateLimitError,
        max_tries=10,
        jitter=backoff.full_jitter,
        base=2,
        factor=1
    )
    async def a_generate(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None
    ) -> BaseModel | str:
        response = await acompletion(
            model=self.llm_cfg.model_name,
            messages=[{"role": "user", "content": prompt}],
            api_key=self.llm_cfg.api_key,
            response_format=schema
        )

        response_content = response['choices'][0]['message']['content']
        if schema:
            return schema.model_validate_json(response_content)

        return response_content

    @backoff.on_exception(
        backoff.expo,
        RateLimitError,
        max_tries=10,
        jitter=backoff.full_jitter,
        base=2,
        factor=1
    )
    def _generate_single(self, prompt: str) -> str:
        """
        Internal helper for a single sync prompt generation, with retry.
        """
        response = completion(
            model=self.llm_cfg.model_name,
            messages=[{"role": "user", "content": prompt}],
            api_key=self.llm_cfg.api_key
        )
        return response['choices'][0]['message']['content']

    def batch_generate(self, prompts: list[str]) -> list[str]:
        """
        Batch prompt generation using threads for concurrent API calls.
        """
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(prompts))) as executor:
            futures = [executor.submit(self._generate_single, prompt) for prompt in prompts]
            for future in concurrent.futures.as_completed(futures):
                results.append(future.result())
        return results

    def get_model_name(self) -> str:
        return self.llm_cfg.model_name

    def load_model(self):
        # LiteLLM handles model loading internally
        return self.model_name
