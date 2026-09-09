from __future__ import annotations

from collections.abc import Callable, Iterable

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtWidgets import QVBoxLayout, QWidget

from models.dto.dashboard_dto import DashboardStatusItem
from ui.theme import (
    BORDER,
    CHART_ACCENTS,
    SURFACE,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)
from utils.report_labels import status_label


CHART_COLORS = CHART_ACCENTS


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

        self.figure = Figure(
            figsize=(5.2, 3.0),
            tight_layout=True,
            facecolor=SURFACE,
        )
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet(f"background-color: {SURFACE}; border: none;")
        self.axes = self.figure.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.addWidget(self.canvas)

        self.set_data(())

    def set_data(
        self,
        items: Iterable[DashboardStatusItem],
    ) -> None:
        data = tuple(items)
        self.axes.clear()
        self._style_axes()

        if not data or sum(item.count for item in data) == 0:
            self._draw_empty(self.empty_message)
            return

        labels = [self.label_formatter(item.status) for item in data]
        values = [item.count for item in data]
        positions = list(range(len(data)))

        bars = self.axes.bar(
            positions,
            values,
            color=[CHART_COLORS[index % len(CHART_COLORS)] for index in positions],
            width=0.62,
        )

        self.axes.set_axis_on()
        self.axes.set_title(self.title, color=TEXT_PRIMARY, pad=14, fontweight="semibold")
        self.axes.set_ylabel(self.y_label, color=TEXT_SECONDARY)
        self.axes.set_xticks(positions)
        self.axes.set_xticklabels(
            labels,
            rotation=25,
            ha="right",
        )
        self.axes.tick_params(axis="both", colors=TEXT_SECONDARY, labelsize=9)
        self.axes.yaxis.grid(True, color=BORDER, alpha=0.45, linewidth=0.8)
        self.axes.set_axisbelow(True)
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
                color=TEXT_PRIMARY,
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
            color=TEXT_SECONDARY,
            fontsize=11,
        )
        self.canvas.draw_idle()

    def _style_axes(self) -> None:
        self.figure.set_facecolor(SURFACE)
        self.axes.set_facecolor(SURFACE)
        for spine in self.axes.spines.values():
            spine.set_color(BORDER)
            spine.set_linewidth(0.8)


class DashboardDonutChart(QWidget):
    """Biểu đồ donut tỷ trọng hồ sơ theo trạng thái."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardDonutChart")

        self.figure = Figure(
            figsize=(5.2, 3.0),
            tight_layout=True,
            facecolor=SURFACE,
        )
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet(f"background-color: {SURFACE}; border: none;")
        self.axes = self.figure.add_subplot(111)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
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
        self.figure.set_facecolor(SURFACE)
        self.axes.set_facecolor(SURFACE)

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
            colors=[CHART_COLORS[index % len(CHART_COLORS)] for index in range(len(values))],
            textprops={"color": TEXT_PRIMARY, "fontsize": 9},
            wedgeprops={"width": 0.42, "edgecolor": SURFACE, "linewidth": 2},
        )

        self.axes.set_axis_on()
        self.axes.text(
            0,
            0,
            f"{total}\nhồ sơ",
            ha="center",
            va="center",
            color=TEXT_PRIMARY,
            fontweight="semibold",
        )
        self.axes.set_title(
            "Tỷ trọng trạng thái",
            color=TEXT_PRIMARY,
            pad=14,
            fontweight="semibold",
        )
        legend = self.axes.legend(
            wedges,
            labels,
            loc="center left",
            bbox_to_anchor=(1.0, 0.5),
            frameon=False,
        )
        for text in legend.get_texts():
            text.set_color(TEXT_SECONDARY)
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
            color=TEXT_SECONDARY,
            fontsize=11,
        )
        self.canvas.draw_idle()
