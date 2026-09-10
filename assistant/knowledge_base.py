from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata

from assistant.exceptions import KnowledgeBaseError
from assistant.models import KnowledgeChunk
from config.paths import resource_path


STRUCTURED_KNOWLEDGE_FILES = (
    "assistant/knowledge/faq_vi.json",
    "assistant/knowledge/workflows_vi.json",
)
APPROVED_DOCUMENT_FILES = (
    "HUONG_DAN.txt",
    "RELEASE_NOTES_V1.2.0.md",
    "installer/PREREQUISITES_V1.2.txt",
)
DEFAULT_KNOWLEDGE_FILES = STRUCTURED_KNOWLEDGE_FILES + APPROVED_DOCUMENT_FILES

REQUIRED_FIELDS = frozenset(
    {"id", "category", "question", "aliases", "answer", "keywords", "screen"}
)
ALLOWED_CATEGORIES = frozenset(
    {
        "login", "dashboard", "students", "scores", "support", "reports",
        "catalogs", "system", "profile", "password", "excel", "installation",
        "prerequisites", "admin_bootstrap", "admin_reset", "permissions",
        "troubleshooting", "support_status", "support_review",
        "support_detection", "safety",
    }
)
AMBIGUOUS_RESPONSE = (
    "Câu hỏi có thể liên quan đến nhiều nội dung. Bạn vui lòng nói rõ hơn, "
    "ví dụ bạn muốn hỏi về nhập điểm trực tiếp hay nhập điểm từ Excel."
)

_STOP_WORDS = {
    "bi", "cua", "co", "duoc", "gi", "he", "la", "lam", "mot", "nao",
    "nhu", "o", "the", "thi", "toi", "trong", "tu", "va", "voi",
}
_MIN_CONFIDENCE = 20
_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)\bpassword\s*="),
    re.compile(r"(?i)\bpwd\s*="),
    re.compile(r"(?i)\bdb_password\b"),
    re.compile(r"(?i)\bapi[_-]?key\b"),
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~-]+"),
    re.compile(r"\$2[aby]\$\d{2}\$[./A-Za-z0-9]{53}"),
    re.compile(r"(?i)\bdriver\s*=.+\bserver\s*=.+\bdatabase\s*="),
)


def normalize_vietnamese(value: str) -> str:
    """Normalize Vietnamese text for matching without changing stored answers."""
    decomposed = unicodedata.normalize("NFD", value.casefold())
    unaccented = "".join(
        character for character in decomposed
        if not unicodedata.combining(character)
    ).replace("đ", "d")
    without_punctuation = re.sub(r"[^a-z0-9]+", " ", unaccented)
    return " ".join(without_punctuation.split())


@dataclass(frozen=True, slots=True)
class _Entry:
    entry_id: str
    category: str
    question: str
    aliases: tuple[str, ...]
    answer: str
    keywords: tuple[str, ...]
    screen: str
    source: str


class KnowledgeBase:
    """Search only an explicit allowlist of static application guidance."""

    def __init__(
        self,
        documents: Mapping[str, str] | None = None,
        structured_files: Sequence[str | Path] | None = None,
    ) -> None:
        if documents is not None and structured_files is not None:
            raise KnowledgeBaseError("Chỉ được chọn một nguồn knowledge khi khởi tạo.")

        self.fallback_source = "offline" if documents is not None else "offline:fallback"
        self._entries: tuple[_Entry, ...] = ()
        if documents is not None:
            self._documents = dict(documents)
        else:
            files = structured_files or tuple(
                resource_path(*Path(name).parts) for name in STRUCTURED_KNOWLEDGE_FILES
            )
            self._entries = self._load_entries(tuple(Path(path) for path in files))
            self._documents = self._load_approved_documents()
        self._chunks = self._build_chunks(self._documents)

    @property
    def entry_count(self) -> int:
        return len(self._entries)

    @property
    def categories(self) -> frozenset[str]:
        return frozenset(entry.category for entry in self._entries)

    def search(self, question: str, limit: int = 3) -> list[KnowledgeChunk]:
        if not isinstance(question, str) or not question.strip() or limit <= 0:
            return []
        normalized_query = normalize_vietnamese(question)
        if not normalized_query:
            return []

        if self._entries:
            return self._search_entries(normalized_query, limit)
        return self._search_legacy_documents(normalized_query, limit)

    def _search_entries(self, query: str, limit: int) -> list[KnowledgeChunk]:
        ranked: list[tuple[int, str, _Entry]] = []
        for entry in self._entries:
            score = self._score_entry(query, entry)
            if score >= _MIN_CONFIDENCE:
                ranked.append((score, entry.source, entry))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        if not ranked:
            return []

        top_score = ranked[0][0]
        near_tied = [item for item in ranked if top_score - item[0] <= 10]
        if len(near_tied) > 1 and len({item[2].entry_id for item in near_tied}) > 1:
            return [KnowledgeChunk("offline:clarify", AMBIGUOUS_RESPONSE, top_score)]

        score, _, entry = ranked[0]
        return [KnowledgeChunk(source=entry.source, content=entry.answer, score=score)]

    @classmethod
    def _score_entry(cls, query: str, entry: _Entry) -> int:
        question = normalize_vietnamese(entry.question)
        aliases = tuple(normalize_vietnamese(alias) for alias in entry.aliases)
        if query == question:
            return 1000
        if query in aliases:
            return 900

        query_terms = cls._terms(query)
        keyword_terms = {normalize_vietnamese(keyword) for keyword in entry.keywords}
        keyword_score = 100 * len(query_terms.intersection(keyword_terms))
        searchable = " ".join((question, *aliases))
        phrase_score = 60 if len(query) >= 5 and query in searchable else 0
        token_score = 10 * len(query_terms.intersection(cls._terms(searchable)))
        return keyword_score + phrase_score + token_score

    def _search_legacy_documents(self, query: str, limit: int) -> list[KnowledgeChunk]:
        query_terms = self._terms(query)
        if not query_terms:
            return []
        matches: list[tuple[int, str, int, str]] = []
        for source, index, content in self._chunks:
            score = len(query_terms.intersection(self._terms(content)))
            if score:
                matches.append((score, source, index, content))
        matches.sort(key=lambda item: (-item[0], item[1].casefold(), item[2]))
        return [
            KnowledgeChunk(source=source, content=content, score=score)
            for score, source, _, content in matches[:limit]
        ]

    @classmethod
    def _load_entries(cls, paths: tuple[Path, ...]) -> tuple[_Entry, ...]:
        entries: list[_Entry] = []
        seen_ids: set[str] = set()
        seen_aliases: dict[str, str] = {}
        try:
            for path in paths:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
                    raise KnowledgeBaseError("Knowledge JSON phải chứa danh sách entries.")
                source_prefix = payload.get("source_prefix")
                if source_prefix not in {"faq", "workflow"}:
                    raise KnowledgeBaseError("Knowledge JSON có source_prefix không hợp lệ.")
                for raw in payload["entries"]:
                    entry = cls._validate_entry(raw, source_prefix)
                    if entry.entry_id in seen_ids:
                        raise KnowledgeBaseError(f"Knowledge ID bị trùng: {entry.entry_id}")
                    seen_ids.add(entry.entry_id)
                    for alias in entry.aliases:
                        normalized = normalize_vietnamese(alias)
                        owner = seen_aliases.get(normalized)
                        if owner is not None and owner != entry.entry_id:
                            raise KnowledgeBaseError(f"Knowledge alias bị trùng: {alias}")
                        seen_aliases[normalized] = entry.entry_id
                    entries.append(entry)
        except KnowledgeBaseError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise KnowledgeBaseError("Không thể đọc knowledge JSON hợp lệ bằng UTF-8.") from exc
        return tuple(entries)

    @classmethod
    def _validate_entry(cls, raw: object, prefix: str) -> _Entry:
        if not isinstance(raw, dict) or not REQUIRED_FIELDS.issubset(raw):
            raise KnowledgeBaseError("Knowledge entry thiếu trường bắt buộc.")
        scalar_fields = ("id", "category", "question", "answer", "screen")
        if any(not isinstance(raw[field], str) or not raw[field].strip() for field in scalar_fields):
            raise KnowledgeBaseError("Knowledge entry có trường văn bản rỗng hoặc không hợp lệ.")
        if raw["category"] not in ALLOWED_CATEGORIES:
            raise KnowledgeBaseError(f"Knowledge category không hợp lệ: {raw['category']}")
        for field in ("aliases", "keywords"):
            value = raw[field]
            if not isinstance(value, list) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                raise KnowledgeBaseError(f"Knowledge field {field} không hợp lệ.")
        searchable_text = " ".join(
            [raw[field] for field in scalar_fields]
            + list(raw["aliases"])
            + list(raw["keywords"])
        )
        if any(pattern.search(searchable_text) for pattern in _SENSITIVE_PATTERNS):
            raise KnowledgeBaseError("Knowledge chứa mẫu dữ liệu nhạy cảm bị cấm.")
        return _Entry(
            entry_id=raw["id"].strip(),
            category=raw["category"],
            question=raw["question"].strip(),
            aliases=tuple(item.strip() for item in raw["aliases"]),
            answer=raw["answer"].strip(),
            keywords=tuple(item.strip() for item in raw["keywords"]),
            screen=raw["screen"].strip(),
            source=f"{prefix}:{raw['id'].strip()}",
        )

    @staticmethod
    def _load_approved_documents() -> dict[str, str]:
        documents: dict[str, str] = {}
        try:
            for relative_name in APPROVED_DOCUMENT_FILES:
                path = resource_path(*Path(relative_name).parts)
                if path.is_file():
                    documents[relative_name] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise KnowledgeBaseError("Không thể đọc tài liệu hướng dẫn của hệ thống.") from exc
        return documents

    @staticmethod
    def _build_chunks(documents: Mapping[str, str]) -> tuple[tuple[str, int, str], ...]:
        chunks: list[tuple[str, int, str]] = []
        for source in sorted(documents, key=str.casefold):
            content = documents[source]
            if not isinstance(content, str):
                raise KnowledgeBaseError("Nội dung tài liệu hướng dẫn không hợp lệ.")
            paragraphs = re.split(r"(?:\r?\n){2,}", content)
            for index, paragraph in enumerate(paragraphs):
                normalized = " ".join(paragraph.split())
                if normalized:
                    chunks.append((source, index, normalized))
        return tuple(chunks)

    @staticmethod
    def _terms(value: str) -> set[str]:
        return {
            term for term in normalize_vietnamese(value).split()
            if len(term) > 1 and term not in _STOP_WORDS
        }
