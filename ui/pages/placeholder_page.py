from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)


class PlaceholderPage(QWidget):
    """
    Page khung dùng trong Bước 7.4.

    Các page nghiệp vụ thật sẽ thay thế dần ở các bước sau.
    """

    def __init__(
        self,
        title: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.title = title
        self.setObjectName("placeholderPage")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        self.title_label = QLabel(
            title,
            self,
        )
        self.title_label.setObjectName(
            "pageTitleLabel"
        )
        self.title_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            self.title_label,
            1,
        )
