from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


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

    ITEMS = (
        SidebarItem("dashboard", "Tổng quan"),
        SidebarItem("students", "Học sinh"),
        SidebarItem("scores", "Điểm & Đánh giá"),
        SidebarItem("support", "Bổ trợ học tập"),
        SidebarItem("reports", "Báo cáo & Thống kê"),
        SidebarItem("catalogs", "Danh mục"),
        SidebarItem("system", "Hệ thống"),
    )

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

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
            12,
            16,
            12,
            16,
        )
        layout.setSpacing(6)

        for item in self.ITEMS:
            button = QPushButton(
                item.text,
                self,
            )
            button.setObjectName(
                f"nav_{item.key}"
            )
            button.setProperty(
                "navigation_key",
                item.key,
            )
            button.setCheckable(True)

            button.clicked.connect(
                lambda checked=False, key=item.key:
                self._on_navigation_clicked(key)
            )

            self._button_group.addButton(button)
            self._buttons[item.key] = button
            layout.addWidget(button)

        layout.addStretch(1)

    def _on_navigation_clicked(
        self,
        key: str,
    ) -> None:
        self.navigation_requested.emit(key)
