from __future__ import annotations

from collections.abc import Callable, Sequence
import logging

import httpx
from google import genai
from google.genai import errors, types

from assistant.exceptions import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderResponseError,
    ProviderTransientError,
)
from assistant.models import ChatMessage
from assistant.policy import build_system_policy, sanitize_history
from assistant.providers.base import AssistantProvider


LOGGER = logging.getLogger(__name__)
TRANSIENT_STATUS_CODES = (408, 429, 500, 502, 503, 504)


class GeminiProvider(AssistantProvider):
    """Official Google Gen AI provider grounded only in supplied static context."""

    provider_name = "gemini"
    status_label = "Trực tuyến"

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout_seconds: float = 15.0,
        max_retries: int = 1,
        client: object | None = None,
        client_factory: Callable[..., object] | None = None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ProviderAuthenticationError("Gemini provider is not configured.")
        if not isinstance(model, str) or not model.strip():
            raise ProviderError("Gemini model is not configured.")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not 1 <= float(timeout_seconds) <= 60
        ):
            raise ProviderError("Gemini timeout configuration is invalid.")
        if (
            isinstance(max_retries, bool)
            or not isinstance(max_retries, int)
            or not 0 <= max_retries <= 2
        ):
            raise ProviderError("Gemini retry configuration is invalid.")

        self.model = model.strip()
        self.timeout_seconds = float(timeout_seconds)
        self.max_retries = max_retries
        self.http_options = types.HttpOptions(
            timeout=int(self.timeout_seconds * 1000),
            retry_options=types.HttpRetryOptions(
                attempts=max_retries + 1,
                initial_delay=0.5,
                max_delay=2.0,
                exp_base=2.0,
                jitter=0.2,
                http_status_codes=list(TRANSIENT_STATUS_CODES),
            ),
        )
        if client is not None:
            self._client = client
        else:
            factory = client_factory or genai.Client
            try:
                self._client = factory(
                    api_key=api_key.strip(),
                    http_options=self.http_options,
                )
            except Exception as exc:
                raise ProviderError("Gemini provider initialization failed.") from exc

    def generate(
        self,
        question: str,
        context: str,
        history: Sequence[ChatMessage],
    ) -> str:
        if not isinstance(context, str) or not context.strip():
            raise ProviderResponseError("Static knowledge context is required.")

        contents = self._build_grounded_prompt(question, context, history)
        config = types.GenerateContentConfig(
            system_instruction=build_system_policy(),
            temperature=0.2,
            max_output_tokens=700,
        )
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=contents,
                config=config,
            )
            text = response.text
        except errors.ClientError as exc:
            self._raise_client_error(exc)
        except errors.ServerError as exc:
            LOGGER.warning("Gemini provider transient failure")
            raise ProviderTransientError("Gemini provider temporarily unavailable.") from exc
        except (TimeoutError, httpx.TimeoutException, httpx.NetworkError) as exc:
            LOGGER.warning("Gemini provider transient failure")
            raise ProviderTransientError("Gemini provider temporarily unavailable.") from exc
        except Exception as exc:
            LOGGER.warning("Gemini provider request failed")
            raise ProviderError("Gemini provider request failed.") from exc

        if not isinstance(text, str) or not text.strip():
            raise ProviderResponseError("Gemini provider returned no usable text.")
        return text.strip()

    @staticmethod
    def _build_grounded_prompt(
        question: str,
        context: str,
        history: Sequence[ChatMessage],
    ) -> str:
        safe_history = sanitize_history(tuple(history), limit=12)
        history_text = "\n".join(
            f"{message.role.value.upper()}: {message.content.strip()}"
            for message in safe_history
        ) or "(không có)"
        return (
            "STATIC APP KNOWLEDGE (nguồn duy nhất để trả lời):\n"
            f"{context.strip()}\n\n"
            "SANITIZED CONVERSATION HISTORY:\n"
            f"{history_text}\n\n"
            "USER QUESTION:\n"
            f"{question.strip()}\n\n"
            "Chỉ trả lời câu hỏi bằng static knowledge ở trên. "
            "Nếu knowledge không đủ, hãy nói rõ không có thông tin phù hợp."
        )

    @staticmethod
    def _raise_client_error(exc: errors.ClientError) -> None:
        code = int(getattr(exc, "code", 0) or 0)
        if code in (401, 403):
            LOGGER.warning("Gemini provider authentication failed")
            raise ProviderAuthenticationError(
                "Gemini provider authentication failed."
            ) from exc
        if code in TRANSIENT_STATUS_CODES:
            LOGGER.warning("Gemini provider transient failure")
            raise ProviderTransientError(
                "Gemini provider temporarily unavailable."
            ) from exc
        LOGGER.warning("Gemini provider request rejected")
        raise ProviderError("Gemini provider request rejected.") from exc
