from __future__ import annotations

from collections.abc import Callable, Iterable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from models.dto.dashboard_dto import DashboardStatusItem


STATUS_LABELS = {
    "DETECTED": "Mới phát hiện",
    "PLANNED": "Đã lập kế hoạch",
    "IN_PROGRESS": "Đang bổ trợ",
    "WAITING_REVIEW": "Chờ đánh giá",
    "CONTINUE": "Cần tiếp tục",
    "COMPLETED": "Đã đạt ngưỡng",
}


def status_label(status: str) -> str:
    return STATUS_LABELS.get(status, status)


class DashboardBarChart(QWidget):
    """Biểu đồ cột số hồ sơ bổ trợ theo trạng thái."""

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        title: str = "Hồ sơ bổ trợ theo trạng thái",
        y_label: str = "Số hồ sơ",
        empty_message: str = "Chưa có dữ liệu trạng thái",
        label_formatter: Callable[[str], str] = status_label,
        object_name: str = "dashboardBarChart",
    ) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)
        self.title = title
        self.y_label = y_label
        self.empty_message = empty_message
        self.label_formatter = label_formatter

        self.figure = Figure(figsize=(5.2, 3.0), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.set_data(())

    def set_data(
        self,
        items: Iterable[DashboardStatusItem],
    ) -> None:
        data = tuple(items)
        self.axes.clear()

        if not data or sum(item.count for item in data) == 0:
            self._draw_empty(self.empty_message)
            return

        labels = [self.label_formatter(item.status) for item in data]
        values = [item.count for item in data]
        positions = list(range(len(data)))

        bars = self.axes.bar(positions, values)

        self.axes.set_title(self.title)
        self.axes.set_ylabel(self.y_label)
        self.axes.set_xticks(positions)
        self.axes.set_xticklabels(
            labels,
            rotation=25,
            ha="right",
        )
        self.axes.set_ylim(
            bottom=0,
            top=max(values) * 1.18 if max(values) > 0 else 1,
        )

        for bar, value in zip(bars, values):
            self.axes.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                str(value),
                ha="center",
                va="bottom",
            )

        self.canvas.draw_idle()

    def _draw_empty(self, message: str) -> None:
        self.axes.set_axis_off()
        self.axes.text(
            0.5,
            0.5,
            message,
            transform=self.axes.transAxes,
            ha="center",
            va="center",
        )
        self.canvas.draw_idle()


class DashboardDonutChart(QWidget):
    """Biểu đồ donut tỷ trọng hồ sơ theo trạng thái."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardDonutChart")

        self.figure = Figure(figsize=(5.2, 3.0), tight_layout=True)
        self.canvas = FigureCanvas(self.figure)
        self.axes = self.figure.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)

        self.set_data(())

    def set_data(
        self,
        items: Iterable[DashboardStatusItem],
    ) -> None:
        data = tuple(
            item
            for item in items
            if item.count > 0
        )
        self.axes.clear()

        total = sum(item.count for item in data)
        if not data or total == 0:
            self._draw_empty("Chưa có dữ liệu trạng thái")
            return

        labels = [status_label(item.status) for item in data]
        values = [item.count for item in data]

        wedges, _, _ = self.axes.pie(
            values,
            autopct=lambda pct: f"{pct:.0f}%" if pct >= 4 else "",
            startangle=90,
            wedgeprops={"width": 0.42},
        )

        self.axes.text(
            0,
            0,
            f"{total}\nhồ sơ",
            ha="center",
            va="center",
        )
        self.axes.set_title("Tỷ trọng trạng thái")
        self.axes.legend(
            wedges,
            labels,
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            frameon=False,
        )
        self.axes.axis("equal")
        self.canvas.draw_idle()

    def _draw_empty(self, message: str) -> None:
        self.axes.set_axis_off()
        self.axes.text(
            0.5,
            0.5,
            message,
            transform=self.axes.transAxes,
            ha="center",
            va="center",
        )
        self.canvas.draw_idle()
