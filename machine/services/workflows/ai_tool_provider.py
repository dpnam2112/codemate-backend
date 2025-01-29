from enum import StrEnum
import functools
import inspect

from typing import Callable, Coroutine
from langchain_core.embeddings import Embeddings

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from core.settings import settings

class EmbeddingsModelName(StrEnum):
    GOOGLE_TEXT_EMBEDDING = "models/text-embedding-004"

class LLMModelName(StrEnum):
    GEMINI_PRO = "gemini-1.5-pro"
    GPT_4O_MINI = "gpt-4o-mini"

class AIToolProvider:
    """Provide dependencies related to ML/LLM tasks."""
    def __init__(self): pass

    def embedding_models_factory(self, modelname: EmbeddingsModelName) -> Embeddings: 
        """Factory for embedding models."""
        if modelname == EmbeddingsModelName.GOOGLE_TEXT_EMBEDDING:
            embeddings = GoogleGenerativeAIEmbeddings(
                    model="models/embedding-001",
                    google_api_key=settings.GOOGLE_GENAI_API_KEY
                )

        return embeddings

    def chat_model_factory(self, modelname: LLMModelName) -> BaseChatModel:

        if modelname == LLMModelName.GEMINI_PRO:
            llm = ChatGoogleGenerativeAI(
                model="gemini-1.5-pro",
                temperature=0,
                max_tokens=None,
                timeout=None,
                max_retries=2,
                api_key=settings.GOOGLE_GENAI_API_KEY
            )
        elif modelname == LLMModelName.GPT_4O_MINI:
            llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.5,
                timeout=None,
                max_retries=2,
                api_key=settings.OPENAI_API_KEY
            )

        return llm

    def inject_embeddings_model(
        self,
        argname: str,
        modelname: EmbeddingsModelName
    ) -> Callable:
        """
        injects an embeddings model into the callback.
        The callback must have 'embeddings_model' as a parameter.
        """
        def _decorator(callback: Callable):
            signature = inspect.signature(callback)

            return_type = signature.return_annotation

            # Create the embedding model asynchronously
            embeddings_model = self.embedding_models_factory(modelname)

            # Wrap the callback and inject the embedding model
            if isinstance(return_type, Coroutine):
                @functools.wraps(callback)
                async def async_wrapper(*args, **kwargs):
                    if kwargs[argname] is None:
                        kwargs[argname] = embeddings_model

                    return await callback(*args, **kwargs)
                
                return async_wrapper
            else:
                @functools.wraps(callback)
                def wrapper(*args, **kwargs):
                    if kwargs.get(argname) is None:
                        kwargs[argname] = embeddings_model

                    return callback(*args, **kwargs)
                
                return wrapper

        return _decorator

    def inject_llm_model(
        self,
        argname: str,
        modelname = None
    ) -> Callable:
        def _decorator(callback: Callable):
            signature = inspect.signature(callback)

            return_type = signature.return_annotation

            # Create the embedding model asynchronously
            llm_model = self.chat_model_factory(modelname)

            # Wrap the callback and inject the embedding model
            if isinstance(return_type, Coroutine):
                @functools.wraps(callback)
                async def async_wrapper(*args, **kwargs):
                    if kwargs.get(argname) is None:
                        kwargs[argname] = llm_model

                    return await callback(*args, **kwargs)
                
                return async_wrapper
            else:
                @functools.wraps(callback)
                def wrapper(*args, **kwargs):
                    if kwargs.get(argname) is None:
                        kwargs[argname] = llm_model

                    return callback(*args, **kwargs)
                
                return wrapper

        return _decorator
