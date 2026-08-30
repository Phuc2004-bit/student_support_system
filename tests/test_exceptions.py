import pytest

from exceptions import (
    AppError,
    BusinessRuleError,
    DuplicateError,
    InvalidStateTransitionError,
    MissingSupportRuleError,
    ValidationError,
)


def test_validation_error_is_app_error():
    assert issubclass(ValidationError, AppError)


def test_duplicate_error_is_app_error():
    assert issubclass(DuplicateError, AppError)


def test_business_rule_error_is_app_error():
    assert issubclass(BusinessRuleError, AppError)


def test_invalid_state_transition_is_business_rule_error():
    assert issubclass(
        InvalidStateTransitionError,
        BusinessRuleError,
    )


def test_missing_support_rule_is_business_rule_error():
    assert issubclass(
        MissingSupportRuleError,
        BusinessRuleError,
    )


def test_exception_message_is_preserved():
    message = "Mã học sinh đã tồn tại."

    with pytest.raises(DuplicateError) as exc_info:
        raise DuplicateError(message)

    assert str(exc_info.value) == message