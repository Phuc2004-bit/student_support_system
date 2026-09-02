import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from tests.test_scores_page_manual_entry import (
    EnrollmentStub,
    ScoreStub,
    complete_context,
    make_page,
)


def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    "text",
    ["abc", "NaN", "Infinity", "-Infinity", "-0.01", "10.01", "1.234"],
)
def test_invalid_ui_score_keeps_input_editable_and_unsaved(text):
    app()
    scores = ScoreStub()
    page = make_page(EnrollmentStub(), scores)
    complete_context(page)
    cell = page.score_table.item(0, 3)
    cell.setText(text)

    assert page.save_scores() is False
    assert scores.calls == []
    assert cell.text() == text
    assert bool(cell.flags() & Qt.ItemFlag.ItemIsEditable)
    assert page.save_button.isEnabled() is True
    assert page.context_status_label.text() == (
        "Điểm nhập vào không hợp lệ."
    )


def test_service_failure_keeps_page_usable_for_retry():
    app()
    failing = ScoreStub(error=RuntimeError("save unavailable"))
    page = make_page(EnrollmentStub(), failing)
    complete_context(page)
    cell = page.score_table.item(0, 3)
    cell.setText("7.50")

    assert page.save_scores() is False
    assert cell.text() == "7.50"
    assert bool(cell.flags() & Qt.ItemFlag.ItemIsEditable)
    assert page.save_button.isEnabled() is True

    working = ScoreStub()
    page.score_service = working
    assert page.save_scores() is True
    assert len(working.calls) == 1
