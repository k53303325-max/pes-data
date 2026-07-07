from __future__ import annotations

import re
from collections import defaultdict, deque
from time import monotonic

import phonenumbers
from phonenumbers import NumberParseException, PhoneNumberFormat

from utils.logger import get_logger

logger = get_logger(__name__)

PHONE_SPLIT_RE = re.compile(r"[\n,;|\s]+")
# Номера в тексте / Excel: +7..., 8..., или 10–11 цифр подряд
PHONE_FIND_RE = re.compile(r"(?:\+7|8|7)\d{10}|\d{11}")


def _preprocess_raw(raw: str) -> str:
    cleaned = raw.strip()
    if not cleaned:
        return ""
    # Excel часто даёт 79991234567.0
    if cleaned.endswith(".0") and cleaned[:-2].replace(".", "").isdigit():
        cleaned = cleaned[:-2]
    # Только цифры без +
    digits = re.sub(r"\D", "", cleaned)
    if len(digits) == 11 and digits.startswith("8"):
        return "+7" + digits[1:]
    if len(digits) == 11 and digits.startswith("7"):
        return "+" + digits
    if len(digits) == 10:
        return "+7" + digits
    return cleaned


def normalize_phone(raw: str, default_region: str = "RU") -> str | None:
    """Normalize phone to E.164 (+79991234567) or return None if invalid."""
    cleaned = _preprocess_raw(raw)
    if not cleaned:
        return None

    try:
        parsed = phonenumbers.parse(cleaned, default_region)
        if not phonenumbers.is_valid_number(parsed):
            return None
        return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    except NumberParseException:
        return None


def extract_phones(text: str) -> list[str]:
    """Parse and deduplicate phones from multiline/comma-separated text."""
    seen: set[str] = set()
    result: list[str] = []

    candidates = list(PHONE_SPLIT_RE.split(text))
    candidates.extend(PHONE_FIND_RE.findall(text))

    for part in candidates:
        part = part.strip()
        if not part:
            continue
        normalized = normalize_phone(part)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)

    return result


class RateLimiter:
    """Simple in-memory sliding window rate limiter per user."""

    def __init__(self, max_calls: int, window_seconds: int) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._buckets: dict[int, deque[float]] = defaultdict(deque)

    def is_allowed(self, user_id: int) -> bool:
        now = monotonic()
        bucket = self._buckets[user_id]

        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()

        if len(bucket) >= self.max_calls:
            logger.warning("Rate limit exceeded for user_id=%s", user_id)
            return False

        bucket.append(now)
        return True

    def seconds_until_reset(self, user_id: int) -> int:
        bucket = self._buckets[user_id]
        if not bucket:
            return 0
        now = monotonic()
        oldest = bucket[0]
        remaining = self.window_seconds - (now - oldest)
        return max(0, int(remaining) + 1)
