class AssistantError(Exception):
    """Base error for the read-only chat assistant boundary."""


class AssistantValidationError(AssistantError):
    """The assistant request is invalid but safe to report to the UI."""


class ProviderError(AssistantError):
    """An assistant provider could not produce a safe response."""


class ProviderAuthenticationError(ProviderError):
    """Online provider rejected its configured authentication."""


class ProviderTransientError(ProviderError):
    """Online provider failed for a retryable or temporary reason."""


class ProviderResponseError(ProviderError):
    """Online provider returned no usable plain-text response."""


class KnowledgeBaseError(AssistantError):
    """Static application guidance could not be read."""
