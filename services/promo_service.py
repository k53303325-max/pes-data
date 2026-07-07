from __future__ import annotations

import hashlib
import hmac

from config.settings import settings


def verify_test_promo(code: str) -> bool:
    """Проверка сложного тестового промокода (1 ₽)."""
    expected = settings.promo_test_code.strip()
    if not expected or not code:
        return False
    return hmac.compare_digest(code.strip(), expected)


def promo_hash_hint() -> str:
    """Подсказка для админа — первые символы хэша, не сам код."""
    if not settings.promo_test_code:
        return "не настроен"
    digest = hashlib.sha256(settings.promo_test_code.encode()).hexdigest()[:12]
    return f"sha256:{digest}…"
