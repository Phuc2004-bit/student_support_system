from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
    QWidget,
)


class KpiCard(QFrame):
    """
    Thẻ KPI tái sử dụng.

    Component chỉ chịu trách nhiệm hiển thị:
    - tiêu đề KPI;
    - giá trị KPI.

    Không gọi service và không chứa business logic.
    """

    def __init__(
        self,
        title: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        if not isinstance(title, str) or not title.strip():
            raise ValueError(
                "Tiêu đề KPI không được để trống."
            )

        self._title = title.strip()
        self._value = 0

        self.setObjectName("kpiCard")
        self.setFrameShape(
            QFrame.Shape.StyledPanel
        )

        self._build_ui()
        self.set_value(0)

    @property
    def title(self) -> str:
        return self._title

    @property
    def value(self) -> int:
        return self._value

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )
        layout.setSpacing(8)

        self.title_label = QLabel(
            self._title,
            self,
        )
        self.title_label.setObjectName(
            "kpiCardTitleLabel"
        )
        self.title_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        self.value_label = QLabel(
            "0",
            self,
        )
        self.value_label.setObjectName(
            "kpiCardValueLabel"
        )
        self.value_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(
            self.title_label
        )
        layout.addWidget(
            self.value_label
        )
        layout.addStretch(1)

    def set_value(
        self,
        value: int,
    ) -> None:
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < 0
        ):
            raise ValueError(
                "Giá trị KPI phải là số nguyên không âm."
            )

        self._value = value
        self.value_label.setText(
            f"{value:,}".replace(",", ".")
        )
