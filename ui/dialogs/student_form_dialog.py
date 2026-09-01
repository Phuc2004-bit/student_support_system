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
    QLineEdit,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.dto import Student, StudentCreateData, StudentUpdateData


class StudentFormDialog(QDialog):
    """
    Form dùng chung cho:
    - CREATE: tạo học sinh mới
    - EDIT: cập nhật hồ sơ học sinh

    Không xử lý lớp học tại đây.
    Việc xếp lớp/chuyển lớp thuộc Enrollment (Bước 9.5).
    """

    MODE_CREATE = "CREATE"
    MODE_EDIT = "EDIT"

    def __init__(
        self,
        student: Student | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)

        self.student = student
        self.mode = (
            self.MODE_EDIT
            if student is not None
            else self.MODE_CREATE
        )

        self.setWindowTitle(
            "Sửa học sinh"
            if self.mode == self.MODE_EDIT
            else "Thêm học sinh"
        )
        self.setModal(True)
        self.resize(520, 520)

        self._build_ui()
        self._load_student_if_needed()
        self._connect_signals()

    # =====================================================
    # UI
    # =====================================================

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        self.title_label = QLabel(
            "Cập nhật hồ sơ học sinh"
            if self.mode == self.MODE_EDIT
            else "Thêm học sinh mới",
            self,
        )
        root.addWidget(self.title_label)

        form = QFormLayout()

        self.student_code_input = QLineEdit(self)
        self.student_code_input.setPlaceholderText("Ví dụ: HS0001")

        self.full_name_input = QLineEdit(self)
        self.full_name_input.setPlaceholderText("Nhập họ và tên")

        self.date_of_birth_input = QDateEdit(self)
        self.date_of_birth_input.setCalendarPopup(True)
        self.date_of_birth_input.setDisplayFormat("dd/MM/yyyy")
        self.date_of_birth_input.setDate(QDate.currentDate())

        self.gender_combo = QComboBox(self)
        self.gender_combo.addItem("Không xác định", None)
        self.gender_combo.addItem("Nam", "Nam")
        self.gender_combo.addItem("Nữ", "Nữ")
        self.gender_combo.addItem("Khác", "Khác")

        self.phone_input = QLineEdit(self)
        self.phone_input.setPlaceholderText("Số điện thoại")

        self.email_input = QLineEdit(self)
        self.email_input.setPlaceholderText("Email")

        self.address_input = QTextEdit(self)
        self.address_input.setPlaceholderText("Địa chỉ")
        self.address_input.setFixedHeight(90)

        form.addRow("Mã học sinh *", self.student_code_input)
        form.addRow("Họ và tên *", self.full_name_input)
        form.addRow("Ngày sinh", self.date_of_birth_input)
        form.addRow("Giới tính", self.gender_combo)
        form.addRow("Điện thoại", self.phone_input)
        form.addRow("Email", self.email_input)
        form.addRow("Địa chỉ", self.address_input)

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
            "Cập nhật"
            if self.mode == self.MODE_EDIT
            else "Thêm học sinh"
        )
        self.cancel_button.setText("Hủy")

        root.addWidget(self.button_box)

    def _connect_signals(self) -> None:
        self.button_box.accepted.connect(
            self._validate_and_accept
        )
        self.button_box.rejected.connect(
            self.reject
        )

    # =====================================================
    # EDIT MODE
    # =====================================================

    def _load_student_if_needed(self) -> None:
        if self.student is None:
            return

        self.student_code_input.setText(
            self.student.student_code
        )
        self.student_code_input.setEnabled(False)

        self.full_name_input.setText(
            self.student.full_name
        )

        if self.student.date_of_birth is not None:
            dob = self.student.date_of_birth
            self.date_of_birth_input.setDate(
                QDate(
                    dob.year,
                    dob.month,
                    dob.day,
                )
            )

        gender_index = self.gender_combo.findData(
            self.student.gender
        )
        if gender_index >= 0:
            self.gender_combo.setCurrentIndex(
                gender_index
            )

        self.phone_input.setText(
            self.student.phone or ""
        )
        self.email_input.setText(
            self.student.email or ""
        )
        self.address_input.setPlainText(
            self.student.address or ""
        )

    # =====================================================
    # VALIDATION
    # =====================================================

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

    def validation_error(self) -> str | None:
        if (
            self.mode == self.MODE_CREATE
            and not self.student_code_input.text().strip()
        ):
            return "Mã học sinh không được để trống."

        if not self.full_name_input.text().strip():
            return "Họ và tên học sinh không được để trống."

        email = self.email_input.text().strip()
        if email and "@" not in email:
            return "Email không hợp lệ."

        phone = self.phone_input.text().strip()
        if phone and not phone.isdigit():
            return "Số điện thoại chỉ được chứa chữ số."

        return None

    # =====================================================
    # DTO OUTPUT
    # =====================================================

    @staticmethod
    def _optional_text(value: str) -> str | None:
        value = value.strip()
        return value or None

    def _date_value(self) -> date:
        value = self.date_of_birth_input.date()

        return date(
            value.year(),
            value.month(),
            value.day(),
        )

    def create_data(self) -> StudentCreateData:
        if self.mode != self.MODE_CREATE:
            raise RuntimeError(
                "create_data() chỉ dùng trong chế độ CREATE."
            )

        error = self.validation_error()
        if error is not None:
            raise ValueError(error)

        return StudentCreateData(
            student_code=self.student_code_input.text().strip(),
            full_name=self.full_name_input.text().strip(),
            date_of_birth=self._date_value(),
            gender=self.gender_combo.currentData(),
            phone=self._optional_text(
                self.phone_input.text()
            ),
            email=self._optional_text(
                self.email_input.text()
            ),
            address=self._optional_text(
                self.address_input.toPlainText()
            ),
        )

    def update_data(self) -> StudentUpdateData:
        if self.mode != self.MODE_EDIT:
            raise RuntimeError(
                "update_data() chỉ dùng trong chế độ EDIT."
            )

        error = self.validation_error()
        if error is not None:
            raise ValueError(error)

        return StudentUpdateData(
            full_name=self.full_name_input.text().strip(),
            date_of_birth=self._date_value(),
            gender=self.gender_combo.currentData(),
            phone=self._optional_text(
                self.phone_input.text()
            ),
            email=self._optional_text(
                self.email_input.text()
            ),
            address=self._optional_text(
                self.address_input.toPlainText()
            ),
        )
