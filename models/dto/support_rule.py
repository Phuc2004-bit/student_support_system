from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class SupportRule:
    rule_id: int
    subject_id: int
    school_year_id: int
    threshold: Decimal
    is_active: bool
    created_at: datetime
    updated_at: datetime