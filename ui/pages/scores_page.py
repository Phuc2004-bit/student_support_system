from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.dto.enrollment import EnrollmentListItem
from models.dto.score import ScoreCreateData, ScoreRosterItem
from services.enrollment_contract import EnrollmentServiceContract
from services.score_contract import (
    ScoreServiceContract as ScoreWriterContract,
)
from ui.widgets.score_context_filter_widget import (
    ScoreContextFilterWidget,
    ScoreContextSelection,
)


def save_score_batch(
    service: ScoreWriterContract,
    entries: tuple[ScoreCreateData, ...],
):
    return service.create_scores(entries)


class ScoresPage(QWidget):
    scores_saved = Signal(int)

    TABLE_HEADERS = (
        "STT",
        "Mã học sinh",
        "Họ và tên",
        "Điểm",
        "Trạng thái",
    )

    def __init__(
        self,
        academic_service=None,
        enrollment_service: EnrollmentServiceContract | None = None,
        score_service: ScoreWriterContract | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.academic_service = academic_service
        self.enrollment_service = enrollment_service
        self.score_service = score_service
        self._enrollments: tuple[EnrollmentListItem, ...] = ()
        self._score_rows: tuple[ScoreRosterItem, ...] = ()
        self._saved_enrollment_ids: set[int] = set()
        self.setObjectName("scoresPage")
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(16)

        self.title_label = QLabel("Điểm & Đánh giá", self)
        self.subtitle_label = QLabel(
            "Chọn đầy đủ ngữ cảnh để xem bảng điểm.",
            self,
        )
        root.addWidget(self.title_label)
        root.addWidget(self.subtitle_label)

        self.context_filter = ScoreContextFilterWidget(
            academic_service=self.academic_service,
            parent=self,
        )
        root.addWidget(self.context_filter)

        self.school_year_combo = self.context_filter.school_year_combo
        self.grade_combo = self.context_filter.grade_combo
        self.class_combo = self.context_filter.class_combo
        self.subject_combo = self.context_filter.subject_combo
        self.assessment_combo = self.context_filter.assessment_combo

        self.context_status_label = QLabel(self)
        root.addWidget(self.context_status_label)

        self.score_table_placeholder = QFrame(self)
        self.score_table_placeholder.setObjectName(
            "scoreTablePlaceholder"
        )
        placeholder_layout = QVBoxLayout(
            self.score_table_placeholder
        )
        self.placeholder_label = QLabel(
            "Bảng điểm sẽ hiển thị tại đây.",
            self.score_table_placeholder,
        )
        self.placeholder_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        placeholder_layout.addWidget(self.placeholder_label)

        self.score_table = QTableWidget(
            self.score_table_placeholder
        )
        self.score_table.setColumnCount(len(self.TABLE_HEADERS))
        self.score_table.setHorizontalHeaderLabels(
            self.TABLE_HEADERS
        )
        self.score_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.score_table.setAlternatingRowColors(True)
        self.score_table.verticalHeader().setVisible(False)
        header = self.score_table.horizontalHeader()
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )
        placeholder_layout.addWidget(self.score_table, 1)
        root.addWidget(self.score_table_placeholder, 1)

        actions = QHBoxLayout()
        actions.addStretch(1)
        self.save_button = QPushButton("Lưu điểm", self)
        self.save_button.setEnabled(False)
        actions.addWidget(self.save_button)
        root.addLayout(actions)

        self.context_filter.context_changed.connect(
            self._on_context_changed
        )
        self.score_table.itemChanged.connect(
            self._update_save_state
        )
        self.save_button.clicked.connect(
            lambda _checked=False: self.save_scores()
        )
        self._on_context_changed(
            self.context_filter.current_value()
        )

    def initialize_scores(self) -> bool:
        if self.academic_service is None:
            return False
        self.context_filter.load_options()
        return True

    def current_context(self) -> ScoreContextSelection:
        return self.context_filter.current_value()

    @property
    def enrollments(self) -> tuple[EnrollmentListItem, ...]:
        return self._enrollments

    @property
    def score_rows(self) -> tuple[ScoreRosterItem, ...]:
        return self._score_rows

    def enrollment_id_at_row(self, row: int) -> int | None:
        if row < 0 or row >= self.score_table.rowCount():
            return None
        item = self.score_table.item(row, 0)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def score_id_at_row(self, row: int) -> int | None:
        if row < 0 or row >= self.score_table.rowCount():
            return None
        item = self.score_table.item(row, 3)
        if item is None:
            return None
        return item.data(Qt.ItemDataRole.UserRole)

    def _on_context_changed(
        self,
        context: ScoreContextSelection,
    ) -> None:
        if context.is_complete:
            self.context_status_label.setText(
                "Đã chọn đầy đủ ngữ cảnh."
            )
            if self._can_read_scores():
                self.load_students()
            return

        self._clear_students(
            "Chọn đầy đủ ngữ cảnh để tải danh sách học sinh."
        )
        self.context_status_label.setText(
            "Vui lòng chọn năm học, khối, lớp, môn học "
            "và bài đánh giá."
        )

    def load_students(self) -> bool:
        context = self.current_context()
        if not context.is_complete or not self._can_read_scores():
            self._clear_students(
                "Chọn đầy đủ ngữ cảnh để tải danh sách học sinh."
            )
            return False

        try:
            reader = getattr(
                self.score_service,
                "list_score_roster",
                None,
            )
            if callable(reader):
                rows = reader(
                    context.class_id,
                    context.school_year_id,
                    context.subject_id,
                    context.assessment_id,
                )
                self.set_score_rows(rows)
            else:
                enrollments = (
                    self.enrollment_service.list_class_enrollments(
                        context.class_id,
                        context.school_year_id,
                    )
                )
                self.set_students(enrollments)
        except Exception as exc:
            self._clear_students(
                "Không thể tải danh sách học sinh."
            )
            self.context_status_label.setText(
                self._error_message(exc)
            )
            return False

        if self._score_rows:
            self.context_status_label.setText(
                f"{len(self._score_rows)} học sinh trong lớp."
            )
        else:
            self.context_status_label.setText(
                "Lớp chưa có học sinh."
            )
        return True

    def set_students(
        self,
        enrollments: Iterable[EnrollmentListItem],
    ) -> None:
        self._enrollments = tuple(enrollments)
        self._render_score_rows(
            tuple(
                ScoreRosterItem(
                    enrollment_id=item.enrollment_id,
                    student_id=item.student_id,
                    student_code=item.student_code,
                    full_name=item.full_name,
                    assessment_id=(
                        self.current_context().assessment_id or 0
                    ),
                    score_id=None,
                    score=None,
                )
                for item in self._enrollments
            )
        )

    def set_score_rows(
        self,
        rows: Iterable[ScoreRosterItem],
    ) -> None:
        self._enrollments = ()
        self._render_score_rows(tuple(rows))

    def _render_score_rows(
        self,
        rows: tuple[ScoreRosterItem, ...],
    ) -> None:
        self._score_rows = rows
        self._saved_enrollment_ids.clear()

        self.score_table.blockSignals(True)
        self.score_table.setRowCount(len(self._score_rows))

        for row, item in enumerate(self._score_rows):
            number_item = QTableWidgetItem(str(row + 1))
            number_item.setData(
                Qt.ItemDataRole.UserRole,
                item.enrollment_id,
            )
            code_item = QTableWidgetItem(item.student_code)
            name_item = QTableWidgetItem(item.full_name)
            score_item = QTableWidgetItem(
                str(item.score) if item.score is not None else ""
            )
            score_item.setData(
                Qt.ItemDataRole.UserRole,
                item.score_id,
            )
            status_item = QTableWidgetItem(
                "Đã có điểm"
                if item.score_id is not None
                else "Chưa có điểm"
            )

            for read_only_item in (
                number_item,
                code_item,
                name_item,
                status_item,
            ):
                read_only_item.setFlags(
                    read_only_item.flags()
                    & ~Qt.ItemFlag.ItemIsEditable
                )
            if item.score_id is not None:
                score_item.setFlags(
                    score_item.flags()
                    & ~Qt.ItemFlag.ItemIsEditable
                )
                self._saved_enrollment_ids.add(item.enrollment_id)

            self.score_table.setItem(row, 0, number_item)
            self.score_table.setItem(row, 1, code_item)
            self.score_table.setItem(row, 2, name_item)
            self.score_table.setItem(row, 3, score_item)
            self.score_table.setItem(row, 4, status_item)

        self.score_table.blockSignals(False)
        has_students = bool(self._score_rows)
        self.placeholder_label.setVisible(not has_students)
        self.score_table.setVisible(has_students)
        if not has_students:
            self.placeholder_label.setText(
                "Lớp chưa có học sinh."
            )
        self._update_save_state()

    def save_scores(self) -> bool:
        context = self.current_context()
        if (
            not context.is_complete
            or self.score_service is None
            or not self._score_rows
        ):
            self._update_save_state()
            return False

        try:
            entries = self._score_entries(context.assessment_id)
        except (InvalidOperation, ValueError):
            self.context_status_label.setText(
                "Điểm nhập vào không hợp lệ."
            )
            return False

        if not entries:
            self._update_save_state()
            return False

        try:
            save_score_batch(self.score_service, entries)
        except Exception as exc:
            self.context_status_label.setText(
                self._error_message(exc)
            )
            return False

        saved_ids = {
            entry.enrollment_id
            for entry in entries
        }
        reader = getattr(
            self.score_service,
            "list_score_roster",
            None,
        )
        refreshed = True
        if callable(reader):
            refreshed = self.load_students()
        else:
            self._saved_enrollment_ids.update(saved_ids)
            self.score_table.blockSignals(True)
            for row in range(self.score_table.rowCount()):
                enrollment_id = self.enrollment_id_at_row(row)
                if enrollment_id not in saved_ids:
                    continue
                score_item = self.score_table.item(row, 3)
                score_item.setFlags(
                    score_item.flags()
                    & ~Qt.ItemFlag.ItemIsEditable
                )
                self.score_table.item(row, 4).setText(
                    "Đã có điểm"
                )
            self.score_table.blockSignals(False)

        if refreshed:
            self.context_status_label.setText(
                f"Đã lưu {len(entries)} điểm."
            )
        else:
            self.context_status_label.setText(
                f"Đã lưu {len(entries)} điểm nhưng không thể tải lại bảng."
            )
        self.scores_saved.emit(len(entries))
        self._update_save_state()
        return True

    def _score_entries(
        self,
        assessment_id: int,
    ) -> tuple[ScoreCreateData, ...]:
        entries: list[ScoreCreateData] = []
        for row in range(self.score_table.rowCount()):
            enrollment_id = self.enrollment_id_at_row(row)
            if enrollment_id in self._saved_enrollment_ids:
                continue

            item = self.score_table.item(row, 3)
            text = item.text().strip() if item is not None else ""
            if not text:
                continue

            entries.append(
                ScoreCreateData(
                    enrollment_id=enrollment_id,
                    assessment_id=assessment_id,
                    score_value=self._parse_score_text(text),
                )
            )
        return tuple(entries)

    @staticmethod
    def _parse_score_text(text: str) -> Decimal:
        value = Decimal(text.replace(",", "."))
        if not value.is_finite():
            raise ValueError("Score must be finite.")
        if value < Decimal("0") or value > Decimal("10"):
            raise ValueError("Score must be between 0 and 10.")
        if value.quantize(Decimal("0.01")) != value:
            raise ValueError("Score supports at most 2 decimal places.")
        return value

    def _update_save_state(self, *_args) -> None:
        can_save = False
        context = self.current_context()
        if (
            context.is_complete
            and self.score_service is not None
            and self._score_rows
        ):
            can_save = any(
                self.enrollment_id_at_row(row)
                not in self._saved_enrollment_ids
                and bool(self.score_table.item(row, 3).text().strip())
                for row in range(self.score_table.rowCount())
            )
        self.save_button.setEnabled(can_save)

    def _clear_students(self, message: str) -> None:
        self._enrollments = ()
        self._score_rows = ()
        self._saved_enrollment_ids.clear()
        self.score_table.blockSignals(True)
        self.score_table.setRowCount(0)
        self.score_table.blockSignals(False)
        self.score_table.setVisible(False)
        self.placeholder_label.setVisible(True)
        self.placeholder_label.setText(
            message
        )
        self.save_button.setEnabled(False)

    def _can_read_scores(self) -> bool:
        return (
            callable(
                getattr(
                    self.score_service,
                    "list_score_roster",
                    None,
                )
            )
            or self.enrollment_service is not None
        )

    @staticmethod
    def _error_message(exc: Exception) -> str:
        message = str(exc).strip()
        return message or "Đã xảy ra lỗi không xác định."
