from __future__ import annotations

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.dto import UserSession
from models.enums import UserRole


class Topbar(QFrame):
    """
    Thanh trên cùng của ứng dụng.

    Bước 7.5:
    - hiển thị tên người dùng;
    - hiển thị vai trò người dùng;
    - toàn bộ dữ liệu lấy từ UserSession;
    - không truy vấn DB và không gọi service.
    """

    logout_requested = Signal()

    HEIGHT = 72

    ROLE_LABELS = {
        UserRole.ADMIN: "Quản trị viên",
        UserRole.TEACHER: "Giáo viên",
    }

    def __init__(
        self,
        session: UserSession,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        if session is None:
            raise ValueError(
                "UserSession không được để trống."
            )

        self.session = session

        self.setObjectName("topbar")
        self.setFixedHeight(self.HEIGHT)

        self._build_ui()

    @property
    def role_text(self) -> str:
        return self.ROLE_LABELS.get(
            self.session.role,
            str(self.session.role),
        )

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(
            24,
            0,
            24,
            0,
        )
        layout.setSpacing(16)

        title_container = QWidget(self)
        title_container.setObjectName("topbarTitleContainer")
        title_layout = QVBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        self.app_title_label = QLabel(
            "Quản lý học sinh cần bổ trợ",
            title_container,
        )
        self.app_title_label.setObjectName(
            "appTitleLabel"
        )

        self.subtitle_label = QLabel(
            "Không gian quản lý tập trung",
            title_container,
        )
        self.subtitle_label.setObjectName("topbarSubtitleLabel")
        title_layout.addWidget(self.app_title_label)
        title_layout.addWidget(self.subtitle_label)

        user_container = QWidget(self)
        user_container.setObjectName(
            "userInfoContainer"
        )

        user_layout = QVBoxLayout(
            user_container
        )
        user_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        user_layout.setSpacing(2)

        self.user_label = QLabel(
            self.session.full_name,
            user_container,
        )
        self.user_label.setObjectName(
            "userLabel"
        )
        self.user_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        self.role_label = QLabel(
            self.role_text,
            user_container,
        )
        self.role_label.setObjectName(
            "roleLabel"
        )
        self.role_label.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        user_layout.addWidget(
            self.user_label
        )
        user_layout.addWidget(
            self.role_label
        )

        self.logout_button = QPushButton(
            "Đăng xuất",
            self,
        )
        self.logout_button.setObjectName(
            "logoutButton"
        )
        self.logout_button.setProperty("variant", "secondary")
        self.logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_button.clicked.connect(
            self.logout_requested.emit
        )

        layout.addWidget(title_container)
        layout.addStretch(1)
        layout.addWidget(
            user_container
        )
        layout.addWidget(
            self.logout_button
        )

    def set_page_title(self, title: str, subtitle: str | None = None) -> None:
        self.app_title_label.setText(title)
        self.subtitle_label.setText(subtitle or "Không gian quản lý tập trung")
