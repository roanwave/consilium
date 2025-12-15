"""Unified LLM client for Consilium.

Supports Anthropic (Claude), OpenAI (GPT), and OpenRouter APIs.
Routes requests based on MODEL_ASSIGNMENTS configuration.
"""

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import httpx
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import BaseModel

from backend.config import (
    MODEL_ASSIGNMENTS,
    ModelConfig,
    ModelProvider,
    ModelType,
    Settings,
    get_settings,
)
from backend.lib.exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMContextLengthError,
    LLMRateLimitError,
    LLMResponseParseError,
)
from backend.lib.models import ExpertContribution, TokenUsage

logger = logging.getLogger(__name__)


# =============================================================================
# Response Models
# =============================================================================


class LLMResponse(BaseModel):
    """Unified response from LLM."""

    content: str
    token_usage: TokenUsage
    model: str
    finish_reason: str | None = None


class StreamChunk(BaseModel):
    """A chunk from streaming response."""

    content: str
    is_final: bool = False
    token_usage: TokenUsage | None = None


# =============================================================================
# LLM Client
# =============================================================================


class LLMClient:
    """
    Unified client for LLM APIs.

    Routes requests to Anthropic, OpenAI, or OpenRouter based on model config.
    Tracks token usage per expert for cost monitoring.
    """

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._anthropic_client: AsyncAnthropic | None = None
        self._openai_client: AsyncOpenAI | None = None
        self._http_client: httpx.AsyncClient | None = None

        # Token tracking per expert
        self._token_usage: dict[str, TokenUsage] = {}

    async def __aenter__(self) -> "LLMClient":
        """Async context manager entry."""
        await self._ensure_clients()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_clients(self) -> None:
        """Initialize clients if needed."""
        if self._anthropic_client is None and self.settings.has_anthropic_key:
            self._anthropic_client = AsyncAnthropic(
                api_key=self.settings.anthropic_api_key,
            )

        if self._openai_client is None and self.settings.has_openai_key:
            self._openai_client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
            )

        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(120.0, connect=10.0),
            )

    async def close(self) -> None:
        """Close all clients."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    def _get_provider(self, model: str) -> ModelProvider:
        """Determine provider for a model."""
        return self.settings.get_model_provider(model)

    def _track_usage(
        self, expert: str, input_tokens: int, output_tokens: int
    ) -> None:
        """Track cumulative token usage per expert."""
        if expert not in self._token_usage:
            self._token_usage[expert] = TokenUsage()
        self._token_usage[expert].input_tokens += input_tokens
        self._token_usage[expert].output_tokens += output_tokens

    def get_usage_summary(self) -> dict[str, dict[str, int]]:
        """Return token usage by expert for cost tracking."""
        return {
            expert: {"input": usage.input_tokens, "output": usage.output_tokens}
            for expert, usage in self._token_usage.items()
        }

    # =========================================================================
    # Anthropic API
    # =========================================================================

    async def _complete_anthropic(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        expert: str | None = None,
    ) -> LLMResponse:
        """Complete using Anthropic API."""
        await self._ensure_clients()

        if not self._anthropic_client:
            raise LLMAuthenticationError("Anthropic API key not configured")

        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system:
                kwargs["system"] = system

            response = await self._anthropic_client.messages.create(**kwargs)

            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens

            token_usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=getattr(
                    response.usage, "cache_read_input_tokens", 0
                )
                or 0,
                cache_creation_tokens=getattr(
                    response.usage, "cache_creation_input_tokens", 0
                )
                or 0,
                model=model,
            )

            if expert:
                self._track_usage(expert, input_tokens, output_tokens)

            return LLMResponse(
                content=content,
                token_usage=token_usage,
                model=model,
                finish_reason=response.stop_reason,
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "429" in error_msg:
                raise LLMRateLimitError(str(e))
            if "context length" in error_msg or "too many tokens" in error_msg:
                raise LLMContextLengthError(str(e))
            if "authentication" in error_msg or "401" in error_msg:
                raise LLMAuthenticationError(str(e))
            raise LLMConnectionError(str(e))

    async def _stream_anthropic(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """Stream using Anthropic API."""
        await self._ensure_clients()

        if not self._anthropic_client:
            raise LLMAuthenticationError("Anthropic API key not configured")

        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system:
                kwargs["system"] = system

            async with self._anthropic_client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(content=text)

                # Final message with usage
                final = await stream.get_final_message()
                token_usage = TokenUsage(
                    input_tokens=final.usage.input_tokens,
                    output_tokens=final.usage.output_tokens,
                    model=model,
                )
                yield StreamChunk(content="", is_final=True, token_usage=token_usage)

        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg:
                raise LLMRateLimitError(str(e))
            raise LLMConnectionError(str(e))

    # =========================================================================
    # OpenAI API
    # =========================================================================

    async def _complete_openai(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        expert: str | None = None,
    ) -> LLMResponse:
        """Complete using OpenAI API."""
        await self._ensure_clients()

        if not self._openai_client:
            raise LLMAuthenticationError("OpenAI API key not configured")

        # Build messages list with system message
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        try:
            response = await self._openai_client.chat.completions.create(
                model=model,
                messages=all_messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )

            content = response.choices[0].message.content or ""
            input_tokens = response.usage.prompt_tokens if response.usage else 0
            output_tokens = response.usage.completion_tokens if response.usage else 0

            token_usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=model,
            )

            if expert:
                self._track_usage(expert, input_tokens, output_tokens)

            return LLMResponse(
                content=content,
                token_usage=token_usage,
                model=model,
                finish_reason=response.choices[0].finish_reason,
            )

        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "429" in error_msg:
                raise LLMRateLimitError(str(e))
            if "context length" in error_msg or "too many tokens" in error_msg:
                raise LLMContextLengthError(str(e))
            if "authentication" in error_msg or "401" in error_msg:
                raise LLMAuthenticationError(str(e))
            raise LLMConnectionError(str(e))

    async def _stream_openai(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """Stream using OpenAI API."""
        await self._ensure_clients()

        if not self._openai_client:
            raise LLMAuthenticationError("OpenAI API key not configured")

        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        try:
            stream = await self._openai_client.chat.completions.create(
                model=model,
                messages=all_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamChunk(content=chunk.choices[0].delta.content)
                if chunk.choices and chunk.choices[0].finish_reason:
                    yield StreamChunk(content="", is_final=True)

        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg:
                raise LLMRateLimitError(str(e))
            raise LLMConnectionError(str(e))

    # =========================================================================
    # OpenRouter API
    # =========================================================================

    async def _complete_openrouter(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        expert: str | None = None,
    ) -> LLMResponse:
        """Complete using OpenRouter API."""
        await self._ensure_clients()

        if not self.settings.has_openrouter_key:
            raise LLMAuthenticationError("OpenRouter API key not configured")

        # Prepend system message if provided
        all_messages = messages.copy()
        if system:
            all_messages.insert(0, {"role": "system", "content": system})

        payload = {
            "model": model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            assert self._http_client is not None
            response = await self._http_client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                    "HTTP-Referer": "https://consilium.local",
                    "X-Title": "Consilium",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            if response.status_code == 429:
                raise LLMRateLimitError("OpenRouter rate limit exceeded")
            if response.status_code == 401:
                raise LLMAuthenticationError("OpenRouter authentication failed")

            response.raise_for_status()
            data = response.json()

            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)

            token_usage = TokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                model=model,
            )

            if expert:
                self._track_usage(expert, input_tokens, output_tokens)

            return LLMResponse(
                content=content,
                token_usage=token_usage,
                model=model,
                finish_reason=data["choices"][0].get("finish_reason"),
            )

        except httpx.HTTPStatusError as e:
            raise LLMConnectionError(f"OpenRouter HTTP error: {e}")
        except httpx.RequestError as e:
            raise LLMConnectionError(f"OpenRouter connection error: {e}")

    async def _stream_openrouter(
        self,
        model: str,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """Stream using OpenRouter API."""
        await self._ensure_clients()

        if not self.settings.has_openrouter_key:
            raise LLMAuthenticationError("OpenRouter API key not configured")

        all_messages = messages.copy()
        if system:
            all_messages.insert(0, {"role": "system", "content": system})

        payload = {
            "model": model,
            "messages": all_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
        }

        try:
            assert self._http_client is not None
            async with self._http_client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.settings.openrouter_api_key}",
                    "HTTP-Referer": "https://consilium.local",
                    "X-Title": "Consilium",
                    "Content-Type": "application/json",
                },
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            yield StreamChunk(content="", is_final=True)
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield StreamChunk(content=content)
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            raise LLMConnectionError(f"OpenRouter HTTP error: {e}")
        except httpx.RequestError as e:
            raise LLMConnectionError(f"OpenRouter connection error: {e}")

    # =========================================================================
    # Public API
    # =========================================================================

    async def complete(
        self,
        model: str | ModelType,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        retries: int = 3,
        retry_delay: float = 1.0,
        expert: str | None = None,
    ) -> LLMResponse:
        """
        Complete a chat conversation.

        Args:
            model: Model to use (ModelType enum or string)
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            retries: Number of retries on transient errors
            retry_delay: Initial delay between retries (exponential backoff)
            expert: Expert codename for token tracking

        Returns:
            LLMResponse with content and token usage
        """
        model_str = model.value if isinstance(model, ModelType) else model
        provider = self._get_provider(model_str)

        for attempt in range(retries):
            try:
                if provider == ModelProvider.ANTHROPIC:
                    return await self._complete_anthropic(
                        model_str, messages, system, max_tokens, temperature, expert
                    )
                elif provider == ModelProvider.OPENAI:
                    return await self._complete_openai(
                        model_str, messages, system, max_tokens, temperature, expert
                    )
                else:
                    return await self._complete_openrouter(
                        model_str, messages, system, max_tokens, temperature, expert
                    )
            except LLMRateLimitError:
                if attempt < retries - 1:
                    delay = retry_delay * (2**attempt)
                    logger.warning(f"Rate limited, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    raise
            except LLMConnectionError:
                if attempt < retries - 1:
                    delay = retry_delay * (2**attempt)
                    logger.warning(f"Connection error, retrying in {delay}s...")
                    await asyncio.sleep(delay)
                else:
                    raise

        # Should never reach here
        raise LLMConnectionError("Max retries exceeded")

    async def complete_for_expert(
        self,
        expert_codename: str,
        system: str,
        prompt: str,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        """
        Complete a request for a specific expert using MODEL_ASSIGNMENTS.

        Args:
            expert_codename: The expert's codename (e.g., "strategist", "auditor")
            system: System prompt
            prompt: User prompt
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with content and token usage
        """
        config = MODEL_ASSIGNMENTS.get(expert_codename)
        if not config:
            raise ValueError(f"Unknown expert: {expert_codename}")

        messages = [{"role": "user", "content": prompt}]

        return await self.complete(
            model=config.model_id,
            messages=messages,
            system=system,
            max_tokens=max_tokens,
            expert=expert_codename,
        )

    async def stream(
        self,
        model: str | ModelType,
        messages: list[dict[str, Any]],
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[StreamChunk]:
        """
        Stream a chat conversation.

        Args:
            model: Model to use
            messages: List of message dicts
            system: Optional system prompt
            max_tokens: Maximum tokens
            temperature: Sampling temperature

        Yields:
            StreamChunk objects with content
        """
        model_str = model.value if isinstance(model, ModelType) else model
        provider = self._get_provider(model_str)

        if provider == ModelProvider.ANTHROPIC:
            async for chunk in self._stream_anthropic(
                model_str, messages, system, max_tokens, temperature
            ):
                yield chunk
        elif provider == ModelProvider.OPENAI:
            async for chunk in self._stream_openai(
                model_str, messages, system, max_tokens, temperature
            ):
                yield chunk
        else:
            async for chunk in self._stream_openrouter(
                model_str, messages, system, max_tokens, temperature
            ):
                yield chunk

    # =========================================================================
    # Structured Output Parsing
    # =========================================================================

    def parse_expert_contribution(
        self,
        response: LLMResponse,
        expert_codename: str,
    ) -> ExpertContribution:
        """
        Parse LLM response into ExpertContribution.

        Expects response to contain JSON or structured format.
        """
        content = response.content.strip()

        # Try to extract JSON from response
        try:
            # Look for JSON block
            if "```json" in content:
                start = content.find("```json") + 7
                end = content.find("```", start)
                json_str = content[start:end].strip()
            elif content.startswith("{"):
                json_str = content
            else:
                # Try to find JSON object in content
                start = content.find("{")
                end = content.rfind("}") + 1
                if start >= 0 and end > start:
                    json_str = content[start:end]
                else:
                    raise LLMResponseParseError(
                        "No JSON found in response", raw_response=content
                    )

            data = json.loads(json_str)
            return ExpertContribution(
                expert=expert_codename,
                domain_claims=data.get("domain_claims", []),
                assumptions=data.get("assumptions", []),
                questions_remaining=data.get("questions_remaining", []),
                delta_requests=data.get("delta_requests", []),
                narrative_fragment=data.get("narrative_fragment", ""),
            )

        except json.JSONDecodeError as e:
            raise LLMResponseParseError(
                f"Invalid JSON in response: {e}", raw_response=content
            )

    async def complete_structured(
        self,
        model: str | ModelType,
        messages: list[dict[str, Any]],
        system: str | None = None,
        expert_codename: str = "unknown",
        **kwargs: Any,
    ) -> tuple[ExpertContribution, TokenUsage]:
        """
        Complete and parse into ExpertContribution.

        Returns:
            Tuple of (ExpertContribution, TokenUsage)
        """
        response = await self.complete(model, messages, system, **kwargs)
        contribution = self.parse_expert_contribution(response, expert_codename)
        return contribution, response.token_usage


# =============================================================================
# Module-level client factory
# =============================================================================


_default_client: LLMClient | None = None


async def get_llm_client() -> LLMClient:
    """Get the default LLM client instance."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
        await _default_client._ensure_clients()
    return _default_client


async def close_llm_client() -> None:
    """Close the default LLM client."""
    global _default_client
    if _default_client:
        await _default_client.close()
        _default_client = None
