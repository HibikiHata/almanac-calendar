"""祝日の照会口。国コードを渡すと、その国の暦での祝日を返す。

日本だけ経路が違う。`holidays_jp` に法の規則として実装してあり、春分の日と
秋分の日を検証済みの節気テーブルから引く（法律に日付が書かれていないため）。
他国は生成済みCSVを読む。**呼び出し側はこの違いを知らなくてよい**。

祝日は法改正で変わる。他国のテーブルは生成時点の法令に基づく写しなので、
先の年ほど「現行法が続いたら」の意味になる。日本も同じだが、規則として
持っているぶん改正への追随がコード差分として見える。
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache
from pathlib import Path

from almanac_calendar.koyomi.holidays_jp import holiday_name as _jp_name

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "holidays"

#: 規則として実装してある国。CSVを持たない
NATIVE = ("JP",)


@lru_cache(maxsize=1)
def available_countries() -> tuple[str, ...]:
    """使える国コード。生成済みのCSVと、規則実装のある国の和。"""
    found = {p.stem for p in ASSETS.glob("*.csv")} if ASSETS.is_dir() else set()
    return tuple(sorted(found | set(NATIVE)))


@lru_cache(maxsize=8)
def _table(country: str) -> dict[dt.date, str]:
    path = ASSETS / f"{country}.csv"
    if not path.is_file():
        raise ValueError(
            f"祝日テーブルがありません: {country}"
            f"（使えるもの: {', '.join(available_countries())}）。"
            "PYTHONPATH=src python3 -m almanac_calendar._generate.gen_holidays "
            f"{country} を実行してください"
        )
    out: dict[dt.date, str] = {}
    for line in path.read_text("utf-8").splitlines():
        if line.startswith("#") or line.startswith("date,") or not line:
            continue
        stamp, _, name = line.partition(",")
        out[dt.date.fromisoformat(stamp)] = name
    return out


def holiday_name(day: dt.date, country: str) -> str | None:
    """その日がその国の祝日なら名前を、違えば None を返す。

    範囲外の年は None ではなく `ValueError`。黙って「祝日なし」を返すと、
    テーブルが古いだけなのか本当に祝日が無いのか区別できなくなる。
    """
    code = country.upper()
    if code in NATIVE:
        return _jp_name(day)
    table = _table(code)
    if not table:
        raise ValueError(f"{code} の祝日テーブルが空です")
    low, high = min(table).year, max(table).year
    if not low <= day.year <= high:
        raise ValueError(
            f"{code} の祝日テーブルは {low}〜{high}年です: {day}")
    return table.get(day)
