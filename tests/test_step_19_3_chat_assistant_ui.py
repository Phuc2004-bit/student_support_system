from __future__ import annotations

import ast
import inspect
import os
from pathlib import Path
import threading
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLabel, QTextBrowser

from app_context import AppContext
from assistant import AssistantResponse, ChatAssistantService, ChatRole
from assistant.policy import OFFLINE_FALLBACK, READ_ONLY_REFUSAL, SAFE_ERROR_RESPONSE
from config.settings import Settings
from models.dto import UserSession
from models.enums import UserRole
from services.permission_service import PermissionService
from ui.main_window import MainWindow
from ui.theme import APP_BACKGROUND, PRIMARY, SURFACE, chat_assistant_stylesheet
from ui.widgets.chat_assistant_widget import (
    QUICK_ACTIONS,
    SAFETY_NOTE,
    WELCOME_TEXT,
    AssistantRequestWorker,
    ChatAssistantDialog,
    ChatAssistantWidget,
    ChatInput,
    MessageBubble,
    source_label,
)


ROOT = Path(__file__).resolve().parent.parent


def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def context(role=UserRole.ADMIN) -> AppContext:
    return AppContext(
        db=object(),
        auth_service=object(),
        permission_service=PermissionService(),
        session=UserSession(1, "actor", "Người dùng", role),
    )


def wait_until_idle(widget: ChatAssistantWidget, timeout=2.0):
    deadline = time.monotonic() + timeout
    while widget.pending_count and time.monotonic() < deadline:
        app().processEvents()
        time.sleep(0.005)
    app().processEvents()
    assert widget.pending_count == 0


class RecordingService:
    def __init__(self, response=None):
        self.response = response or AssistantResponse(
            "Câu trả lời an toàn.", "faq:sample", False
        )
        self.requests = []

    def ask(self, request):
        self.requests.append(request)
        return self.response


class FailingService:
    def ask(self, request):
        raise RuntimeError("C:/private/raw/provider traceback")


def test_widget_constructs_complete_read_only_chat_layout():
    app()
    widget = ChatAssistantWidget(RecordingService())

    assert widget.objectName() == "chatAssistantWidget"
    assert widget.title_label.text() == "Trợ lý hệ thống"
    assert widget.subtitle_label.text() == "Hướng dẫn sử dụng • Chỉ đọc"
    assert widget.welcome_label.text() == WELCOME_TEXT
    assert widget.input_edit.placeholderText() == "Hỏi cách sử dụng hệ thống..."
    assert widget.send_button.text() == "Gửi"
    assert widget.safety_label.text() == SAFETY_NOTE
    assert [button.text() for button in widget.quick_action_buttons] == list(QUICK_ACTIONS)
    assert not widget.findChildren(QTextBrowser)


def test_message_bubbles_are_plain_text_and_role_aligned():
    app()
    widget = ChatAssistantWidget(RecordingService())
    user = widget._append_bubble(ChatRole.USER, "<b>Không render HTML</b>")
    assistant = widget._append_bubble(
        ChatRole.ASSISTANT, "Hướng dẫn", "faq:login_001"
    )

    assert user.content_label.textFormat() == Qt.TextFormat.PlainText
    assert user.content_label.text() == "<b>Không render HTML</b>"
    assert widget.message_rows[0].layout().itemAt(0).spacerItem() is not None
    assert widget.message_rows[1].layout().itemAt(0).widget() is assistant
    assert assistant.source_label.text() == "Nguồn: FAQ hệ thống"


def test_feature_flag_false_hides_entry_and_does_not_create_dialog():
    app()
    window = MainWindow(
        context(),
        chat_assistant_enabled=False,
        chat_assistant_service=RecordingService(),
    )
    assert window.topbar.assistant_button.isHidden()
    assert window.open_chat_assistant() is False
    assert window.chat_assistant_dialog is None
    window.close()


def test_feature_flag_true_opens_and_reuses_dialog_without_new_navigation_page():
    app()
    window = MainWindow(
        context(),
        chat_assistant_enabled=True,
        chat_assistant_service=RecordingService(),
    )
    original_pages = tuple(window.PAGE_TITLES)
    assert not window.topbar.assistant_button.isHidden()
    assert window.open_chat_assistant() is True
    dialog = window.chat_assistant_dialog
    assert dialog is not None and not dialog.isHidden()
    dialog.close()
    assert window.open_chat_assistant() is True
    assert window.chat_assistant_dialog is dialog
    assert tuple(window.PAGE_TITLES) == original_pages
    window.close()


def test_default_feature_flag_remains_disabled():
    assert Settings.CHAT_ASSISTANT_ENABLED is False


def test_allowed_faq_send_appends_user_and_assistant_bubbles():
    app()
    widget = ChatAssistantWidget(ChatAssistantService())
    received = []
    widget.response_received.connect(received.append)

    assert widget.send_text("Làm thế nào để đăng nhập?") is True
    assert not widget.send_button.isEnabled()
    wait_until_idle(widget)

    assert [bubble.role for bubble in widget.bubbles] == [
        ChatRole.USER, ChatRole.ASSISTANT
    ]
    assert "Tại màn hình Đăng nhập" in widget.bubbles[-1].content_label.text()
    assert widget.bubbles[-1].source_label.text() == "Nguồn: FAQ hệ thống"
    assert received[0].source == "faq:login_001"
    assert widget.send_button.isEnabled()


@pytest.mark.parametrize(
    "question",
    (
        "Sửa điểm em A thành 9",
        "Cho tôi mật khẩu admin",
        "Chạy SQL",
        "Đánh dấu intervention COMPLETED",
    ),
)
def test_forbidden_request_ui_displays_only_safe_service_response(question):
    app()
    widget = ChatAssistantWidget(ChatAssistantService())
    widget.send_text(question)
    wait_until_idle(widget)
    assert widget.bubbles[-1].content_label.text() == READ_ONLY_REFUSAL
    assert widget.bubbles[-1].source_label.text() == "Nguồn: Chính sách an toàn"
    assert not any("Thực hiện" in button.text() for button in widget.findChildren(type(widget.send_button)))


def test_no_match_displays_offline_fallback_and_friendly_source():
    app()
    widget = ChatAssistantWidget(ChatAssistantService())
    widget.send_text("support zxqv")
    wait_until_idle(widget)
    assert widget.bubbles[-1].content_label.text() == OFFLINE_FALLBACK
    assert widget.bubbles[-1].source_label.text() == "Nguồn: Trợ lý offline"


def test_quick_action_sends_question_only_through_service():
    app()
    service = RecordingService()
    widget = ChatAssistantWidget(service)
    widget.quick_action_buttons[0].click()
    wait_until_idle(widget)
    assert service.requests[0].message == QUICK_ACTIONS[0]
    assert widget.history[0].content == QUICK_ACTIONS[0]


def test_clear_conversation_clears_only_ui_and_memory():
    app()
    widget = ChatAssistantWidget(RecordingService())
    widget.send_text("Cách đăng nhập")
    wait_until_idle(widget)
    assert widget.history and widget.bubbles
    assert widget.clear_conversation() is True
    app().processEvents()
    assert widget.history == ()
    assert widget.bubbles == []
    assert widget.message_rows == []
    assert not widget.empty_state.isHidden()


def test_history_is_limited_in_memory_and_passed_without_current_message():
    app()
    service = RecordingService()
    widget = ChatAssistantWidget(service, history_limit=4)
    for index in range(4):
        widget.send_text(f"Điểm câu hỏi {index}")
        wait_until_idle(widget)

    assert len(widget.history) == 4
    assert [item.content for item in widget.history] == [
        "Điểm câu hỏi 2", "Câu trả lời an toàn.",
        "Điểm câu hỏi 3", "Câu trả lời an toàn.",
    ]
    assert service.requests[0].history == ()
    assert service.requests[-1].history[-1].content == "Câu trả lời an toàn."


@pytest.mark.parametrize(
    ("source", "label"),
    (
        ("faq:login_001", "FAQ hệ thống"),
        ("workflow:support_review", "Quy trình hệ thống"),
        ("offline:fallback", "Trợ lý offline"),
        ("policy", "Chính sách an toàn"),
        ("error", "Trợ lý hệ thống"),
    ),
)
def test_internal_sources_map_to_friendly_labels(source, label):
    assert source_label(source) == label
    assert source not in label


def test_worker_normalizes_unexpected_error_without_raw_detail():
    app()
    widget = ChatAssistantWidget(FailingService())
    widget.send_text("support workflow")
    wait_until_idle(widget)
    answer = widget.bubbles[-1].content_label.text()
    assert answer == SAFE_ERROR_RESPONSE
    assert "private" not in answer and "RuntimeError" not in answer
    assert widget.bubbles[-1].source_label.text() == "Nguồn: Trợ lý hệ thống"


def test_enter_sends_shift_enter_inserts_newline_and_empty_is_ignored():
    app()
    service = RecordingService()
    widget = ChatAssistantWidget(service)
    widget.input_edit.setPlainText("   ")
    assert widget.send_current_message() is False
    assert service.requests == []

    widget.input_edit.setPlainText("Dòng một")
    QTest.keyClick(widget.input_edit, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
    assert "\n" in widget.input_edit.toPlainText()
    widget.input_edit.setPlainText("Cách đăng nhập")
    QTest.keyClick(widget.input_edit, Qt.Key.Key_Return)
    wait_until_idle(widget)
    assert service.requests[-1].message == "Cách đăng nhập"


def test_worker_lifecycle_disables_controls_without_blocking_ui_thread():
    app()
    started = threading.Event()
    release = threading.Event()

    class BlockingService:
        def ask(self, request):
            started.set()
            release.wait(1)
            return AssistantResponse("Xong", "faq:sample")

    widget = ChatAssistantWidget(BlockingService())
    assert widget.send_text("Điểm được nhập thế nào?") is True
    assert started.wait(1)
    assert widget.pending_count == 1
    assert not widget.input_edit.isEnabled()
    release.set()
    wait_until_idle(widget)
    assert widget.input_edit.isEnabled()
    assert widget.bubbles[-1].content_label.text() == "Xong"


def test_worker_source_calls_only_assistant_service_ask():
    source = inspect.getsource(AssistantRequestWorker)
    assert ".ask(" in source
    for forbidden in ("repository", "cursor", "execute(", "commit(", "ScoreService", "SupportService"):
        assert forbidden not in source


@pytest.mark.parametrize(
    ("width", "height"),
    ((1280, 720), (1366, 768), (1920, 1080), (1093, 614)),
)
def test_responsive_dialog_size_fits_common_and_125_percent_views(width, height):
    recommended = ChatAssistantDialog.recommended_size(width, height)
    assert 360 <= recommended[0] <= width
    assert 480 <= recommended[1] <= height
    assert recommended[0] <= 460 and recommended[1] <= 680


def test_chat_theme_uses_central_tokens_and_controls_have_accessible_labels():
    app()
    widget = ChatAssistantWidget(RecordingService())
    style = chat_assistant_stylesheet()
    assert APP_BACKGROUND in style and SURFACE in style and PRIMARY in style
    assert widget.send_button.text() and widget.send_button.toolTip()
    assert widget.close_button.text() and widget.close_button.toolTip()
    assert widget.status_label.text() == "Offline"


def test_chat_ui_has_no_database_repository_or_business_service_imports():
    path = ROOT / "ui" / "widgets" / "chat_assistant_widget.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = (
        "repositories", "database", "services.score_service",
        "services.support_service", "services.student_service",
        "services.user_service", "services.report_service",
    )
    assert not {
        name for name in imported
        if any(name == prefix or name.startswith(prefix + ".") for prefix in forbidden)
    }
    source = path.read_text(encoding="utf-8").lower()
    assert "select " not in source and "insert " not in source


def test_chat_ui_is_provider_neutral_and_has_no_chat_database_wiring():
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "ui" / "widgets" / "chat_assistant_widget.py",
            ROOT / "ui" / "main_window.py",
            ROOT / "bootstrap.py",
        )
    )
    assert "GeminiProvider" not in sources
    assert "google.genai" not in sources
    assert "API_KEY" not in sources
    assert "ChatAssistantService" not in (ROOT / "bootstrap.py").read_text(encoding="utf-8")
