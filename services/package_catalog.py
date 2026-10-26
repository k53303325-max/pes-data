from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PackageOffer:
    code: str
    name: str
    contact_count: int
    price: int
    emoji: str = ""
    is_trial: bool = False
    tariff_id: int | None = None

    @property
    def unit_price(self) -> int:
        if self.contact_count <= 0:
            return 0
        return self.price // self.contact_count

    @property
    def button_label(self) -> str:
        if self.is_trial:
            return f"🎁 Бесплатный триал · {self.contact_count} контактов · 0 ₽"
        price_fmt = f"{self.price:,} ₽".replace(",", " ")
        return f"{self.name} · {self.contact_count} контактов · {price_fmt}"


# Пакеты по инструкции (раздел 5). tariff_id — для связи с БД при оплате позже.
PACKAGES: tuple[PackageOffer, ...] = (
    PackageOffer("trial", "Бесплатный триал", 20, 0, "🎁", is_trial=True),
    PackageOffer("mini", "Мини", 50, 5_000, tariff_id=1),
    PackageOffer("start", "Старт", 100, 9_000, tariff_id=2),
    PackageOffer("growth", "Рост", 250, 20_000, tariff_id=3),
    PackageOffer("business", "Бизнес", 500, 35_000, tariff_id=4),
    PackageOffer("scale", "Масштаб", 1_000, 60_000, tariff_id=5),
)


def get_package(code: str) -> PackageOffer | None:
    for pkg in PACKAGES:
        if pkg.code == code:
            return pkg
    return None


def paid_packages() -> list[PackageOffer]:
    return [p for p in PACKAGES if not p.is_trial]
