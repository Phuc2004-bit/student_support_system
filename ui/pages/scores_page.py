from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.dto.enrollment import EnrollmentListItem
from models.dto.score import ScoreCreateData, ScoreRosterItem
from models.dto.score_import import ScoreImportContext, ScoreImportTemplateStudent
from models.dto.data_export import ScoreExportContext
from services.data_export_contract import ScoreExportServiceContract
from ui.action_permissions import action_is_allowed, apply_action_permission
from services.enrollment_contract import EnrollmentServiceContract
from services.score_contract import (
    ScoreServiceContract as ScoreWriterContract,
)
from ui.widgets.score_context_filter_widget import (
    ScoreContextFilterWidget,
    ScoreContextSelection,
)
from ui.dialogs.score_import_preview_dialog import ScoreImportPreviewDialog
from ui.theme import (
    SIDEBAR_BACKGROUND,
    TEXT_PRIMARY,
    scores_page_stylesheet,
    status_badge_colors,
)


def save_score_batch(
    service: ScoreWriterContract,
    entries: tuple[ScoreCreateData, ...],
):
    detection_writer = getattr(
        service,
        "create_scores_and_detect",
        None,
    )
    if callable(detection_writer):
        return detection_writer(entries)
    return service.create_scores(entries)


def detected_support_count(save_result) -> int:
    return getattr(
        save_result,
        "detected_intervention_count",
        0,
    )


def imported_support_case_count(import_result) -> int:
    return getattr(import_result, "intervention_created_count", 0)


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
        score_import_parser=None,
        score_import_template_service=None,
        score_import_preview_service=None,
        score_import_commit_service=None,
        parent=None,
        score_export_service: ScoreExportServiceContract | None = None,
        excel_permission_check=None,
    ):
        super().__init__(parent)
        self.academic_service = academic_service
        self.enrollment_service = enrollment_service
        self.score_service = score_service
        self.score_import_parser = score_import_parser
        self.score_import_template_service = score_import_template_service
        self.score_import_preview_service = score_import_preview_service
        self.score_import_commit_service = score_import_commit_service
        self.score_export_service = score_export_service
        self.excel_permission_check = excel_permission_check
        self._enrollments: tuple[EnrollmentListItem, ...] = ()
        self._score_rows: tuple[ScoreRosterItem, ...] = ()
        self._saved_enrollment_ids: set[int] = set()
        self._editing_row: int | None = None
        self._original_score_text = ""
        self.setObjectName("scoresPage")
        self._build_ui()
        self.setStyleSheet(scores_page_stylesheet())
        for button in (
            self.download_template_button,
            self.import_excel_button,
            self.export_button,
        ):
            apply_action_permission(button, self.excel_permission_check)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 24)
        root.setSpacing(14)

        self.title_label = QLabel("Điểm & Đánh giá", self)
        self.subtitle_label = QLabel(
            "Quản lý kết quả đánh giá của học sinh",
            self,
        )
        self.title_label.setVisible(False)
        self.subtitle_label.setVisible(False)

        self.toolbar_card = QFrame(self)
        self.toolbar_card.setObjectName("scoresToolbarCard")
        toolbar_layout = QVBoxLayout(self.toolbar_card)
        toolbar_layout.setContentsMargins(16, 14, 16, 14)
        toolbar_layout.setSpacing(12)

        self.context_filter = ScoreContextFilterWidget(
            academic_service=self.academic_service,
            parent=self.toolbar_card,
        )
        toolbar_layout.addWidget(self.context_filter)

        import_actions = QHBoxLayout()
        import_actions.setSpacing(10)
        self.export_button = QPushButton("Xuất Excel", self)
        self.export_button.setObjectName("exportScoresExcelButton")
        self.download_template_button = QPushButton("Tải file mẫu", self)
        self.download_template_button.setObjectName(
            "downloadScoreImportTemplateButton"
        )
        self.import_excel_button = QPushButton("Nhập điểm từ Excel", self)
        self.import_excel_button.setObjectName("importScoresFromExcelButton")
        import_actions.addWidget(self.import_excel_button)
        import_actions.addWidget(self.download_template_button)
        import_actions.addWidget(self.export_button)
        import_actions.addStretch(1)
        self.import_excel_button.setProperty("variant", "primary")
        self.download_template_button.setProperty("variant", "secondary")
        self.export_button.setProperty("variant", "secondary")
        toolbar_layout.addLayout(import_actions)
        root.addWidget(self.toolbar_card)

        self.school_year_combo = self.context_filter.school_year_combo
        self.grade_combo = self.context_filter.grade_combo
        self.class_combo = self.context_filter.class_combo
        self.subject_combo = self.context_filter.subject_combo
        self.assessment_combo = self.context_filter.assessment_combo

        self.assessment_info_card = QFrame(self)
        self.assessment_info_card.setObjectName("assessmentInfoCard")
        assessment_layout = QHBoxLayout(self.assessment_info_card)
        assessment_layout.setContentsMargins(16, 11, 16, 11)
        assessment_layout.setSpacing(14)
        assessment_text = QVBoxLayout()
        assessment_text.setSpacing(3)
        self.assessment_caption_label = QLabel(
            "BÀI ĐÁNH GIÁ ĐANG CHỌN",
            self.assessment_info_card,
        )
        self.assessment_caption_label.setObjectName("assessmentInfoCaption")
        self.assessment_name_label = QLabel(
            "Chưa chọn bài đánh giá",
            self.assessment_info_card,
        )
        self.assessment_name_label.setObjectName("assessmentInfoName")
        self.assessment_meta_label = QLabel("—", self.assessment_info_card)
        self.assessment_meta_label.setObjectName("assessmentInfoMeta")
        assessment_text.addWidget(self.assessment_caption_label)
        assessment_text.addWidget(self.assessment_name_label)
        assessment_text.addWidget(self.assessment_meta_label)
        assessment_layout.addLayout(assessment_text, 1)
        self.assessment_status_label = QLabel("Chưa chọn", self.assessment_info_card)
        self.assessment_status_label.setObjectName("assessmentStatusBadge")
        self.assessment_status_label.setProperty("assessmentStatus", "NONE")
        assessment_layout.addWidget(
            self.assessment_status_label,
            0,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        )
        root.addWidget(self.assessment_info_card)

        self.score_table_placeholder = QFrame(self)
        self.score_table_placeholder.setObjectName(
            "scoreTablePlaceholder"
        )
        placeholder_layout = QVBoxLayout(
            self.score_table_placeholder
        )
        placeholder_layout.setContentsMargins(16, 12, 16, 16)
        placeholder_layout.setSpacing(10)

        table_header = QHBoxLayout()
        table_header.setSpacing(9)
        self.score_table_caption = QLabel(
            "Danh sách học sinh & điểm",
            self.score_table_placeholder,
        )
        self.score_table_caption.setObjectName("scoreTableCaption")
        table_header.addWidget(self.score_table_caption)
        table_header.addStretch(1)
        self.unsaved_label = QLabel(
            "Có thay đổi chưa lưu",
            self.score_table_placeholder,
        )
        self.unsaved_label.setObjectName("scoreUnsavedState")
        self.unsaved_label.setVisible(False)
        table_header.addWidget(self.unsaved_label)

        self.edit_button = QPushButton("Sửa", self)
        self.edit_button.setEnabled(False)
        self.cancel_edit_button = QPushButton("Hủy sửa", self)
        self.cancel_edit_button.setEnabled(False)
        self.update_button = QPushButton("Lưu thay đổi", self)
        self.update_button.setEnabled(False)
        self.save_button = QPushButton("Lưu điểm", self)
        self.save_button.setEnabled(False)
        self.update_button.setProperty("variant", "primary")
        self.save_button.setProperty("variant", "primary")
        self.edit_button.setProperty("variant", "secondary")
        self.cancel_edit_button.setProperty("variant", "secondary")
        table_header.addWidget(self.edit_button)
        table_header.addWidget(self.cancel_edit_button)
        table_header.addWidget(self.update_button)
        table_header.addWidget(self.save_button)
        placeholder_layout.addLayout(table_header)

        self.context_status_label = QLabel(self)
        self.context_status_label.setObjectName("scoreContextStatus")
        self.context_status_label.setWordWrap(True)
        placeholder_layout.addWidget(self.context_status_label)

        self.placeholder_label = QLabel(
            "Chọn bài đánh giá để xem hoặc nhập điểm.",
            self.score_table_placeholder,
        )
        self.placeholder_label.setObjectName("scoreEmptyTitle")
        self.placeholder_label.setWordWrap(True)
        self.placeholder_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        placeholder_layout.addWidget(self.placeholder_label)

        self.score_table = QTableWidget(
            self.score_table_placeholder
        )
        self.score_table.setObjectName("scoreEntryTable")
        self.score_table.setColumnCount(len(self.TABLE_HEADERS))
        self.score_table.setHorizontalHeaderLabels(
            self.TABLE_HEADERS
        )
        self.score_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.score_table.setAlternatingRowColors(True)
        self.score_table.setShowGrid(False)
        self.score_table.setWordWrap(False)
        self.score_table.verticalHeader().setVisible(False)
        self.score_table.verticalHeader().setDefaultSectionSize(40)
        header = self.score_table.horizontalHeader()
        header.setMinimumHeight(42)
        header.setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        header.setSectionResizeMode(
            2,
            QHeaderView.ResizeMode.Stretch,
        )
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.score_table.setColumnWidth(3, 110)
        placeholder_layout.addWidget(self.score_table, 1)
        root.addWidget(self.score_table_placeholder, 1)

        self.context_filter.context_changed.connect(
            self._on_context_changed
        )
        self.score_table.itemChanged.connect(
            self._update_save_state
        )
        self.score_table.itemSelectionChanged.connect(
            self._update_edit_state
        )
        self.edit_button.clicked.connect(
            lambda _checked=False: self.begin_edit_selected_score()
        )
        self.cancel_edit_button.clicked.connect(
            lambda _checked=False: self.cancel_score_edit()
        )
        self.update_button.clicked.connect(
            lambda _checked=False: self.save_score_edit()
        )
        self.save_button.clicked.connect(
            lambda _checked=False: self.save_scores()
        )
        self.download_template_button.clicked.connect(
            lambda _checked=False: self.download_import_template()
        )
        self.import_excel_button.clicked.connect(
            lambda _checked=False: self.import_scores_from_excel()
        )
        self.export_button.clicked.connect(
            lambda _checked=False: self.export_scores()
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

    def score_import_context(self) -> ScoreImportContext | None:
        selected = self.current_context()
        if not selected.is_complete:
            self.context_status_label.setText(
                "Vui lòng chọn đầy đủ năm học, khối, lớp, môn học và bài đánh giá."
            )
            return None
        return ScoreImportContext(
            school_year_id=selected.school_year_id,
            school_year_name=self.school_year_combo.currentText(),
            class_id=selected.class_id,
            class_name=self.class_combo.currentText(),
            subject_id=selected.subject_id,
            subject_name=self.subject_combo.currentText(),
            assessment_id=selected.assessment_id,
            assessment_name=self.assessment_combo.currentText(),
        )

    def score_export_context(self) -> ScoreExportContext | None:
        selected = self.current_context()
        if not selected.is_complete:
            self.context_status_label.setText(
                "Vui lòng chọn đầy đủ năm học, khối, lớp, môn học và bài đánh giá."
            )
            return None
        return ScoreExportContext(
            school_year_id=selected.school_year_id,
            school_year_name=self.school_year_combo.currentText(),
            class_id=selected.class_id,
            class_name=self.class_combo.currentText(),
            subject_id=selected.subject_id,
            subject_name=self.subject_combo.currentText(),
            assessment_id=selected.assessment_id,
            assessment_name=self.assessment_combo.currentText(),
        )

    def export_scores(self) -> bool:
        if not action_is_allowed(self.excel_permission_check):
            self._show_export_error("Bạn không có quyền xuất bảng điểm.")
            return False
        context = self.score_export_context()
        if context is None:
            return False
        if self.score_export_service is None:
            self._show_export_error("Chưa có dịch vụ xuất bảng điểm.")
            return False
        output_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Xuất bảng điểm",
            "bang_diem.xlsx",
            "Excel Workbook (*.xlsx)",
        )
        if not output_path:
            return False
        if not output_path.lower().endswith(".xlsx"):
            output_path += ".xlsx"
        try:
            self.score_export_service.export_xlsx(context, output_path)
        except Exception as exc:
            self._show_export_error(self._error_message(exc))
            return False
        QMessageBox.information(
            self,
            "Xuất Excel",
            "Đã xuất bảng điểm thành công.",
        )
        return True

    def _show_export_error(self, message: str) -> None:
        self.context_status_label.setText(message)
        QMessageBox.warning(self, "Xuất bảng điểm", message)

    def download_import_template(self) -> bool:
        if not action_is_allowed(self.excel_permission_check):
            self._show_import_error(
                "Bạn không có quyền tải file mẫu nhập điểm."
            )
            return False
        context = self.score_import_context()
        if context is None:
            return False
        if self.enrollment_service is None or self.score_import_template_service is None:
            self._show_import_error("Chưa có dịch vụ tạo file mẫu nhập điểm.")
            return False
        output_path, _selected_filter = QFileDialog.getSaveFileName(
            self,
            "Lưu file mẫu nhập điểm",
            "mau_nhap_diem.xlsx",
            "Excel Workbook (*.xlsx)",
        )
        if not output_path:
            return False
        try:
            roster = self.enrollment_service.list_class_enrollments(
                context.class_id, context.school_year_id
            )
            template_students = tuple(
                ScoreImportTemplateStudent(item.student_id, item.full_name)
                for item in roster
            )
            self.score_import_template_service.create_template(
                context, template_students, output_path
            )
        except Exception as exc:
            self._show_import_error(self._error_message(exc))
            return False
        QMessageBox.information(
            self, "Tải file mẫu", "Đã tạo file mẫu nhập điểm thành công."
        )
        return True

    def import_scores_from_excel(self) -> bool:
        if not action_is_allowed(self.excel_permission_check):
            self._show_import_error(
                "Bạn không có quyền nhập điểm từ Excel."
            )
            return False
        context = self.score_import_context()
        if context is None:
            return False
        if (
            self.score_import_parser is None
            or self.score_import_preview_service is None
            or self.score_import_commit_service is None
        ):
            self._show_import_error("Chưa có đầy đủ dịch vụ nhập điểm Excel.")
            return False
        file_path, _selected_filter = QFileDialog.getOpenFileName(
            self,
            "Chọn file nhập điểm",
            "",
            "Excel Workbook (*.xlsx)",
        )
        if not file_path:
            return False
        try:
            workbook = self.score_import_parser.parse_workbook(file_path)
            preview = self.score_import_preview_service.preview_import(
                context, workbook
            )
        except Exception as exc:
            self._show_import_error(self._error_message(exc))
            return False

        dialog = ScoreImportPreviewDialog(preview, self)
        if dialog.exec() != ScoreImportPreviewDialog.DialogCode.Accepted:
            return False
        if not preview.can_commit:
            self._show_import_error(
                "Preview có dòng lỗi; không thể nhập một phần dữ liệu."
            )
            return False
        answer = QMessageBox.question(
            self,
            "Xác nhận nhập điểm",
            f"Nhập {preview.valid_count} điểm vào hệ thống?\n"
            "Thao tác sẽ được thực hiện toàn bộ hoặc không ghi dữ liệu nếu có lỗi.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return False
        if not action_is_allowed(self.excel_permission_check):
            self._show_import_error(
                "Phiên đăng nhập không còn quyền nhập điểm từ Excel."
            )
            return False
        try:
            result = self.score_import_commit_service.commit_import(preview)
        except Exception as exc:
            self._show_import_error(self._error_message(exc))
            return False

        refreshed = self.load_students()
        message = (
            f"Đã nhập {result.imported_count} điểm.\n"
            f"Phát hiện {imported_support_case_count(result)} ca cần bổ trợ."
        )
        self.context_status_label.setText(message.replace("\n", " "))
        QMessageBox.information(self, "Nhập điểm thành công", message)
        self.scores_saved.emit(result.imported_count)
        return refreshed

    def _show_import_error(self, message: str) -> None:
        self.context_status_label.setText(message)
        QMessageBox.warning(self, "Nhập điểm Excel", message)

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
        self._render_assessment_info()
        if context.is_complete:
            self.context_status_label.setText(
                "Đã chọn đầy đủ ngữ cảnh."
            )
            if self._can_read_scores():
                self.load_students()
            return

        self._clear_students(
            "Chọn bài đánh giá để xem hoặc nhập điểm."
        )
        self.context_status_label.setText(
            "Vui lòng chọn năm học, khối, lớp, môn học "
            "và bài đánh giá."
        )

    def load_students(self) -> bool:
        context = self.current_context()
        if not context.is_complete or not self._can_read_scores():
            self._clear_students(
                "Chọn bài đánh giá để xem hoặc nhập điểm."
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
                "Chưa có học sinh trong phạm vi đã chọn."
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
        self._editing_row = None
        self._original_score_text = ""

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

            for centered_item in (
                number_item,
                code_item,
                score_item,
                status_item,
            ):
                centered_item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )
            foreground, background = status_badge_colors(
                "ACTIVE" if item.score_id is not None else "INACTIVE"
            )
            status_item.setForeground(QColor(foreground))
            status_item.setBackground(QColor(background))
            if item.score_id is None:
                score_item.setForeground(QColor(TEXT_PRIMARY))
                score_item.setBackground(QColor(SIDEBAR_BACKGROUND))

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
                "Chưa có học sinh trong phạm vi đã chọn."
            )
        self._update_save_state()
        self._update_edit_state()

    def begin_edit_selected_score(self) -> bool:
        row = self.score_table.currentRow()
        score_id = self.score_id_at_row(row)
        if score_id is None or self.score_service is None:
            self._update_edit_state()
            return False

        checker = getattr(self.score_service, "can_edit_score", None)
        try:
            if callable(checker) and not checker(score_id):
                self.context_status_label.setText(
                    "Không thể sửa điểm đã được sử dụng trong lịch sử bổ trợ."
                )
                return False
        except Exception as exc:
            self.context_status_label.setText(self._error_message(exc))
            return False

        item = self.score_table.item(row, 3)
        self._editing_row = row
        self._original_score_text = item.text()
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        self.score_table.editItem(item)
        self._update_edit_state()
        return True

    def cancel_score_edit(self) -> bool:
        if self._editing_row is None:
            return False
        row = self._editing_row
        item = self.score_table.item(row, 3)
        self.score_table.blockSignals(True)
        item.setText(self._original_score_text)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.score_table.blockSignals(False)
        self._editing_row = None
        self._original_score_text = ""
        self.context_status_label.setText("Đã hủy chỉnh sửa điểm.")
        self._update_save_state()
        self._update_edit_state()
        return True

    def save_score_edit(self) -> bool:
        if self._editing_row is None or self.score_service is None:
            return False
        row = self._editing_row
        score_id = self.score_id_at_row(row)
        item = self.score_table.item(row, 3)
        try:
            score_value = self._parse_score_text(item.text().strip())
            self.score_service.update_score(score_id, score_value)
        except (InvalidOperation, ValueError):
            self.context_status_label.setText(
                "Điểm nhập vào không hợp lệ."
            )
            return False
        except Exception as exc:
            self.context_status_label.setText(self._error_message(exc))
            return False

        self._editing_row = None
        self._original_score_text = ""
        refreshed = self.load_students()
        if refreshed:
            self.context_status_label.setText("Đã cập nhật điểm.")
        self._update_edit_state()
        return refreshed

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
            save_result = save_score_batch(self.score_service, entries)
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
            detected_count = detected_support_count(save_result)
            message = f"Đã lưu {len(entries)} điểm."
            if detected_count:
                message += (
                    f" Có {detected_count} học sinh "
                    "được phát hiện cần bổ trợ."
                )
            self.context_status_label.setText(message)
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
        if self._editing_row is not None:
            self.save_button.setEnabled(False)
        self.unsaved_label.setVisible(can_save and self._editing_row is None)

    def _update_edit_state(self) -> None:
        editing = self._editing_row is not None
        selected_score_id = self.score_id_at_row(
            self.score_table.currentRow()
        )
        self.edit_button.setEnabled(
            not editing
            and selected_score_id is not None
            and self.score_service is not None
        )
        self.cancel_edit_button.setEnabled(editing)
        self.update_button.setEnabled(editing)
        if editing:
            self.save_button.setEnabled(False)
            self.unsaved_label.setText("Đang chỉnh sửa điểm đã lưu")
            self.unsaved_label.setVisible(True)
        elif not self.save_button.isEnabled():
            self.unsaved_label.setText("Có thay đổi chưa lưu")
            self.unsaved_label.setVisible(False)

    def _clear_students(self, message: str) -> None:
        self._enrollments = ()
        self._score_rows = ()
        self._saved_enrollment_ids.clear()
        self._editing_row = None
        self._original_score_text = ""
        self.score_table.blockSignals(True)
        self.score_table.setRowCount(0)
        self.score_table.blockSignals(False)
        self.score_table.setVisible(False)
        self.placeholder_label.setVisible(True)
        self.placeholder_label.setText(
            message
        )
        self.save_button.setEnabled(False)
        self.edit_button.setEnabled(False)
        self.cancel_edit_button.setEnabled(False)
        self.update_button.setEnabled(False)
        self.unsaved_label.setText("Có thay đổi chưa lưu")
        self.unsaved_label.setVisible(False)

    def _render_assessment_info(self) -> None:
        assessment = self.context_filter.selected_assessment()
        if assessment is None:
            self.assessment_name_label.setText("Chưa chọn bài đánh giá")
            self.assessment_meta_label.setText(
                "Chọn năm học, lớp và môn học để tiếp tục."
            )
            status_value = "NONE"
            status_text = "Chưa chọn"
        else:
            status_value = str(
                getattr(assessment.status, "value", assessment.status)
            )
            status_text = {
                "ACTIVE": "Đang mở",
                "LOCKED": "Đã khóa",
                "CANCELLED": "Ngừng sử dụng",
            }.get(status_value, status_value)
            assessment_date = getattr(assessment, "assessment_date", None)
            date_text = (
                assessment_date.strftime("%d/%m/%Y")
                if assessment_date is not None
                else "Chưa có ngày"
            )
            assessment_type = getattr(assessment, "assessment_type", None)
            type_text = assessment_type or "Không phân loại"
            self.assessment_name_label.setText(assessment.assessment_name)
            self.assessment_meta_label.setText(
                f"{self.subject_combo.currentText()}  •  {date_text}  •  {type_text}"
            )
        self.assessment_status_label.setText(status_text)
        self.assessment_status_label.setProperty(
            "assessmentStatus",
            status_value,
        )
        self.assessment_status_label.style().unpolish(
            self.assessment_status_label
        )
        self.assessment_status_label.style().polish(
            self.assessment_status_label
        )

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
