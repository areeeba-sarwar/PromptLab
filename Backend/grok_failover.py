from __future__ import annotations

import os
import re
from typing import Any, Callable, Iterable, List, Tuple

try:
    from groq import Groq
except Exception:  # pragma: no cover - handled at runtime for clean frontend errors
    Groq = None


class GrokFailoverError(RuntimeError):
    """Raised after all configured Grok API keys fail."""


USER_FRIENDLY_GROK_ERROR = (
    "AI service is temporarily unavailable. Please try again later."
)

_RETRYABLE_STATUS_CODES = {401, 403, 408, 409, 429, 500, 502, 503, 504}
_RETRYABLE_ERROR_TEXT = (
    "rate limit",
    "rate_limit",
    "quota",
    "insufficient_quota",
    "exceeded",
    "credit",
    "credits",
    "billing",
    "payment",
    "authentication",
    "unauthorized",
    "forbidden",
    "invalid api key",
    "invalid_api_key",
    "api key",
    "service unavailable",
    "temporarily unavailable",
    "timeout",
    "timed out",
    "connection",
    "server error",
    "internal error",
    "bad gateway",
    "gateway",
    "overloaded",
)


def _key_sort_value(name: str) -> int:
    match = re.fullmatch(r"GROK_API_KEY_(\d+)", name)
    return int(match.group(1)) if match else 0


def load_grok_api_keys() -> List[Tuple[int, str]]:
    """
    Load Grok API keys in deterministic order.

    Preferred variables are GROK_API_KEY_1, GROK_API_KEY_2, ...
    Legacy single-key names are accepted only when numbered keys are absent.
    """
    numbered_names = sorted(
        (name for name in os.environ if re.fullmatch(r"GROK_API_KEY_\d+", name)),
        key=_key_sort_value,
    )
    keys = [
        (_key_sort_value(name), os.getenv(name, "").strip())
        for name in numbered_names
        if os.getenv(name, "").strip()
    ]
    if keys:
        return keys

    legacy_keys = []
    for idx, name in enumerate(("GROK_API_KEY", "GROQ_API_KEY"), start=1):
        value = os.getenv(name, "").strip()
        if value and value not in {key for _, key in legacy_keys}:
            legacy_keys.append((idx, value))
    return legacy_keys


def has_grok_api_keys() -> bool:
    return bool(load_grok_api_keys())


def _status_code(exc: Exception) -> int | None:
    status = getattr(exc, "status_code", None)
    if status is None and getattr(exc, "response", None) is not None:
        status = getattr(exc.response, "status_code", None)
    try:
        return int(status) if status is not None else None
    except (TypeError, ValueError):
        return None


def _is_retryable_grok_error(exc: Exception) -> bool:
    status = _status_code(exc)
    if status in _RETRYABLE_STATUS_CODES:
        return True
    text = str(exc).lower()
    return any(marker in text for marker in _RETRYABLE_ERROR_TEXT)


def _call_with_failover(operation: Callable[[Any], Any], action: str) -> Any:
    if Groq is None:
        raise GrokFailoverError(USER_FRIENDLY_GROK_ERROR)

    keys = load_grok_api_keys()
    if not keys:
        raise GrokFailoverError(USER_FRIENDLY_GROK_ERROR)

    last_error: Exception | None = None
    for position, (configured_index, api_key) in enumerate(keys, start=1):
        key_label = configured_index or position
        try:
            print(f"[Grok] Trying Key #{key_label} for {action}", flush=True)
            response = operation(Groq(api_key=api_key))
            print(f"[Grok] Key #{key_label} succeeded for {action}", flush=True)
            return response
        except Exception as exc:
            last_error = exc
            if not _is_retryable_grok_error(exc):
                print(f"[Grok] Key #{key_label} failed for {action}; trying next key", flush=True)
            else:
                print(f"[Grok] Key #{key_label} hit a retryable error for {action}; trying next key", flush=True)

    print(f"[Grok] All configured keys failed for {action}", flush=True)
    raise GrokFailoverError(USER_FRIENDLY_GROK_ERROR) from last_error


def create_chat_completion(*, action: str = "chat completion", **kwargs: Any) -> Any:
    """Create a Grok chat completion with automatic API key failover."""
    return _call_with_failover(
        lambda client: client.chat.completions.create(**kwargs),
        action,
    )
