from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: ChatRole
    content: str


@dataclass(frozen=True, slots=True)
class AssistantRequest:
    message: str
    history: tuple[ChatMessage, ...] = ()


@dataclass(frozen=True, slots=True)
class AssistantResponse:
    text: str
    source: str
    fallback_used: bool = False


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    source: str
    content: str
    score: int = 0


@dataclass(frozen=True, slots=True)
class TopicDecision:
    allowed: bool
    reason: str
