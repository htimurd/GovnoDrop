"""
Игровые предметы Govno Drop.
Полностью вымышленные предметы, НЕ являются скинами CS2 или иным реальным
торгуемым активом. Игровая валюта ("монеты") не обменивается на реальные
деньги и не имеет ценности вне бота.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Tier:
    key: str
    title: str
    emoji: str
    value: int          # стоимость в монетах (виртуальных)
    drop_weight: int     # вес при открытии кейса (чем больше, тем чаще выпадает)
    upgrade_chance: float  # шанс успешно улучшиться ДО следующего тира, 0..1


# Тиры отсортированы от самого частого/дешёвого к самому редкому/дорогому.
# upgrade_chance — шанс успеха при попытке улучшить предмет ЭТОГО тира
# до следующего по списку. У последнего тира апгрейда нет.
TIERS: list[Tier] = [
    Tier("trash",     "Драный носок",        "🧦",    10, 100, 0.65),
    Tier("common",    "Ржавая банка",        "🥫",    25,  70, 0.50),
    Tier("uncommon",  "Сломанный веник",     "🧹",    60,  45, 0.35),
    Tier("rare",      "Пластиковый таз",     "🪣",   150,  25, 0.22),
    Tier("epic",      "Золотой унитаз",      "🚽",   400,  10, 0.12),
    Tier("legendary", "Алмазная лопата",     "⛏️",  1000,   4, 0.06),
    Tier("mythic",    "Метеорит Говна",      "☄️",  3000,   1, 0.0),
]

TIERS_BY_KEY = {t.key: t for t in TIERS}


def next_tier(key: str) -> Tier | None:
    idx = next(i for i, t in enumerate(TIERS) if t.key == key)
    if idx + 1 < len(TIERS):
        return TIERS[idx + 1]
    return None


def case_price() -> int:
    return 50


def total_drop_weight() -> int:
    return sum(t.drop_weight for t in TIERS)


def format_odds_table() -> str:
    lines = ["<b>🎲 Шансы выпадения из кейса</b> (цена кейса: {} монет)".format(case_price())]
    total = total_drop_weight()
    for t in TIERS:
        chance = t.drop_weight / total * 100
        lines.append(f"{t.emoji} {t.title} — {chance:.2f}% (цена {t.value} монет)")

    lines.append("\n<b>⬆️ Шансы апгрейда предмета до следующего тира</b>")
    for t in TIERS:
        nt = next_tier(t.key)
        if nt is None:
            continue
        lines.append(
            f"{t.emoji} {t.title} → {nt.emoji} {nt.title}: {t.upgrade_chance*100:.0f}% "
            f"(при неудаче предмет теряется)"
        )
    return "\n".join(lines)
