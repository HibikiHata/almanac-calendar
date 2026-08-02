"""生成済み天文テーブルの読み込み（実行時・標準ライブラリのみ）。

CSV を読むだけ。天文計算は開発時に済ませてある（ADR-0011）。
値は **UTC** で持つ。天文現象は子午線に依存せず、暦日の割り当てだけが
依存するので、同じテーブルを他の暦体系にも使える。
"""
from __future__ import annotations

import datetime as dt
from bisect import bisect_right
from functools import lru_cache
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "koyomi"

# 表が実際に答えを出せる範囲。生成範囲はこれより広い（月名の決定に
# 前年の冬至と翌年の中気が要るため。ADR-0011 不変条件6）。
SUPPORTED_RANGE = (dt.date(1900, 1, 1), dt.date(2100, 12, 31))


def _read(name: str) -> tuple[list[str], dict[str, str]]:
    path = ASSETS / name
    if not path.is_file():
        raise ValueError(
            f"天文テーブルがありません: {path}。"
            "PYTHONPATH=src python3 -m almanac_calendar._generate.gen_koyomi_tables を実行してください"
        )
    meta: dict[str, str] = {}
    rows: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            if ":" in line:
                key, _, value = line[1:].partition(":")
                meta[key.strip()] = value.strip()
        elif line and not line.startswith("utc"):
            rows.append(line)
    return rows, meta


def _parse(stamp: str) -> dt.datetime:
    return dt.datetime.fromisoformat(stamp).replace(tzinfo=dt.timezone.utc)


#: 月相コード -> (離角の度数, 識別子)。表示名は言語ごとに変わるので持たない
PHASES = {0: 0, 1: 90, 2: 180, 3: 270}


@lru_cache(maxsize=1)
def moon_phases() -> tuple[tuple[dt.datetime, int], ...]:
    """朔弦望すべて。コードは 0:朔 1:上弦 2:望 3:下弦（離角 0/90/180/270度）。"""
    rows, _ = _read("moonphases.csv")
    out = []
    for row in rows:
        stamp, _, code = row.partition(",")
        out.append((_parse(stamp), int(code)))
    return tuple(out)


@lru_cache(maxsize=1)
def new_moons() -> tuple[dt.datetime, ...]:
    """朔だけを取り出す。旧暦の月はここからしか始まらない。"""
    return tuple(when for when, code in moon_phases() if code == 0)


@lru_cache(maxsize=1)
def solar_terms() -> tuple[tuple[dt.datetime, int], ...]:
    """24節気すべて。中気（黄経が30の倍数）も節気も含む。"""
    rows, _ = _read("solarterms.csv")
    out = []
    for row in rows:
        stamp, _, lon = row.partition(",")
        out.append((_parse(stamp), int(lon)))
    return tuple(out)


@lru_cache(maxsize=1)
def provenance() -> dict[str, str]:
    """生成条件。黄経の定義がここに残っていないと後で検証できない。"""
    _, meta = _read("moonphases.csv")
    return meta


def _check_supported(day: dt.date) -> None:
    lo, hi = SUPPORTED_RANGE
    if not (lo <= day <= hi):
        raise ValueError(f"サポート範囲外です（{lo}〜{hi}）: {day}")


def new_moon_on_or_before(day: dt.date, *, offset_hours: int = 9) -> dt.datetime:
    """その日を含む朔月の、朔の瞬間を返す。

    offset_hours は暦体系の基準子午線（日本の旧暦は +9）。閲覧者の
    タイムゾーンではない（ADR-0011 不変条件2）。
    """
    _check_supported(day)
    tz = dt.timezone(dt.timedelta(hours=offset_hours))
    # その日の終わり（現地時刻）までに起きた最後の朔
    limit = dt.datetime.combine(day, dt.time(23, 59), tzinfo=tz)
    moons = new_moons()
    index = bisect_right(moons, limit) - 1
    if index < 0:
        raise ValueError(f"テーブルに該当する朔がありません: {day}")
    return moons[index]


@lru_cache(maxsize=4)
def _terms_by_day(offset_hours: int) -> dict[dt.date, int]:
    tz = dt.timezone(dt.timedelta(hours=offset_hours))
    return {when.astimezone(tz).date(): longitude
            for when, longitude in solar_terms()}


def solar_term_on(day: dt.date, *, offset_hours: int = 9) -> int | None:
    """その日に二十四節気があれば黄経を、無ければ None を返す。

    `offset_hours` は暦法の境界子午線。日本は東経135度＝UTC+9で固定
    （ADR-0011 不変条件2）。節気の瞬間が日界の前後数分にある事象が
    1900〜2100年で40件あり、子午線を取り違えると日が1つずれる。
    """
    _check_supported(day)
    return _terms_by_day(offset_hours).get(day)
