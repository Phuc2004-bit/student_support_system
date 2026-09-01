from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from models.dto.enrollment import EnrollmentListItem


class CurrentEnrollmentWidget(QWidget):
    assign_requested = Signal()
    transfer_requested = Signal()

    def __init__(
        self,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self._enrollment: EnrollmentListItem | None = None
        self._build_ui()
        self._connect_signals()
        self.set_enrollment(None)

    @property
    def enrollment(
        self,
    ) -> EnrollmentListItem | None:
        return self._enrollment

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        self.heading_label = QLabel(
            "Lớp hiện tại",
            self,
        )
        root.addWidget(self.heading_label)

        self.class_label = QLabel(
            "Chưa xếp lớp",
            self,
        )
        self.year_label = QLabel(
            "—",
            self,
        )
        self.grade_label = QLabel(
            "—",
            self,
        )

        root.addWidget(self.class_label)
        root.addWidget(self.year_label)
        root.addWidget(self.grade_label)

        actions = QHBoxLayout()

        self.assign_button = QPushButton(
            "Xếp lớp",
            self,
        )
        self.transfer_button = QPushButton(
            "Chuyển lớp",
            self,
        )

        actions.addWidget(self.assign_button)
        actions.addWidget(self.transfer_button)
        actions.addStretch(1)

        root.addLayout(actions)

    def _connect_signals(self) -> None:
        self.assign_button.clicked.connect(
            self.assign_requested.emit
        )
        self.transfer_button.clicked.connect(
            self.transfer_requested.emit
        )

    def set_enrollment(
        self,
        enrollment: EnrollmentListItem | None,
    ) -> None:
        self._enrollment = enrollment

        if enrollment is None:
            self.class_label.setText(
                "Chưa xếp lớp"
            )
            self.year_label.setText(
                "Năm học: —"
            )
            self.grade_label.setText(
                "Khối: —"
            )
            self.assign_button.setVisible(True)
            self.transfer_button.setVisible(False)
            return

        self.class_label.setText(
            enrollment.class_name
        )
        self.year_label.setText(
            f"Năm học: {enrollment.school_year_name}"
        )
        self.grade_label.setText(
            f"Khối: {enrollment.grade_number}"
        )
        self.assign_button.setVisible(False)
        self.transfer_button.setVisible(True)
