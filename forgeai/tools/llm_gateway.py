"""LLM Gateway — Unified interface for calling LLM APIs.

Supports Google Gemini (primary), with extensible design for OpenAI/Anthropic.
Handles rate limiting, retries, token counting, and request/response logging.

Uses the google-genai SDK (google.genai) — the successor to google-generativeai.
"""

import json
import time
from typing import Optional

from google import genai
from google.genai import types as genai_types

from forgeai.core.activity_logger import ActivityLogger


class LLMGateway:
    """Unified LLM API interface with logging and retry logic."""

    def __init__(self, provider: str, model: str, api_key: str,
                 temperature: float = 0.2, max_tokens: int = 8192,
                 logger: Optional[ActivityLogger] = None):
        self.provider = provider
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.logger = logger

        # Counters for summary report
        self.total_api_calls = 0
        self.total_tokens_used = 0

        # Initialize provider
        if provider == "google":
            self._client = genai.Client(api_key=api_key)
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")

    def generate(self, prompt: str, system_instruction: str = "",
                 temperature: Optional[float] = None,
                 max_retries: int = 3) -> str:
        """Generate a response from the LLM.
        
        Args:
            prompt: The user/task prompt.
            system_instruction: System-level instruction for the model.
            temperature: Override default temperature.
            max_retries: Number of retry attempts on failure.
            
        Returns:
            The generated text response.
        """
        temp = temperature if temperature is not None else self.temperature

        for attempt in range(max_retries):
            try:
                if self.logger:
                    self.logger.api_call("LLMGateway", f"API call #{self.total_api_calls + 1} to {self.provider}/{self.model}", {
                        "prompt_length": len(prompt),
                        "attempt": attempt + 1,
                    })

                response = self._call_provider(prompt, system_instruction, temp)
                self.total_api_calls += 1

                # Estimate tokens (rough: 1 token ≈ 4 chars)
                est_tokens = (len(prompt) + len(response)) // 4
                self.total_tokens_used += est_tokens

                if self.logger:
                    self.logger.api_call("LLMGateway", f"Response received ({len(response)} chars, ~{est_tokens} tokens)")

                return response

            except Exception as e:
                error_msg = f"LLM API error (attempt {attempt + 1}/{max_retries}): {str(e)}"
                if self.logger:
                    self.logger.error("LLMGateway", error_msg)

                if attempt < max_retries - 1:
                    err_str = str(e)
                    is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
                    if is_rate_limit:
                        suggested = self._parse_retry_delay(e)
                        wait = max(suggested, 2 ** (attempt + 1))
                    else:
                        wait = 2 ** (attempt + 1)
                    time.sleep(wait)
                else:
                    raise RuntimeError(f"LLM API failed after {max_retries} attempts: {str(e)}")

    def _call_provider(self, prompt: str, system_instruction: str, temperature: float) -> str:
        """Call the configured LLM provider."""
        if self.provider == "google":
            return self._call_gemini(prompt, system_instruction, temperature)
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def _call_gemini(self, prompt: str, system_instruction: str, temperature: float) -> str:
        """Call Google Gemini API using the google-genai SDK."""
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=self.max_tokens,
            system_instruction=system_instruction if system_instruction else None,
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text

    def _call_gemini_json(self, prompt: str, system_instruction: str, temperature: float) -> str:
        """Call Gemini with response_mime_type=application/json for guaranteed JSON output."""
        config = genai_types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=self.max_tokens,
            system_instruction=system_instruction if system_instruction else None,
            response_mime_type="application/json",
        )

        response = self._client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        return response.text

    @staticmethod
    def _parse_retry_delay(error: Exception) -> float:
        """Extract retryDelay seconds from a Gemini 429 error, or return 0."""
        import re
        msg = str(error)
        m = re.search(r"retryDelay.*?(\d+)s", msg)
        if m:
            return float(m.group(1))
        return 0.0

    def generate_json(self, prompt: str, system_instruction: str = "",
                      max_retries: int = 5) -> dict:
        """Generate a response and parse it as JSON.

        Uses Gemini's native JSON mode (response_mime_type=application/json) so the
        model is constrained to emit valid JSON without prose or markdown fences.
        Respects Gemini's retryDelay on 429 errors and applies exponential backoff.
        """
        raw = ""
        for attempt in range(max_retries):
            try:
                if self.logger:
                    self.logger.api_call("LLMGateway",
                        f"JSON API call #{self.total_api_calls + 1} (attempt {attempt + 1})", {})

                raw = self._call_gemini_json(prompt, system_instruction, self.temperature)
                self.total_api_calls += 1
                est_tokens = (len(prompt) + len(raw)) // 4
                self.total_tokens_used += est_tokens

                if self.logger:
                    self.logger.api_call("LLMGateway",
                        f"Response received ({len(raw)} chars, ~{est_tokens} tokens)")

                return json.loads(raw)

            except json.JSONDecodeError as e:
                if self.logger:
                    self.logger.warn("LLMGateway", f"JSON parse failed (attempt {attempt + 1}): {str(e)}")
                start = raw.find("{")
                end = raw.rfind("}") + 1
                if start != -1 and end > start:
                    try:
                        return json.loads(raw[start:end])
                    except json.JSONDecodeError:
                        pass
                if attempt >= max_retries - 1:
                    raise

            except Exception as e:
                err_str = str(e)
                is_rate_limit = "429" in err_str or "RESOURCE_EXHAUSTED" in err_str
                if self.logger:
                    self.logger.error("LLMGateway",
                        f"JSON call failed (attempt {attempt + 1}): {err_str[:200]}")

                if attempt >= max_retries - 1:
                    raise RuntimeError(f"JSON generation failed after {max_retries} attempts: {err_str}")

                if is_rate_limit:
                    # Respect the API's suggested retry delay, then add backoff
                    suggested = self._parse_retry_delay(e)
                    wait = max(suggested, 2 ** (attempt + 1))
                    if self.logger:
                        self.logger.api_call("LLMGateway",
                            f"Rate limited — waiting {wait:.0f}s before retry")
                    time.sleep(wait)
                else:
                    time.sleep(2 ** (attempt + 1))

    def get_stats(self) -> dict:
        """Return usage statistics."""
        return {
            "total_api_calls": self.total_api_calls,
            "total_tokens_used": self.total_tokens_used,
            "provider": self.provider,
            "model": self.model,
        }
