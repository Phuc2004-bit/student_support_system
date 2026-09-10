from __future__ import annotations

from collections.abc import Sequence

from assistant.models import ChatMessage
from assistant.policy import OFFLINE_FALLBACK
from assistant.providers.base import AssistantProvider


class OfflineProvider(AssistantProvider):
    provider_name = "offline"
    status_label = "Offline"

    def __init__(self, fallback_text: str = OFFLINE_FALLBACK) -> None:
        self.fallback_text = fallback_text

    def generate(
        self,
        question: str,
        context: str,
        history: Sequence[ChatMessage],
    ) -> str:
        del question, history
        guidance = context.strip()
        if not guidance:
            return self.fallback_text
        return f"Theo tài liệu hệ thống:\n{guidance}"
