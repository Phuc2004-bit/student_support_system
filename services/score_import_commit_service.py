from __future__ import annotations

from exceptions import AppError, DatabaseError, ScoreImportError, ValidationError
from models.dto import ScoreCreateData
from models.dto.score_import import (
    ScoreImportPreview,
    ScoreImportTransactionResult,
)
from services.score_import_preview_service import ScoreImportPreviewService
from services.score_service import ScoreService


class ScoreImportCommitService:
    """Atomically persist a validated preview and run canonical detection."""

    def __init__(
        self,
        db,
        preview_service: ScoreImportPreviewService | None = None,
        score_service: ScoreService | None = None,
    ) -> None:
        self.db = db
        self.preview_service = preview_service or ScoreImportPreviewService(db)
        self.score_service = score_service or ScoreService(db)

    def commit_import(
        self,
        preview: ScoreImportPreview,
    ) -> ScoreImportTransactionResult:
        entries = self._validate_and_build_batch(preview)
        try:
            with self.db.transaction() as connection:
                self.preview_service._revalidate_preview(connection, preview)
                batch = self.score_service._create_scores_and_detect(
                    connection, entries
                )
        except AppError:
            raise
        except Exception as exc:
            raise DatabaseError(
                "Không thể hoàn tất import điểm. Toàn bộ thay đổi đã được hủy."
            ) from exc

        created_score_ids = tuple(score.score_id for score in batch.scores)
        created_score_id_set = set(created_score_ids)
        created_interventions = tuple(
            intervention
            for intervention in batch.interventions
            if intervention.trigger_score_id in created_score_id_set
        )
        return ScoreImportTransactionResult(
            assessment_id=preview.context.assessment_id,
            imported_count=len(batch.scores),
            intervention_created_count=len(created_interventions),
            score_ids=created_score_ids,
            intervention_ids=tuple(
                intervention.intervention_id
                for intervention in created_interventions
            ),
        )

    @staticmethod
    def _validate_and_build_batch(
        preview: ScoreImportPreview,
    ) -> tuple[ScoreCreateData, ...]:
        if not isinstance(preview, ScoreImportPreview) or not preview.can_commit:
            raise ScoreImportError(
                "Preview không hợp lệ hoặc có dòng lỗi; không thể import."
            )
        try:
            return ScoreService.normalize_score_batch(
                ScoreCreateData(
                    enrollment_id=row.enrollment_id,
                    assessment_id=preview.context.assessment_id,
                    score_value=row.normalized_score,
                )
                for row in preview.rows
            )
        except ValidationError as exc:
            raise ScoreImportError(
                "Preview chứa dữ liệu không hợp lệ; vui lòng preview lại."
            ) from exc
