from __future__ import annotations


STATUS_LABELS = {
    "DETECTED": "Mới phát hiện",
    "PLANNED": "Đã lập kế hoạch",
    "IN_PROGRESS": "Đang bổ trợ",
    "WAITING_REVIEW": "Chờ đánh giá",
    "CONTINUE": "Cần tiếp tục",
    "COMPLETED": "Đã đạt ngưỡng",
}

REVIEW_RESULT_LABELS = {
    "PASSED": "Đạt",
    "NOT_PASSED": "Chưa đạt",
}


def status_label(status: str | None) -> str:
    if status is None:
        return "-"
    return STATUS_LABELS.get(status, status)


def review_result_label(result: str | None) -> str:
    if result is None:
        return "-"
    return REVIEW_RESULT_LABELS.get(result, result)
