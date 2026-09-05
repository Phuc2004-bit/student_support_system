from __future__ import annotations

from datetime import date
from typing import Protocol

from models.dto import Grade, SchoolClass, SchoolYear


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
