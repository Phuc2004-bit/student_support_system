from __future__ import annotations

from collections.abc import Sequence
import re

from assistant.exceptions import AssistantError, AssistantValidationError, KnowledgeBaseError
from assistant.knowledge_base import KnowledgeBase
from assistant.models import AssistantRequest, AssistantResponse, ChatMessage, ChatRole
from assistant.policy import (
    OFFLINE_FALLBACK,
    SAFE_ERROR_RESPONSE,
    TopicGuard,
    refusal_for,
)
from assistant.providers import AssistantProvider, OfflineProvider


class ChatAssistantService:
    DEFAULT_HISTORY_LIMIT = 12
    MAX_MESSAGE_LENGTH = 2000
    MAX_RESPONSE_LENGTH = 4000

    def __init__(
        self,
        knowledge_base: KnowledgeBase | None = None,
        provider: AssistantProvider | None = None,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        topic_guard: TopicGuard | None = None,
    ) -> None:
        if isinstance(history_limit, bool) or not isinstance(history_limit, int) or history_limit <= 0:
            raise ValueError("history_limit phải là số nguyên dương.")
        if knowledge_base is not None:
            self.knowledge_base = knowledge_base
        else:
            try:
                self.knowledge_base = KnowledgeBase()
            except KnowledgeBaseError as exc:
                self.knowledge_base = _UnavailableKnowledgeBase(exc)
        self.provider = provider or OfflineProvider()
        self.history_limit = history_limit
        self.topic_guard = topic_guard or TopicGuard()

    @classmethod
    def from_settings(cls, settings: object | None = None) -> "ChatAssistantService":
        """Build the service from safe application settings without UI coupling."""
        if settings is None:
            from config.settings import Settings

            settings = Settings
        from assistant.providers.factory import create_provider

        return cls(provider=create_provider(settings))

    @property
    def provider_name(self) -> str:
        return str(getattr(self.provider, "provider_name", "offline"))

    @property
    def provider_status_label(self) -> str:
        return str(getattr(self.provider, "status_label", "Offline"))

    def ask(self, request: AssistantRequest) -> AssistantResponse:
        question, history = self._validate_request(request)
        decision = self.topic_guard.check(question)
        if not decision.allowed:
            return AssistantResponse(
                text=refusal_for(decision),
                source="policy",
                fallback_used=False,
            )

        chunks = []
        context = ""
        try:
            chunks = self.knowledge_base.search(question)
            if chunks and chunks[0].source == "offline:clarify":
                return AssistantResponse(
                    text=chunks[0].content,
                    source="offline:clarify",
                    fallback_used=True,
                )
            if not chunks and self.provider_name == "gemini":
                return self._offline_response(question, "", history, chunks)
            context = "\n\n".join(chunk.content for chunk in chunks)
            answer = self.provider.generate(question, context, history)
        except AssistantError:
            if self.provider_name == "gemini":
                return self._offline_response(question, context, history, chunks)
            return self._error_response()
        except Exception:
            if self.provider_name == "gemini":
                return self._offline_response(question, context, history, chunks)
            return self._error_response()

        sanitized = self._sanitize_response(answer)
        if sanitized is None:
            if self.provider_name == "gemini":
                return self._offline_response(question, context, history, chunks)
            return self._error_response()
        fallback_used = not chunks or sanitized == OFFLINE_FALLBACK
        sources = ", ".join(dict.fromkeys(chunk.source for chunk in chunks))
        return AssistantResponse(
            text=sanitized,
            source=sources or getattr(
                self.knowledge_base, "fallback_source", self.provider.provider_name
            ),
            fallback_used=fallback_used,
        )

    def _offline_response(
        self,
        question: str,
        context: str,
        history: Sequence[ChatMessage],
        chunks: Sequence,
    ) -> AssistantResponse:
        """Return deterministic static guidance after an online-provider failure."""
        try:
            answer = OfflineProvider().generate(question, context, history)
            sanitized = self._sanitize_response(answer)
        except Exception:
            sanitized = None
        if sanitized is None:
            return self._error_response()
        sources = ", ".join(dict.fromkeys(chunk.source for chunk in chunks))
        return AssistantResponse(
            text=sanitized,
            source=sources or getattr(self.knowledge_base, "fallback_source", "offline:fallback"),
            fallback_used=True,
        )

    def _validate_request(self, request: AssistantRequest) -> tuple[str, Sequence[ChatMessage]]:
        if not isinstance(request, AssistantRequest):
            raise AssistantValidationError("Yêu cầu trợ lý không hợp lệ.")
        if not isinstance(request.message, str) or not request.message.strip():
            raise AssistantValidationError("Vui lòng nhập câu hỏi.")
        question = request.message.strip()
        if len(question) > self.MAX_MESSAGE_LENGTH:
            raise AssistantValidationError("Câu hỏi quá dài.")
        if not isinstance(request.history, (tuple, list)):
            raise AssistantValidationError("Lịch sử hội thoại không hợp lệ.")
        for item in request.history:
            if (
                not isinstance(item, ChatMessage)
                or not isinstance(item.role, ChatRole)
                or not isinstance(item.content, str)
            ):
                raise AssistantValidationError("Lịch sử hội thoại không hợp lệ.")
        return question, tuple(request.history[-self.history_limit :])

    def _sanitize_response(self, answer: object) -> str | None:
        if not isinstance(answer, str):
            return None
        text = answer.replace("\x00", "").strip()
        if not text:
            return OFFLINE_FALLBACK
        sensitive_patterns = (
            r"(?i)password_hash\s*[=:]",
            r"(?i)DB_PASSWORD\s*[=:]",
            r"(?i)\bPWD\s*[=:]",
            r"(?i)api[_-]?key\s*[=:]",
            r"(?i)system prompt\s*[=:]",
            r"(?i)DRIVER\s*=.*SERVER\s*=.*DATABASE\s*=",
            r"(?i)\b(ignore|disregard)\b.*\b(previous|system)\b.*\b(instruction|prompt)s?\b",
            r"(?i)\b(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|EXEC)\s+\S+",
            r"(?i)\bt[oô]i\s+(?:đ[aã]|s[eẽ])\s+(?:sửa|xóa|cập nhật|đánh dấu|tạo|chuyển)\b",
        )
        if any(re.search(pattern, text) for pattern in sensitive_patterns):
            return None
        return text[: self.MAX_RESPONSE_LENGTH]

    @staticmethod
    def _error_response() -> AssistantResponse:
        return AssistantResponse(
            text=SAFE_ERROR_RESPONSE,
            source="error",
            fallback_used=True,
        )


class _UnavailableKnowledgeBase:
    """Delay a startup knowledge failure so requests receive a safe response."""

    fallback_source = "offline:fallback"

    def __init__(self, error: KnowledgeBaseError) -> None:
        self._error = error

    def search(self, question: str) -> list:
        del question
        raise self._error
