from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from assistant.models import ChatMessage


class AssistantProvider(ABC):
    provider_name = "unknown"
    status_label = "Offline"

    @abstractmethod
    def generate(
        self,
        question: str,
        context: str,
        history: Sequence[ChatMessage],
    ) -> str:
        """Generate an answer using only the supplied static context."""
