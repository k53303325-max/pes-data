from __future__ import annotations


def _inn10_checksum(digits: list[int]) -> int:
    weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    s = sum(d * w for d, w in zip(digits[:9], weights))
    return s % 11 % 10


def _inn12_checksum(digits: list[int], weights: list[int]) -> int:
    s = sum(d * w for d, w in zip(digits[: len(weights)], weights))
    return s % 11 % 10


def normalize_inn(raw: str) -> str | None:
    cleaned = "".join(ch for ch in (raw or "").strip() if ch.isdigit())
    if len(cleaned) not in (10, 12):
        return None
    return cleaned


def validate_inn(raw: str) -> tuple[bool, str | None]:
    inn = normalize_inn(raw)
    if not inn:
        return False, None
    digits = [int(c) for c in inn]
    if len(digits) == 10:
        if _inn10_checksum(digits) != digits[9]:
            return False, inn
        return True, inn
    w1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    w2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    if _inn12_checksum(digits, w1) != digits[10]:
        return False, inn
    if _inn12_checksum(digits, w2) != digits[11]:
        return False, inn
    return True, inn
