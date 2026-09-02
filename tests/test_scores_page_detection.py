import inspect
import os
from dataclasses import replace
from datetime import date, datetime
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from models.dto import Assessment, ScoreBatchDetectionResult, ScoreRosterItem
from models.enums import AssessmentStatus
from ui.pages.scores_page import ScoresPage, save_score_batch


class AcademicStub:
    def list_school_years(self):
        return [(2, "2026-2027", None, None, True)]

    def list_grades(self):
        return [(6, 6, "Khối 6")]

    def list_classes_by_school_year(self, _year_id):
        return [(61, "6A1", 6, None, True)]

    def list_active_subjects(self):
        return [(11, "M1", "Môn 1")]

    def list_assessments(self, school_year_id, subject_id=None):
        return [Assessment(
            101, subject_id, school_year_id, "Giữa kỳ", 1, "MIDTERM",
            date(2026, 10, 1), AssessmentStatus.ACTIVE,
            datetime(2026, 9, 1),
        )]


class DetectionWriter:
    def __init__(self):
        self.rows = [
            ScoreRosterItem(71, "s1", "HS1", "Học sinh 1", 101, None, None),
            ScoreRosterItem(72, "s2", "HS2", "Học sinh 2", 101, None, None),
        ]
        self.detection_calls = []
        self.legacy_calls = []
        self.read_calls = 0

    def list_score_roster(self, *_context):
        self.read_calls += 1
        return self.rows

    def create_scores_and_detect(self, entries):
        batch = tuple(entries)
        self.detection_calls.append(batch)
        values = {item.enrollment_id: item.score_value for item in batch}
        self.rows = [
            replace(
                row,
                score_id=900 + index,
                score=values[row.enrollment_id],
            ) if row.enrollment_id in values else row
            for index, row in enumerate(self.rows)
        ]
        return ScoreBatchDetectionResult((), (object(),))

    def create_scores(self, entries):
        self.legacy_calls.append(tuple(entries))
        raise AssertionError("legacy create path must not be used")


def select(combo, value):
    combo.setCurrentIndex(combo.findData(value))


def make_page(service):
    QApplication.instance() or QApplication([])
    page = ScoresPage(AcademicStub(), score_service=service)
    page.initialize_scores()
    select(page.grade_combo, 6)
    select(page.class_combo, 61)
    select(page.subject_combo, 11)
    select(page.assessment_combo, 101)
    return page


def test_save_helper_prefers_detection_aware_batch_api():
    service = DetectionWriter()
    result = save_score_batch(service, ())
    assert isinstance(result, ScoreBatchDetectionResult)
    assert len(service.detection_calls) == 1
    assert service.legacy_calls == []


def test_page_save_uses_detection_path_refreshes_and_reports_count():
    service = DetectionWriter()
    page = make_page(service)
    page.score_table.item(0, 3).setText("2.50")
    page.score_table.item(1, 3).setText("8.00")

    assert page.save_scores() is True

    assert len(service.detection_calls) == 1
    assert service.legacy_calls == []
    assert service.read_calls == 2
    assert page.score_table.item(0, 3).text() == "2.50"
    assert page.score_table.item(1, 3).text() == "8.00"
    assert "Có 1 học sinh" in page.context_status_label.text()


def test_ui_has_no_threshold_or_support_business_logic():
    source = inspect.getsource(ScoresPage).upper()
    assert "THRESHOLD" not in source
    assert "SUPPORTSERVICE" not in source
    assert "SUPPORT_RULE" not in source
    assert "< 3.5" not in source
