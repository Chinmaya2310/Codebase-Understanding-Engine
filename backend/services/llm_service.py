"""LLM service with OpenAI primary and local fallback."""
from __future__ import annotations
import asyncio, logging
from functools import lru_cache
from typing import Optional
from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError
from backend.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMServiceError(Exception):
    pass


@lru_cache()
def _load_local():
    try:
        from transformers import pipeline
        model = settings.local_llm_model_path or "distilgpt2"
        logger.info("Loading local LLM: %s", model)
        return pipeline("text-generation", model=model)
    except Exception:
        return None


class LLMService:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 800, temperature: float = 0.2, max_retries: int = 3) -> str:
        if self._client:
            for attempt in range(1, max_retries + 1):
                try:
                    resp = await self._client.chat.completions.create(
                        model=settings.openai_model,
                        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                        max_tokens=max_tokens, temperature=temperature,
                    )
                    content = resp.choices[0].message.content
                    if content:
                        return content.strip()
                except (RateLimitError, APIConnectionError) as e:
                    await asyncio.sleep(2 ** attempt)
                except APIError:
                    break
        local = _load_local()
        if local is None:
            raise LLMServiceError("No LLM backend available. Set OPENAI_API_KEY in .env to enable Q&A.")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: local(user_prompt, max_new_tokens=256, num_return_sequences=1))
        text = result[0]["generated_text"]
        return text[len(user_prompt):].strip() or text.strip()
