"""
llm.py
------
This file contains utility functions for processing calls to LLMs.
"""

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic
import asyncio
import os
from tenacity import (
    retry,
    wait_exponential,
    stop_after_attempt,
    retry_if_exception_type,
)
from openai import APIError, RateLimitError
from anthropic import (
    AsyncAnthropic,
    APIError as AnthropicAPIError,
    RateLimitError as AnthropicRateLimitError,
)

MODEL_FAMILIES = {
    "gpt-4.1": {"provider": "openai", "context_window": 1000000},
    "gpt-4.1-mini": {"provider": "openai", "context_window": 1000000},
    "gpt-5-mini": {"provider": "openai", "context_window": 1000000},
    "claude-sonnet-4-5-20250929": {"provider": "anthropic", "context_window": 1000000},
}


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=6),
    stop=stop_after_attempt(3),
    retry=retry_if_exception_type((AnthropicAPIError, AnthropicRateLimitError)),
)
async def call_anthropic(
    client: AsyncAnthropic,
    model: str,
    prompt: str,
    *,
    temperature: float = 1.0,
    max_tokens: int = 5000,
    system: str | None = None,
) -> str:
    """
    Call Anthropic Messages API and return the text content of the first response block.

    Parameters
    ----------
    client
        An instance of `AsyncAnthropic` (already configured with API key).
    model
        Claude model identifier to call.
    prompt
        User prompt/message content.
    temperature
        Sampling temperature for Claude (default 1.0).
    max_tokens
        Maximum number of tokens to generate.
    system
        Optional system prompt to prepend.
    """
    if not isinstance(client, AsyncAnthropic):
        raise TypeError("call_anthropic expects an AsyncAnthropic client.")

    messages = [{"role": "user", "content": prompt}]
    if system:
        # Anthropic SDK accepts a string for system prompt instead of a message block.
        response = await client.messages.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
        )
    else:
        response = await client.messages.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
        )

    # Concatenate all text blocks in the response.
    parts = [
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text" and hasattr(block, "text")
    ]
    if not parts:
        raise ValueError("Anthropic response did not include any text content.")
    return "".join(parts)


@retry(
    wait=wait_exponential(multiplier=1, min=2, max=5),
    stop=stop_after_attempt(1),
    retry=retry_if_exception_type((APIError, RateLimitError)),
)
async def call_gpt(client, prompt, model, resp_format=None):
    try:
        if resp_format == None:
            resp = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "text"},
            )
            return resp.choices[0].message.content
        else:
            resp = await client.responses.parse(
                model=model,
                input=[{"role": "user", "content": prompt}],
                text_format=resp_format,
            )

            return resp.output_parsed
    except Exception as e:
        print(e)


class LLM:
    def __init__(self, name: str, api_key: str):
        self.model_name = name
        if self.model_name not in MODEL_FAMILIES:
            raise ValueError(f"Model {self.model_name} not found")
        self.provider = MODEL_FAMILIES[self.model_name]["provider"]
        self.client = self.setup_llm_fn(api_key)
        self._sem = asyncio.Semaphore(int(os.getenv("LLM_CONCURRENCY", "16")))

    def setup_llm_fn(self, api_key) -> AsyncOpenAI | AsyncAnthropic:
        if self.provider == "openai":
            llm_client = AsyncOpenAI(
                api_key=api_key,
            )
        elif self.provider == "anthropic":
            llm_client = AsyncAnthropic(
                api_key=api_key,
            )
        else:
            raise ValueError(f"Provider {self.provider} not supported")
        return llm_client

    async def call(self, prompt: str, resp_format=None):
        async with self._sem:
            if self.provider == "openai":
                if resp_format == None:
                    is_structured = False
                else:
                    is_structured = True
                return await call_gpt(
                    client=self.client,
                    prompt=prompt,
                    model=self.model_name,
                    resp_format=resp_format,
                )
            elif self.provider == "anthropic":
                return await call_anthropic(
                    client=self.client, prompt=prompt, model=self.model_name
                )
