from __future__ import annotations

from datetime import date

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)


class EnrollmentDialog(QDialog):
    """
    Dialog dùng cho hai trường hợp:
    - ASSIGN: xếp lớp lần đầu
    - TRANSFER: chuyển lớp

    Dialog chỉ thu thập class_id + ngày thực hiện.
    Việc ghi dữ liệu và quy tắc nghiệp vụ thuộc EnrollmentService.
    """

    MODE_ASSIGN = "ASSIGN"
    MODE_TRANSFER = "TRANSFER"

    def __init__(
        self,
        academic_service=None,
        mode: str = MODE_ASSIGN,
        current_class_id: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        if mode not in {
            self.MODE_ASSIGN,
            self.MODE_TRANSFER,
        }:
            raise ValueError("Chế độ enrollment không hợp lệ.")

        self.academic_service = academic_service
        self.mode = mode
        self.current_class_id = current_class_id

        self.setWindowTitle(
            "Chuyển lớp"
            if mode == self.MODE_TRANSFER
            else "Xếp lớp"
        )
        self.setModal(True)
        self.resize(460, 260)

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        self.title_label = QLabel(
            "Chọn lớp mới cho học sinh"
            if self.mode == self.MODE_TRANSFER
            else "Xếp lớp hiện tại cho học sinh",
            self,
        )
        root.addWidget(self.title_label)

        form = QFormLayout()

        self.school_year_combo = QComboBox(self)
        self.class_combo = QComboBox(self)

        self.action_date_input = QDateEdit(self)
        self.action_date_input.setCalendarPopup(True)
        self.action_date_input.setDisplayFormat("dd/MM/yyyy")
        self.action_date_input.setDate(QDate.currentDate())

        form.addRow("Năm học *", self.school_year_combo)
        form.addRow("Lớp *", self.class_combo)
        form.addRow(
            "Ngày chuyển"
            if self.mode == self.MODE_TRANSFER
            else "Ngày xếp lớp",
            self.action_date_input,
        )

        root.addLayout(form)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.save_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Save
        )
        self.cancel_button = self.button_box.button(
            QDialogButtonBox.StandardButton.Cancel
        )

        self.save_button.setText(
            "Chuyển lớp"
            if self.mode == self.MODE_TRANSFER
            else "Xếp lớp"
        )
        self.cancel_button.setText("Hủy")

        root.addWidget(self.button_box)

    def _connect_signals(self) -> None:
        self.school_year_combo.currentIndexChanged.connect(
            self._reload_classes
        )
        self.button_box.accepted.connect(
            self._validate_and_accept
        )
        self.button_box.rejected.connect(
            self.reject
        )

    def load_options(self) -> None:
        self.school_year_combo.blockSignals(True)
        self.school_year_combo.clear()
        self.school_year_combo.addItem(
            "Chọn năm học",
            None,
        )

        if self.academic_service is not None:
            years = self.academic_service.list_school_years()

            current_index = 0
            for year in years:
                self.school_year_combo.addItem(
                    year.year_name,
                    year.school_year_id,
                )
                if getattr(year, "is_current", False):
                    current_index = (
                        self.school_year_combo.count() - 1
                    )

            self.school_year_combo.setCurrentIndex(
                current_index
            )

        self.school_year_combo.blockSignals(False)
        self._reload_classes()

    def _reload_classes(self) -> None:
        self.class_combo.clear()
        self.class_combo.addItem(
            "Chọn lớp",
            None,
        )

        if self.academic_service is None:
            return

        school_year_id = self.school_year_combo.currentData()
        if school_year_id is None:
            return

        classes = (
            self.academic_service
            .list_classes_by_school_year(
                school_year_id
            )
        )

        for item in classes:
            if not getattr(item, "is_active", True):
                continue

            class_id = getattr(item, "class_id")
            if (
                self.mode == self.MODE_TRANSFER
                and self.current_class_id is not None
                and class_id == self.current_class_id
            ):
                continue

            label = getattr(
                item,
                "class_name",
                str(class_id),
            )
            self.class_combo.addItem(
                label,
                class_id,
            )

    def validation_error(self) -> str | None:
        if self.school_year_combo.currentData() is None:
            return "Vui lòng chọn năm học."

        if self.class_combo.currentData() is None:
            return "Vui lòng chọn lớp."

        return None

    def _validate_and_accept(self) -> None:
        error = self.validation_error()

        if error is not None:
            QMessageBox.warning(
                self,
                "Dữ liệu chưa hợp lệ",
                error,
            )
            return

        self.accept()

    def selected_class_id(self) -> int:
        error = self.validation_error()
        if error is not None:
            raise ValueError(error)

        return int(
            self.class_combo.currentData()
        )

    def action_date(self) -> date:
        value = self.action_date_input.date()
        return date(
            value.year(),
            value.month(),
            value.day(),
        )
