"""LLM service — OpenAI primary, Groq (qwen3.8-27b) fallback, local distilgpt2 last resort."""
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
        self._groq_client = None
        self._openai_client: Optional[AsyncOpenAI] = None

        if settings.openai_api_key:
            logger.info("LLMService: using OpenAI (%s)", settings.openai_model)
            self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        elif settings.groq_api_key:
            logger.info("LLMService: using Groq (%s)", settings.groq_model)
            from groq import AsyncGroq
            self._groq_client = AsyncGroq(api_key=settings.groq_api_key)

    async def generate(self, system_prompt: str, user_prompt: str, max_tokens: int = 800, temperature: float = 0.2, max_retries: int = 3) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        if self._openai_client:
            for attempt in range(1, max_retries + 1):
                try:
                    resp = await self._openai_client.chat.completions.create(
                        model=settings.openai_model,
                        messages=messages,
                        max_tokens=max_tokens, temperature=temperature,
                    )
                    content = resp.choices[0].message.content
                    if content:
                        return content.strip()
                except (RateLimitError, APIConnectionError) as e:
                    await asyncio.sleep(2 ** attempt)
                except APIError:
                    break

        if self._groq_client:
            for attempt in range(1, max_retries + 1):
                try:
                    resp = await self._groq_client.chat.completions.create(
                        model=settings.groq_model,
                        messages=messages,
                        max_tokens=max_tokens, temperature=temperature,
                    )
                    content = resp.choices[0].message.content
                    if content:
                        return content.strip()
                except Exception as e:
                    logger.warning("Groq attempt %d failed: %s", attempt, e)
                    await asyncio.sleep(2 ** attempt)
            # Groq exhausted retries — fall through to local

        local = _load_local()
        if local is None:
            raise LLMServiceError("No LLM backend available. Set OPENAI_API_KEY or GROQ_API_KEY in .env.")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: local(user_prompt, max_new_tokens=256, num_return_sequences=1))
        text = result[0]["generated_text"]
        return text[len(user_prompt):].strip() or text.strip()
