from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Protocol

from models.dto import (
    Assessment,
    Grade,
    SchoolClass,
    SchoolYear,
    Subject,
    SupportRule,
)
from models.enums import AssessmentStatus


class CatalogServiceContract(Protocol):
    def list_catalog_school_years(self) -> list[SchoolYear]: ...

    def list_catalog_grades(self) -> list[Grade]: ...

    def list_catalog_classes(
        self,
        school_year_id: int,
        grade_id: int | None = None,
    ) -> list[SchoolClass]: ...

    def create_school_year(
        self,
        year_name: str,
        start_date: date,
        end_date: date,
        is_current: bool = False,
    ) -> int: ...

    def update_school_year(
        self,
        school_year_id: int,
        year_name: str,
        start_date: date,
        end_date: date,
        is_current: bool,
    ) -> None: ...

    def create_grade(
        self,
        grade_number: int,
        grade_name: str | None = None,
    ) -> int: ...

    def update_grade_name(
        self,
        grade_id: int,
        grade_name: str | None,
    ) -> None: ...

    def create_class(
        self,
        class_name: str,
        grade_id: int,
        school_year_id: int,
        homeroom_teacher: str | None = None,
        status: str = "ACTIVE",
    ) -> int: ...

    def update_class(
        self,
        class_id: int,
        class_name: str,
        grade_id: int,
        school_year_id: int,
        homeroom_teacher: str | None = None,
        status: str = "ACTIVE",
    ) -> None: ...

    def set_class_active(
        self,
        class_id: int,
        is_active: bool,
    ) -> None: ...

    def list_catalog_subjects(self) -> list[Subject]: ...

    def create_subject(
        self,
        subject_code: str,
        subject_name: str,
        is_active: bool = True,
    ) -> int: ...

    def update_subject(
        self,
        subject_id: int,
        subject_code: str,
        subject_name: str,
        is_active: bool,
    ) -> None: ...

    def set_subject_active(self, subject_id: int, is_active: bool) -> None: ...

    def list_assessments(
        self,
        school_year_id: int,
        subject_id: int | None = None,
        semester: int | None = None,
        status: AssessmentStatus | None = None,
    ) -> list[Assessment]: ...

    def create_assessment(
        self,
        subject_id: int,
        school_year_id: int,
        assessment_name: str,
        semester: int | None,
        assessment_type: str | None,
        assessment_date: date | None,
    ) -> Assessment: ...

    def update_assessment(
        self,
        assessment_id: int,
        subject_id: int,
        school_year_id: int,
        assessment_name: str,
        semester: int | None,
        assessment_type: str | None,
        assessment_date: date | None,
        status: AssessmentStatus,
    ) -> None: ...

    def set_assessment_active(
        self,
        assessment_id: int,
        is_active: bool,
    ) -> None: ...

    def list_catalog_support_rules(
        self,
        school_year_id: int,
        subject_id: int | None = None,
    ) -> list[SupportRule]: ...

    def create_support_rule(
        self,
        subject_id: int,
        school_year_id: int,
        threshold: Decimal,
        is_active: bool = True,
    ) -> SupportRule: ...

    def update_support_rule_threshold(
        self,
        rule_id: int,
        threshold: Decimal,
    ) -> SupportRule: ...

    def set_support_rule_active(
        self,
        rule_id: int,
        is_active: bool,
    ) -> SupportRule: ...
