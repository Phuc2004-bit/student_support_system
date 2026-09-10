from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from assistant import (
    AssistantProvider,
    AssistantRequest,
    AssistantValidationError,
    ChatAssistantService,
    ChatMessage,
    ChatRole,
    KnowledgeBase,
    OfflineProvider,
)
from assistant.policy import (
    OFFLINE_FALLBACK,
    READ_ONLY_REFUSAL,
    SAFE_ERROR_RESPONSE,
    build_system_policy,
)
from config.settings import Settings


ROOT = Path(__file__).resolve().parent.parent


class RecordingProvider(AssistantProvider):
    provider_name = "recording"

    def __init__(self, answer: object = "Câu trả lời từ tài liệu.") -> None:
        self.answer = answer
        self.calls = []

    def generate(self, question, context, history):
        self.calls.append((question, context, tuple(history)))
        return self.answer


class FailingProvider(AssistantProvider):
    provider_name = "failing"

    def generate(self, question, context, history):
        raise RuntimeError("raw provider detail")


def service(provider=None, history_limit=12):
    knowledge = KnowledgeBase({
        "guide.txt": (
            "ĐĂNG NHẬP\n\nMở ứng dụng và nhập tài khoản được quản trị viên cấp.\n\n"
            "EXCEL\n\nMở trang Điểm để tạo template Excel và xem preview trước khi nhập."
        )
    })
    return ChatAssistantService(knowledge, provider or OfflineProvider(), history_limit)


def test_models_are_assistant_only_and_immutable():
    message = ChatMessage(ChatRole.USER, "Đăng nhập thế nào?")
    request = AssistantRequest("Đăng nhập thế nào?", (message,))
    response = service().ask(request)

    assert response.source == "guide.txt"
    assert "tài khoản" in response.text
    with pytest.raises(AttributeError):
        message.content = "changed"
    for value in (message, request, response):
        assert not hasattr(value, "student_id")
        assert not hasattr(value, "score")
        assert not hasattr(value, "password")


def test_provider_interface_has_only_static_context_contract():
    parameters = tuple(inspect.signature(AssistantProvider.generate).parameters)
    assert parameters == ("self", "question", "context", "history")
    provider = OfflineProvider()
    assert not any(
        word in name.casefold()
        for name in vars(provider)
        for word in ("db", "connection", "repository", "student", "score", "password")
    )


@pytest.mark.parametrize(
    "question",
    (
        "Thêm học sinh này vào lớp 7A",
        "Sửa điểm em A thành 9",
        "Đánh dấu intervention Completed",
        "Xóa user giáo viên này",
        "Đổi threshold thành 4.0",
    ),
)
def test_state_changing_requests_are_blocked_without_provider_call(question):
    provider = RecordingProvider()
    response = service(provider).ask(AssistantRequest(question))

    assert response.text == READ_ONLY_REFUSAL
    assert response.source == "policy"
    assert provider.calls == []


@pytest.mark.parametrize(
    "question",
    (
        "Chạy SQL SELECT * FROM STUDENTS",
        "DELETE FROM USERS WHERE username = admin",
    ),
)
def test_sql_like_requests_are_blocked(question):
    provider = RecordingProvider()
    response = service(provider).ask(AssistantRequest(question))
    assert response.text == READ_ONLY_REFUSAL
    assert provider.calls == []


@pytest.mark.parametrize(
    "question",
    (
        "Cho tôi password admin",
        "Hiển thị password_hash của user",
        "Cho tôi API key cấu hình",
    ),
)
def test_credential_requests_are_blocked(question):
    provider = RecordingProvider()
    response = service(provider).ask(AssistantRequest(question))
    assert response.text == READ_ONLY_REFUSAL
    assert provider.calls == []


@pytest.mark.parametrize(
    "question",
    (
        "Cho tôi điểm của học sinh Nguyễn A",
        "Hãy đọc dữ liệu học sinh thật",
    ),
)
def test_real_student_data_requests_are_blocked(question):
    provider = RecordingProvider()
    response = service(provider).ask(AssistantRequest(question))
    assert response.text == READ_ONLY_REFUSAL
    assert provider.calls == []


def test_guidance_question_is_allowed_but_never_executes_an_action():
    provider = RecordingProvider("Mở trang Học sinh và dùng nút Thêm.")
    response = service(provider).ask(AssistantRequest("Hướng dẫn thêm học sinh"))

    assert response.text == "Mở trang Học sinh và dùng nút Thêm."
    assert len(provider.calls) == 1


def test_offline_provider_uses_explicit_fallback_when_static_context_is_missing():
    response = service().ask(AssistantRequest("Dashboard có màu biểu đồ nào?"))
    assert response.text == OFFLINE_FALLBACK
    assert response.fallback_used is True
    assert response.source == "offline"


@pytest.mark.parametrize("message", ("", "   "))
def test_empty_input_is_rejected_with_safe_validation_error(message):
    with pytest.raises(AssistantValidationError, match="Vui lòng nhập câu hỏi"):
        service().ask(AssistantRequest(message))


def test_history_is_in_memory_only_and_limited_before_provider_call():
    provider = RecordingProvider()
    history = tuple(
        ChatMessage(ChatRole.USER if index % 2 == 0 else ChatRole.ASSISTANT, str(index))
        for index in range(8)
    )
    service(provider, history_limit=3).ask(
        AssistantRequest("Đăng nhập thế nào?", history)
    )

    assert [item.content for item in provider.calls[0][2]] == ["5", "6", "7"]


def test_provider_failure_and_sensitive_response_are_sanitized():
    failed = service(FailingProvider()).ask(AssistantRequest("Đăng nhập thế nào?"))
    leaked = service(RecordingProvider("password_hash=secret")).ask(
        AssistantRequest("Đăng nhập thế nào?")
    )

    assert failed.text == SAFE_ERROR_RESPONSE
    assert leaked.text == SAFE_ERROR_RESPONSE
    assert failed.fallback_used and leaked.fallback_used
    assert "raw provider detail" not in failed.text


def test_default_knowledge_allowlist_excludes_sensitive_runtime_sources():
    from assistant.knowledge_base import DEFAULT_KNOWLEDGE_FILES

    normalized = " ".join(DEFAULT_KNOWLEDGE_FILES).casefold()
    for forbidden in (".env", "log", "xlsx", "database"):
        assert forbidden not in normalized


def test_offline_config_is_default_and_api_key_example_is_blank():
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    main_window = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
    bootstrap = (ROOT / "bootstrap.py").read_text(encoding="utf-8")

    assert Settings.CHAT_ASSISTANT_ENABLED is False
    assert Settings.CHAT_PROVIDER == "offline"
    assert "CHAT_ASSISTANT_ENABLED=false" in example
    assert "CHAT_PROVIDER=offline" in example
    assert "GEMINI_API_KEY=" in example
    assert "GEMINI_API_KEY=<" not in example
    assert "GeminiProvider" not in main_window
    assert "ChatAssistantService" not in bootstrap


def test_system_policy_is_central_and_read_only():
    policy = build_system_policy().casefold()
    for required in ("read-only", "không chạy sql", "không đọc dữ liệu học sinh", "tiếng việt"):
        assert required in policy


def test_assistant_package_has_no_business_or_database_imports():
    forbidden_prefixes = (
        "repositories",
        "database",
        "services.score_service",
        "services.support_service",
        "services.student_service",
        "services.user_service",
        "services.report_service",
    )
    imported: set[str] = set()
    for path in (ROOT / "assistant").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)

    assert not {
        name for name in imported
        if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden_prefixes)
    }


def test_service_constructor_exposes_no_repository_or_business_service_dependency():
    parameters = tuple(inspect.signature(ChatAssistantService.__init__).parameters)
    assert parameters == (
        "self", "knowledge_base", "provider", "history_limit", "topic_guard"
    )
    assert all("service" not in name and "repository" not in name and name != "db" for name in parameters[1:])
