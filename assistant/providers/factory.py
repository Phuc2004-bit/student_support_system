from __future__ import annotations

import logging

from assistant.exceptions import ProviderError
from assistant.providers.base import AssistantProvider
from assistant.providers.gemini_provider import GeminiProvider
from assistant.providers.offline_provider import OfflineProvider


LOGGER = logging.getLogger(__name__)


def create_provider(settings: object) -> AssistantProvider:
    """Create one configured provider, falling back safely to offline mode."""
    provider_name = str(getattr(settings, "CHAT_PROVIDER", "offline")).strip().lower()
    if provider_name == "offline":
        return OfflineProvider()
    if provider_name != "gemini":
        LOGGER.warning("Unsupported assistant provider; offline fallback selected")
        return OfflineProvider()

    api_key = getattr(settings, "GEMINI_API_KEY", "")
    if not isinstance(api_key, str) or not api_key.strip():
        LOGGER.warning("Gemini provider unavailable; API key is not configured")
        return OfflineProvider()

    try:
        return GeminiProvider(
            api_key=api_key,
            model=getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash"),
            timeout_seconds=getattr(settings, "GEMINI_TIMEOUT_SECONDS", 15.0),
            max_retries=getattr(settings, "GEMINI_MAX_RETRIES", 1),
        )
    except ProviderError:
        LOGGER.warning("Gemini provider initialization failed; offline fallback selected")
        return OfflineProvider()
