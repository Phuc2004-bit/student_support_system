from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.dto import UserSession
from models.enums import UserRole


@dataclass(frozen=True)
class SidebarItem:
    key: str
    text: str


class Sidebar(QFrame):
    """
    Thanh điều hướng bên trái.

    Bước 7.2 chỉ chịu trách nhiệm:
    - hiển thị menu;
    - quản lý trạng thái mục đang chọn;
    - phát signal khi người dùng chọn mục.

    Sidebar không tự chuyển page và không chứa business logic.
    """

    navigation_requested = Signal(str)
    logout_requested = Signal()

    ITEMS = (
        SidebarItem("dashboard", "Tổng quan"),
        SidebarItem("students", "Học sinh"),
        SidebarItem("scores", "Điểm & Đánh giá"),
        SidebarItem("support", "Bổ trợ học tập"),
        SidebarItem("reports", "Báo cáo & Thống kê"),
        SidebarItem("catalogs", "Danh mục"),
        SidebarItem("system", "Hệ thống"),
    )

    SECTIONS = (
        ("TỔNG QUAN", ("dashboard",)),
        ("QUẢN LÝ", ("students", "scores", "support", "reports")),
        ("QUẢN TRỊ", ("catalogs", "system")),
    )

    ROLE_LABELS = {
        UserRole.ADMIN: "Quản trị viên",
        UserRole.TEACHER: "Giáo viên",
    }

    def __init__(
        self,
        parent: QWidget | None = None,
        session: UserSession | None = None,
    ) -> None:
        super().__init__(parent)

        self.session = session
        self.setObjectName("sidebar")

        self._buttons: dict[str, QPushButton] = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)

        self._build_ui()
        self.set_current_item("dashboard")

    @property
    def current_key(self) -> str | None:
        checked = self._button_group.checkedButton()

        if checked is None:
            return None

        return checked.property("navigation_key")

    def button(self, key: str) -> QPushButton:
        try:
            return self._buttons[key]
        except KeyError as exc:
            raise KeyError(
                f"Không tồn tại mục sidebar: {key}"
            ) from exc

    def set_current_item(
        self,
        key: str,
    ) -> None:
        button = self.button(key)
        button.setChecked(True)

    def set_item_visible(
        self,
        key: str,
        visible: bool,
    ) -> None:
        self.button(key).setVisible(visible)

    def set_item_enabled(
        self,
        key: str,
        enabled: bool,
    ) -> None:
        self.button(key).setEnabled(enabled)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            14,
            18,
            14,
            14,
        )
        layout.setSpacing(4)

        self._build_brand(layout)

        items_by_key = {item.key: item for item in self.ITEMS}
        self.section_labels: dict[str, QLabel] = {}

        for section_name, keys in self.SECTIONS:
            section_label = QLabel(section_name, self)
            section_label.setProperty("sidebarSection", True)
            section_label.setObjectName(
                "sidebarSection_" + section_name.lower().replace(" ", "_")
            )
            self.section_labels[section_name] = section_label
            layout.addWidget(section_label)

            for key in keys:
                item = items_by_key[key]
                button = self._create_navigation_button(item)
                layout.addWidget(button)

        layout.addStretch(1)
        self._build_user_block(layout)

    def _build_brand(self, layout: QVBoxLayout) -> None:
        brand = QWidget(self)
        brand.setObjectName("sidebarBrand")
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(4, 0, 4, 12)
        brand_layout.setSpacing(10)

        self.brand_mark_label = QLabel("SS", brand)
        self.brand_mark_label.setObjectName("sidebarBrandMark")
        self.brand_mark_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        self.brand_title_label = QLabel("Student Support", brand)
        self.brand_title_label.setObjectName("sidebarBrandTitle")
        self.brand_subtitle_label = QLabel("Quản lý học tập", brand)
        self.brand_subtitle_label.setObjectName("sidebarBrandSubtitle")
        text_layout.addWidget(self.brand_title_label)
        text_layout.addWidget(self.brand_subtitle_label)

        brand_layout.addWidget(self.brand_mark_label)
        brand_layout.addLayout(text_layout, 1)
        layout.addWidget(brand)

    def _create_navigation_button(self, item: SidebarItem) -> QPushButton:
        button = QPushButton(item.text, self)
        button.setObjectName(f"nav_{item.key}")
        button.setProperty("navigation_key", item.key)
        button.setProperty("navItem", True)
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(
            lambda checked=False, key=item.key: self._on_navigation_clicked(key)
        )

        self._button_group.addButton(button)
        self._buttons[item.key] = button
        return button

    def _build_user_block(self, layout: QVBoxLayout) -> None:
        self.user_block = QFrame(self)
        self.user_block.setObjectName("sidebarUserBlock")
        user_layout = QVBoxLayout(self.user_block)
        user_layout.setContentsMargins(10, 10, 10, 10)
        user_layout.setSpacing(8)

        identity_layout = QHBoxLayout()
        identity_layout.setContentsMargins(0, 0, 0, 0)
        identity_layout.setSpacing(9)

        full_name = self.session.full_name if self.session is not None else ""
        self.avatar_label = QLabel(self._initials(full_name), self.user_block)
        self.avatar_label.setObjectName("sidebarAvatarLabel")
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        labels_layout = QVBoxLayout()
        labels_layout.setContentsMargins(0, 0, 0, 0)
        labels_layout.setSpacing(1)
        self.user_label = QLabel(full_name, self.user_block)
        self.user_label.setObjectName("sidebarUserLabel")
        self.role_label = QLabel(
            self.ROLE_LABELS.get(self.session.role, "")
            if self.session is not None
            else "",
            self.user_block,
        )
        self.role_label.setObjectName("sidebarRoleLabel")
        labels_layout.addWidget(self.user_label)
        labels_layout.addWidget(self.role_label)

        identity_layout.addWidget(self.avatar_label)
        identity_layout.addLayout(labels_layout, 1)
        user_layout.addLayout(identity_layout)

        self.logout_button = QPushButton("Đăng xuất", self.user_block)
        self.logout_button.setObjectName("sidebarLogoutButton")
        self.logout_button.setProperty("variant", "danger")
        self.logout_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.logout_button.clicked.connect(self.logout_requested.emit)
        user_layout.addWidget(self.logout_button)

        self.user_block.setVisible(self.session is not None)
        layout.addWidget(self.user_block)

    @staticmethod
    def _initials(full_name: str) -> str:
        parts = [part for part in full_name.strip().split() if part]
        if not parts:
            return "?"
        return "".join(part[0] for part in parts[-2:]).upper()

    def _on_navigation_clicked(
        self,
        key: str,
    ) -> None:
        self.navigation_requested.emit(key)
