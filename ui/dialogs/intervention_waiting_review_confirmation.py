from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from services.support_contract import (
    InterventionWaitingReviewServiceContract,
)


def confirm_ready_for_review(
    parent: QWidget,
    service: InterventionWaitingReviewServiceContract,
    intervention_id: int,
) -> bool:
    answer = QMessageBox.question(
        parent,
        "Chuyển chờ đánh giá",
        "Chuyển hồ sơ này sang trạng thái chờ đánh giá?",
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        return False

    service.mark_waiting_review(intervention_id)
    return True
