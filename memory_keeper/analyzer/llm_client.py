"""Async LLM client for Memory Keeper analyzer."""

import json
import re
from typing import Optional

import httpx

from memory_keeper.config import LLMConfig


class LLMClientError(Exception):
    """Raised when LLM client encounters an error."""


class LLMClient:
    """Async HTTP client for calling LLM APIs.

    Supports OpenAI-compatible endpoints (OpenAI, DeepSeek, local LLMs)
    and Anthropic's API format.
    """

    def __init__(self, config: LLMConfig):
        self.config = config
        self.provider = config.provider
        self.model = config.model
        self.api_key = config.api_key
        self.temperature = config.temperature
        self.max_tokens = config.max_tokens

        # Determine base URL
        if config.api_base:
            self.api_base = config.api_base.rstrip("/")
        elif self.provider == "anthropic":
            self.api_base = "https://api.anthropic.com"
        else:
            self.api_base = "https://api.openai.com"

    async def call(self, system_prompt: str, user_prompt: str) -> str:
        """Send a chat completion request and return the text response."""
        if self.provider == "anthropic":
            return await self._call_anthropic(system_prompt, user_prompt)
        return await self._call_openai_compatible(system_prompt, user_prompt)

    async def call_json(self, system_prompt: str, user_prompt: str) -> dict:
        """Call the LLM and parse the response as JSON.

        Retries up to 3 times on JSON parse failures.
        """
        last_error = None
        for attempt in range(3):
            try:
                raw = await self.call(system_prompt, user_prompt)
                return self._extract_json(raw)
            except (json.JSONDecodeError, ValueError) as e:
                last_error = e
                if attempt < 2:
                    # Retry with a nudge to return valid JSON
                    user_prompt = (
                        f"{user_prompt}\n\n"
                        "IMPORTANT: You must respond with valid JSON only. "
                        "No markdown, no explanation, just the JSON object."
                    )
        raise LLMClientError(f"Failed to parse JSON after 3 attempts: {last_error}")

    async def _call_openai_compatible(self, system_prompt: str, user_prompt: str) -> str:
        """Call an OpenAI-compatible API endpoint."""
        url = f"{self.api_base}/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        return await self._send_request(url, headers, payload, parser=self._parse_openai)

    async def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        """Call the Anthropic Messages API."""
        url = f"{self.api_base}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
        }

        payload = {
            "model": self.model,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        return await self._send_request(url, headers, payload, parser=self._parse_anthropic)

    async def _send_request(self, url: str, headers: dict, payload: dict, parser) -> str:
        """Send HTTP request with retry logic."""
        last_error = None
        for attempt in range(3):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    return parser(response.json())
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500 or e.response.status_code == 429:
                    last_error = e
                    # Exponential backoff: 2s, 4s
                    import asyncio
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                raise LLMClientError(
                    f"LLM API error {e.response.status_code}: {e.response.text}"
                ) from e
            except httpx.RequestError as e:
                last_error = e
                import asyncio
                await asyncio.sleep(2 ** (attempt + 1))

        raise LLMClientError(f"LLM request failed after 3 retries: {last_error}")

    @staticmethod
    def _parse_openai(data: dict) -> str:
        """Parse OpenAI-compatible response."""
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMClientError(f"Unexpected OpenAI response format: {data}") from e

    @staticmethod
    def _parse_anthropic(data: dict) -> str:
        """Parse Anthropic Messages API response."""
        try:
            return data["content"][0]["text"]
        except (KeyError, IndexError) as e:
            raise LLMClientError(f"Unexpected Anthropic response format: {data}") from e

    @staticmethod
    def _extract_json(text: str) -> dict:
        """Extract JSON from LLM response text.

        Handles markdown code fences and extra text around JSON.
        """
        # Strip markdown code fences
        cleaned = re.sub(r"```(?:json)?\s*", "", text)
        cleaned = cleaned.strip()

        # Try direct parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Find first JSON object in text
        brace_start = cleaned.find("{")
        if brace_start == -1:
            raise ValueError(f"No JSON object found in response: {text[:200]}")

        # Find matching closing brace
        depth = 0
        for i in range(brace_start, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    return json.loads(cleaned[brace_start : i + 1])

        raise ValueError(f"Unmatched braces in response: {text[:200]}")
