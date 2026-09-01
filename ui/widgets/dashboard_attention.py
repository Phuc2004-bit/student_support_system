from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.dto.dashboard_dto import DashboardAttentionItem
from ui.widgets.dashboard_charts import status_label


class DashboardAttentionTable(QWidget):
    """
    Danh sách hồ sơ cần ưu tiên xử lý trên Dashboard.

    Chỉ nhận DashboardAttentionItem đã được Service/Repository chuẩn bị.
    Không truy vấn database và không chứa business logic.
    """

    HEADERS = (
        "Mã HS",
        "Họ và tên",
        "Lớp",
        "Môn",
        "Trạng thái",
        "Ngày phát hiện",
        "Điểm phát hiện",
        "Điểm đánh giá gần nhất",
    )

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.setObjectName("dashboardAttentionTableWidget")
        self._items: tuple[DashboardAttentionItem, ...] = ()

        self._build_ui()
        self.set_items(())

    @property
    def items(self) -> tuple[DashboardAttentionItem, ...]:
        return self._items

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.empty_label = QLabel(
            "Không có hồ sơ cần chú ý.",
            self,
        )
        self.empty_label.setObjectName(
            "dashboardAttentionEmptyLabel"
        )
        self.empty_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.table = QTableWidget(self)
        self.table.setObjectName(
            "dashboardAttentionTable"
        )
        self.table.setColumnCount(
            len(self.HEADERS)
        )
        self.table.setHorizontalHeaderLabels(
            self.HEADERS
        )
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            1,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(
            3,
            QHeaderView.ResizeMode.Stretch,
        )

        layout.addWidget(self.empty_label)
        layout.addWidget(self.table)

    def set_items(
        self,
        items: Iterable[DashboardAttentionItem],
    ) -> None:
        self._items = tuple(items)

        self.table.setRowCount(0)

        for row_index, item in enumerate(self._items):
            self.table.insertRow(row_index)

            values = (
                item.student_code,
                item.full_name,
                item.class_name,
                item.subject_name,
                status_label(item.status),
                item.detected_date.strftime("%d/%m/%Y"),
                self._format_score(item.trigger_score),
                self._format_score(item.latest_review_score),
            )

            for column_index, value in enumerate(values):
                cell = QTableWidgetItem(value)

                if column_index in (0, 2, 4, 5, 6, 7):
                    cell.setTextAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                self.table.setItem(
                    row_index,
                    column_index,
                    cell,
                )

        has_items = bool(self._items)
        self.empty_label.setVisible(not has_items)
        self.table.setVisible(has_items)

    def intervention_id_at_row(
        self,
        row: int,
    ) -> int | None:
        if row < 0 or row >= len(self._items):
            return None

        return self._items[row].intervention_id

    @staticmethod
    def _format_score(
        value: Decimal | None,
    ) -> str:
        if value is None:
            return "—"

        normalized = value.quantize(
            Decimal("0.01")
        )
        return f"{normalized:.2f}"
