from datetime import date
from decimal import Decimal

from models.dto.dashboard_dto import (
    DashboardAttentionItem,
    DashboardData,
    DashboardStatusItem,
    DashboardSummary,
)


def test_dashboard_summary_contains_six_kpis():
    summary = DashboardSummary(
        total_students=1000,
        needs_support_count=120,
        in_progress_count=55,
        waiting_review_count=20,
        completed_count=35,
        continue_count=10,
    )

    assert summary.total_students == 1000
    assert summary.needs_support_count == 120
    assert summary.in_progress_count == 55
    assert summary.waiting_review_count == 20
    assert summary.completed_count == 35
    assert summary.continue_count == 10


def test_dashboard_status_item_is_immutable():
    item = DashboardStatusItem(
        status="IN_PROGRESS",
        count=12,
    )

    assert item.status == "IN_PROGRESS"
    assert item.count == 12


def test_dashboard_attention_item_keeps_student_and_support_context():
    item = DashboardAttentionItem(
        intervention_id=101,
        student_code="HS001",
        full_name="Nguyễn Văn A",
        grade_number=10,
        class_name="10A1",
        subject_code="TOAN",
        subject_name="Toán",
        status="WAITING_REVIEW",
        detected_date=date(2026, 9, 1),
        trigger_score=Decimal("2.80"),
        latest_review_score=Decimal("3.20"),
    )

    assert item.intervention_id == 101
    assert item.student_code == "HS001"
    assert item.grade_number == 10
    assert item.subject_code == "TOAN"
    assert item.status == "WAITING_REVIEW"
    assert item.trigger_score == Decimal("2.80")
    assert item.latest_review_score == Decimal("3.20")


def test_dashboard_data_groups_summary_breakdown_and_attention_items():
    summary = DashboardSummary(
        total_students=100,
        needs_support_count=20,
        in_progress_count=8,
        waiting_review_count=4,
        completed_count=6,
        continue_count=2,
    )

    breakdown = (
        DashboardStatusItem(
            status="IN_PROGRESS",
            count=8,
        ),
        DashboardStatusItem(
            status="WAITING_REVIEW",
            count=4,
        ),
    )

    attention = (
        DashboardAttentionItem(
            intervention_id=1,
            student_code="HS001",
            full_name="Học sinh A",
            grade_number=9,
            class_name="9A1",
            subject_code="VAN",
            subject_name="Ngữ văn",
            status="WAITING_REVIEW",
            detected_date=date(2026, 9, 1),
            trigger_score=Decimal("3.00"),
        ),
    )

    data = DashboardData(
        summary=summary,
        status_breakdown=breakdown,
        attention_items=attention,
    )

    assert data.summary is summary
    assert data.status_breakdown == breakdown
    assert data.attention_items == attention
