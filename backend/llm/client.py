"""
Thin wrapper around Groq's OpenAI-compatible chat endpoint.

This is the ONLY file that knows about Groq/httpx specifics. Every agent
(extractor, question_generator, grounding, novice) calls through
LLMClient.complete_json() and never touches the API directly. Swapping
providers later means editing only this file.
"""

from __future__ import annotations

import json
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.groq.com/openai/v1")
LLM_MODEL_DEFAULT = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class LLMError(Exception):
    """Raised when the LLM call fails or returns unparseable output after retry."""


class LLMClient:
    def __init__(self, model: str | None = None, timeout: float = 30.0):
        if not GROQ_API_KEY:
            raise LLMError(
                "GROQ_API_KEY is not set. Add it to backend/.env before making LLM calls."
            )
        self.model = model or LLM_MODEL_DEFAULT
        self.timeout = timeout
        self._client = httpx.Client(
            base_url=LLM_API_BASE,
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> dict:
        """
        Calls the model in JSON mode and returns a parsed dict.

        Tries once normally. If the response fails to parse as JSON, retries
        exactly once with a stricter instruction appended. Raises LLMError
        if it still fails — callers should decide how to degrade (e.g. skip
        this turn's extraction rather than crash the session).
        """
        raw = self._call(system_prompt, user_prompt, temperature)
        parsed = self._try_parse(raw)
        if parsed is not None:
            return parsed

        strict_system_prompt = (
            system_prompt
            + "\n\nCRITICAL: Your entire response must be a single valid JSON "
            "object. No markdown fences, no commentary, no text before or "
            "after the JSON."
        )
        raw_retry = self._call(strict_system_prompt, user_prompt, temperature)
        parsed_retry = self._try_parse(raw_retry)
        if parsed_retry is not None:
            return parsed_retry

        raise LLMError(
            f"Failed to parse JSON from model after retry. Last raw output:\n{raw_retry}"
        )

    def _call(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        try:
            response = self._client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": temperature,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise LLMError(f"LLM API returned {e.response.status_code}: {e.response.text}") from e
        except httpx.RequestError as e:
            raise LLMError(f"LLM API request failed: {e}") from e

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Unexpected LLM response shape: {data}") from e

    @staticmethod
    def _try_parse(raw: str) -> dict | None:
        text = raw.strip()
        # Strip markdown fences if the model added them despite instructions.
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            return None
        return result if isinstance(result, dict) else None

    def close(self) -> None:
        self._client.close()