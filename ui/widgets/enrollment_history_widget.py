from __future__ import annotations

from collections.abc import Iterable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.dto.enrollment import EnrollmentListItem
from ui.theme import status_badge_colors


def enrollment_status_label(status) -> str:
    value = getattr(status, "value", status)
    return {
        "ACTIVE": "Đang học",
        "TRANSFERRED": "Đã chuyển lớp",
        "COMPLETED": "Đã hoàn thành",
    }.get(str(value), str(value))


class EnrollmentHistoryWidget(QWidget):
    TABLE_HEADERS = (
        "Năm học",
        "Khối",
        "Lớp",
        "Trạng thái",
    )

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._history: tuple[EnrollmentListItem, ...] = ()

        self.setObjectName("enrollmentHistoryWidget")
        self._build_ui()

    @property
    def history(self) -> tuple[EnrollmentListItem, ...]:
        return self._history

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        self.heading_label = QLabel(
            "Lịch sử xếp lớp",
            self,
        )
        self.heading_label.setObjectName("enrollmentHistoryHeading")
        root.addWidget(self.heading_label)

        self.table = QTableWidget(self)
        self.table.setObjectName("enrollmentHistoryTable")
        self.table.setColumnCount(len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.NoSelection
        )
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)

        header = self.table.horizontalHeader()
        header.setMinimumHeight(38)
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        root.addWidget(self.table)

    def set_history(
        self,
        history: Iterable[EnrollmentListItem],
    ) -> None:
        self._history = tuple(history)
        self.table.setRowCount(len(self._history))

        for row, item in enumerate(self._history):
            values = (
                item.school_year_name,
                str(item.grade_number),
                item.class_name,
                enrollment_status_label(item.status),
            )

            for column, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
                if column == 3:
                    foreground, background = status_badge_colors(item.status)
                    cell.setForeground(QColor(foreground))
                    cell.setBackground(QColor(background))
                self.table.setItem(row, column, cell)
