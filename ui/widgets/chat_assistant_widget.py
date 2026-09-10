from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from assistant import (
    AssistantRequest,
    AssistantResponse,
    ChatAssistantService,
    ChatMessage,
    ChatRole,
)
from assistant.policy import SAFE_ERROR_RESPONSE
from ui.theme import chat_assistant_stylesheet


WELCOME_TEXT = (
    "Xin chào! Tôi có thể hướng dẫn bạn sử dụng Student Support System."
)
SAFETY_NOTE = "Trợ lý chỉ hướng dẫn sử dụng và không thay đổi dữ liệu."
QUICK_ACTIONS = (
    "Làm sao nhập điểm?",
    "Các trạng thái bổ trợ có ý nghĩa gì?",
    "Làm sao đổi mật khẩu?",
    "Vì sao tôi không thấy dữ liệu?",
)


def source_label(source: str) -> str:
    """Map an internal source identifier to a stable user-facing label."""
    if source.startswith("faq:"):
        return "FAQ hệ thống"
    if source.startswith("workflow:"):
        return "Quy trình hệ thống"
    if source.startswith("offline:") or source == "offline":
        return "Trợ lý offline"
    if source == "policy":
        return "Chính sách an toàn"
    if source == "error":
        return "Trợ lý hệ thống"
    return "Hướng dẫn hệ thống"


class ChatInput(QPlainTextEdit):
    """Multiline input where Enter sends and Shift+Enter inserts a line break."""

    send_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if (
            event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter)
            and not event.modifiers() & Qt.KeyboardModifier.ShiftModifier
        ):
            self.send_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class MessageBubble(QFrame):
    """Plain-text chat bubble; it never renders HTML or Markdown."""

    def __init__(
        self,
        role: ChatRole,
        content: str,
        source: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        if role not in (ChatRole.USER, ChatRole.ASSISTANT):
            raise ValueError("Vai trò tin nhắn không hợp lệ.")

        self.role = role
        self.source = source
        self.setObjectName(
            "chatUserBubble" if role is ChatRole.USER else "chatAssistantBubble"
        )
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        self.setMaximumWidth(390)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 9, 12, 9)
        layout.setSpacing(5)

        self.content_label = QLabel(content, self)
        self.content_label.setObjectName("chatMessageText")
        self.content_label.setTextFormat(Qt.TextFormat.PlainText)
        self.content_label.setWordWrap(True)
        self.content_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.content_label)

        self.source_label = QLabel(self)
        self.source_label.setObjectName("chatSourceLabel")
        self.source_label.setTextFormat(Qt.TextFormat.PlainText)
        if role is ChatRole.ASSISTANT and source:
            self.source_label.setText(f"Nguồn: {source_label(source)}")
            layout.addWidget(self.source_label)
        else:
            self.source_label.hide()


class _AssistantWorkerSignals(QObject):
    finished = Signal(object, int, object)


class AssistantRequestWorker(QRunnable):
    """Background unit that calls only the assistant service boundary."""

    def __init__(
        self,
        service: ChatAssistantService,
        request: AssistantRequest,
        generation: int,
    ) -> None:
        super().__init__()
        self.service = service
        self.request = request
        self.generation = generation
        self.signals = _AssistantWorkerSignals()

    def run(self) -> None:
        try:
            response = self.service.ask(self.request)
            if not isinstance(response, AssistantResponse):
                raise TypeError("Assistant service returned an invalid response.")
        except Exception:
            response = AssistantResponse(
                text=SAFE_ERROR_RESPONSE,
                source="error",
                fallback_used=True,
            )
        self.signals.finished.emit(response, self.generation, self)


class ChatAssistantWidget(QWidget):
    """Read-only assistant presentation backed only by ChatAssistantService.ask."""

    response_received = Signal(object)
    DEFAULT_HISTORY_LIMIT = ChatAssistantService.DEFAULT_HISTORY_LIMIT

    def __init__(
        self,
        service: ChatAssistantService,
        parent: QWidget | None = None,
        thread_pool: QThreadPool | None = None,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
    ) -> None:
        super().__init__(parent)
        if service is None or not callable(getattr(service, "ask", None)):
            raise ValueError("ChatAssistantService không hợp lệ.")
        if isinstance(history_limit, bool) or not isinstance(history_limit, int) or history_limit <= 0:
            raise ValueError("history_limit phải là số nguyên dương.")

        self.service = service
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self.history_limit = history_limit
        self._history: list[ChatMessage] = []
        self._workers: set[AssistantRequestWorker] = set()
        self._generation = 0
        self.bubbles: list[MessageBubble] = []
        self.message_rows: list[QWidget] = []

        self.setObjectName("chatAssistantWidget")
        self._build_ui()
        self.setStyleSheet(chat_assistant_stylesheet())
        self._connect_signals()

    @property
    def history(self) -> tuple[ChatMessage, ...]:
        return tuple(self._history)

    @property
    def pending_count(self) -> int:
        return len(self._workers)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QFrame(self)
        header.setObjectName("chatHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 12, 12)
        header_layout.setSpacing(10)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)
        self.title_label = QLabel("Trợ lý hệ thống", header)
        self.title_label.setObjectName("chatTitleLabel")
        self.subtitle_label = QLabel("Hướng dẫn sử dụng • Chỉ đọc", header)
        self.subtitle_label.setObjectName("chatSubtitleLabel")
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.subtitle_label)

        self.status_label = QLabel(
            str(getattr(self.service, "provider_status_label", "Offline")), header
        )
        self.status_label.setObjectName("chatOfflineBadge")
        self.close_button = QPushButton("Đóng", header)
        self.close_button.setObjectName("chatCloseButton")
        self.close_button.setToolTip("Đóng cửa sổ trợ lý")
        header_layout.addLayout(title_layout, 1)
        header_layout.addWidget(self.status_label)
        header_layout.addWidget(self.close_button)
        root.addWidget(header)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setObjectName("chatScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.message_container = QWidget(self.scroll_area)
        self.message_container.setObjectName("chatMessageContainer")
        self.messages_layout = QVBoxLayout(self.message_container)
        self.messages_layout.setContentsMargins(14, 14, 14, 14)
        self.messages_layout.setSpacing(10)

        self.empty_state = QWidget(self.message_container)
        self.empty_state.setObjectName("chatEmptyState")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(8, 18, 8, 18)
        empty_layout.setSpacing(9)
        self.welcome_label = QLabel(WELCOME_TEXT, self.empty_state)
        self.welcome_label.setObjectName("chatWelcomeLabel")
        self.welcome_label.setWordWrap(True)
        self.quick_action_buttons: list[QPushButton] = []
        empty_layout.addWidget(self.welcome_label)
        for text in QUICK_ACTIONS:
            button = QPushButton(text, self.empty_state)
            button.setProperty("quickAction", True)
            button.setToolTip(f"Gửi câu hỏi: {text}")
            self.quick_action_buttons.append(button)
            empty_layout.addWidget(button)
        self.messages_layout.addWidget(self.empty_state)
        self.messages_layout.addStretch(1)
        self.scroll_area.setWidget(self.message_container)
        root.addWidget(self.scroll_area, 1)

        composer = QFrame(self)
        composer.setObjectName("chatComposer")
        composer_layout = QVBoxLayout(composer)
        composer_layout.setContentsMargins(14, 12, 14, 12)
        composer_layout.setSpacing(8)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(8)
        self.input_edit = ChatInput(composer)
        self.input_edit.setObjectName("chatInput")
        self.input_edit.setPlaceholderText("Hỏi cách sử dụng hệ thống...")
        self.input_edit.setMaximumHeight(82)
        self.input_edit.setMinimumHeight(48)
        self.send_button = QPushButton("Gửi", composer)
        self.send_button.setObjectName("chatSendButton")
        self.send_button.setProperty("variant", "primary")
        self.send_button.setToolTip("Gửi câu hỏi cho trợ lý")
        input_layout.addWidget(self.input_edit, 1)
        input_layout.addWidget(self.send_button)

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        self.safety_label = QLabel(SAFETY_NOTE, composer)
        self.safety_label.setObjectName("chatSafetyLabel")
        self.safety_label.setWordWrap(True)
        self.clear_button = QPushButton("Xóa cuộc trò chuyện", composer)
        self.clear_button.setObjectName("chatClearButton")
        self.clear_button.setToolTip("Xóa lịch sử chat trong phiên hiện tại")
        footer_layout.addWidget(self.safety_label, 1)
        footer_layout.addWidget(self.clear_button)
        composer_layout.addLayout(input_layout)
        composer_layout.addLayout(footer_layout)
        root.addWidget(composer)

        QWidget.setTabOrder(self.input_edit, self.send_button)
        QWidget.setTabOrder(self.send_button, self.clear_button)
        QWidget.setTabOrder(self.clear_button, self.close_button)

    def _connect_signals(self) -> None:
        self.send_button.clicked.connect(self.send_current_message)
        self.input_edit.send_requested.connect(self.send_current_message)
        self.clear_button.clicked.connect(self.clear_conversation)
        for button in self.quick_action_buttons:
            button.clicked.connect(
                lambda checked=False, text=button.text(): self.send_text(text)
            )

    def send_current_message(self) -> bool:
        return self.send_text(self.input_edit.toPlainText())

    def send_text(self, text: str) -> bool:
        if self.pending_count or not isinstance(text, str):
            return False
        question = text.strip()
        if not question:
            return False

        previous_history = tuple(self._history)
        self.input_edit.clear()
        self.empty_state.hide()
        self._append_bubble(ChatRole.USER, question)
        self._append_history(ChatMessage(ChatRole.USER, question))
        self._set_busy(True)

        worker = AssistantRequestWorker(
            self.service,
            AssistantRequest(question, previous_history),
            self._generation,
        )
        worker.signals.finished.connect(self._on_worker_finished)
        self._workers.add(worker)
        self.thread_pool.start(worker)
        return True

    def _on_worker_finished(
        self,
        response: AssistantResponse,
        generation: int,
        worker: AssistantRequestWorker,
    ) -> None:
        self._workers.discard(worker)
        if generation == self._generation:
            if (
                getattr(self.service, "provider_name", "offline") == "gemini"
                and response.fallback_used
            ):
                self.status_label.setText("Đang dùng chế độ offline")
            else:
                self.status_label.setText(
                    str(getattr(self.service, "provider_status_label", "Offline"))
                )
            self._append_bubble(ChatRole.ASSISTANT, response.text, response.source)
            self._append_history(ChatMessage(ChatRole.ASSISTANT, response.text))
            self.response_received.emit(response)
        self._set_busy(bool(self._workers))

    def _append_history(self, message: ChatMessage) -> None:
        self._history.append(message)
        if len(self._history) > self.history_limit:
            del self._history[:-self.history_limit]

    def _append_bubble(
        self,
        role: ChatRole,
        content: str,
        source: str | None = None,
    ) -> MessageBubble:
        row_widget = QWidget(self.message_container)
        row_widget.setObjectName("chatMessageRow")
        row = QHBoxLayout(row_widget)
        row.setContentsMargins(0, 0, 0, 0)
        bubble = MessageBubble(role, content, source, row_widget)
        if role is ChatRole.USER:
            row.addStretch(1)
            row.addWidget(bubble)
        else:
            row.addWidget(bubble)
            row.addStretch(1)
        self.messages_layout.insertWidget(
            self.messages_layout.count() - 1,
            row_widget,
        )
        self.bubbles.append(bubble)
        self.message_rows.append(row_widget)
        self._scroll_to_bottom()
        return bubble

    def clear_conversation(self) -> bool:
        if self.pending_count:
            return False
        self._generation += 1
        self._history.clear()
        for row in self.message_rows:
            row.deleteLater()
        self.bubbles.clear()
        self.message_rows.clear()
        self.empty_state.show()
        self.input_edit.clear()
        self.input_edit.setFocus(Qt.FocusReason.OtherFocusReason)
        self._scroll_to_bottom()
        return True

    def focus_input(self) -> None:
        QTimer.singleShot(
            0,
            lambda: self.input_edit.setFocus(Qt.FocusReason.OtherFocusReason),
        )

    def _set_busy(self, busy: bool) -> None:
        self.input_edit.setEnabled(not busy)
        self.send_button.setEnabled(not busy)
        self.clear_button.setEnabled(not busy)
        for button in self.quick_action_buttons:
            button.setEnabled(not busy)
        if not busy:
            self.focus_input()

    def _scroll_to_bottom(self) -> None:
        QTimer.singleShot(
            0,
            lambda: self.scroll_area.verticalScrollBar().setValue(
                self.scroll_area.verticalScrollBar().maximum()
            ),
        )


class ChatAssistantDialog(QDialog):
    """Responsive, non-modal shell for the assistant widget."""

    def __init__(
        self,
        service: ChatAssistantService,
        parent: QWidget | None = None,
        thread_pool: QThreadPool | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("chatAssistantDialog")
        self.setWindowTitle("Trợ lý hệ thống")
        self.setModal(False)
        self.setMinimumSize(360, 480)
        self.resize(440, 620)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.chat_widget = ChatAssistantWidget(
            service,
            self,
            thread_pool=thread_pool,
        )
        layout.addWidget(self.chat_widget)
        self.chat_widget.close_button.clicked.connect(self.close)

    def open_for_user(self) -> None:
        self._fit_available_screen()
        self.show()
        self.raise_()
        self.activateWindow()
        self.chat_widget.focus_input()

    def _fit_available_screen(self) -> None:
        screen = self.screen()
        if screen is None:
            return
        available = screen.availableGeometry()
        width, height = self.recommended_size(available.width(), available.height())
        self.resize(width, height)

    @staticmethod
    def recommended_size(available_width: int, available_height: int) -> tuple[int, int]:
        width = min(460, max(360, int(available_width * 0.36)))
        height = min(680, max(480, int(available_height * 0.78)))
        return min(width, available_width), min(height, available_height)


ChatWidget = ChatAssistantWidget
