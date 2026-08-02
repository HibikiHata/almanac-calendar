"""月齢と月の形。

**この2つは別の量**で、比例しない。月齢は朔からの経過日数（時間）、
形は月と太陽の離角（角度）。月の軌道が楕円で不等速なため、望（満月）が
起きる月齢は13.9〜15.6日の幅で動く。月齢から線形に形を出すと、この幅が
そのまま絵の誤差になる（実測で最大10ポイント超。test_moon.py で固定）。

形は**四相の間を離角で補間**して出す。四相は離角が 0/90/180/270度と
厳密に決まっているので、節点では輝面比が 0/50/100/50% と誤差なく合う。
節点間は離角が時間に比例すると見なす——実際には月の速度が変わるので
近似だが、7日ごとに節点で引き戻されるため誤差は蓄積しない。
"""
from __future__ import annotations

import datetime as dt
import math
from bisect import bisect_right
from functools import lru_cache

from almanac_calendar.koyomi import tables

#: 朔望月の平均日数。月齢の上限判定と線形近似の比較にだけ使う。
#: **形の計算には使わない**（モジュール冒頭の理由）
SYNODIC_MONTH = 29.530588853

#: 月齢を「その日の何時の値」として出すか。日本の暦の慣習は正午。
#: 1日の中でも月齢は1増えるので、基準時刻を決めないと値が定まらない
AGE_REFERENCE_HOUR = 12


def _noon(day: dt.date, offset_hours: int) -> dt.datetime:
    tz = dt.timezone(dt.timedelta(hours=offset_hours))
    return dt.datetime(day.year, day.month, day.day,
                       AGE_REFERENCE_HOUR, tzinfo=tz)


def moon_age(day: dt.date, *, offset_hours: int = 9) -> float:
    """正午（現地）時点の月齢。直前の朔からの経過日数。

    朔がその日の正午より後にある場合は、**前の朔**から数える。
    朔の日の月齢を負にしないため（暦の慣習では0日台になる）。
    """
    tables._check_supported(day)
    moment = _noon(day, offset_hours)
    moons = tables.new_moons()
    index = bisect_right(moons, moment) - 1
    if index < 0:
        raise ValueError(f"朔のデータが足りません: {day}")
    return (moment - moons[index]).total_seconds() / 86400


@lru_cache(maxsize=1)
def _phase_instants() -> tuple[tuple[dt.datetime, int], ...]:
    return tables.moon_phases()


def _elongation(moment: dt.datetime) -> float:
    """月と太陽の離角（度、0〜360）。四相を節点に線形補間する。"""
    phases = _phase_instants()
    index = bisect_right([w for w, _ in phases], moment) - 1
    if index < 0 or index + 1 >= len(phases):
        raise ValueError(f"月相のデータが足りません: {moment}")
    (start, code), (end, _) = phases[index], phases[index + 1]
    span = (end - start).total_seconds()
    ratio = (moment - start).total_seconds() / span if span else 0.0
    return (tables.PHASES[code] + 90 * ratio) % 360


def illumination(moment: dt.datetime) -> float:
    """輝面比（0=朔、1=望）。離角から出す。"""
    return (1 - math.cos(math.radians(_elongation(moment)))) / 2


def is_waxing(moment: dt.datetime) -> bool:
    """満ちていく側か（朔→望）。形の左右を決めるのに使う。"""
    return _elongation(moment) < 180


def appearance(day: dt.date, *, offset_hours: int = 9) -> tuple[float, bool]:
    """その日の正午の (輝面比, 満ちる側か)。描画側が使う唯一の入口。

    描画層に子午線の知識を持たせないための関数。`offset_hours` は暦法の
    境界子午線であって表示タイムゾーンではない（ADR-0011 不変条件2）。
    """
    tables._check_supported(day)
    moment = _noon(day, offset_hours)
    return illumination(moment), is_waxing(moment)


def phase_code_on(day: dt.date, *, offset_hours: int = 9) -> int | None:
    """その日が四相のいずれかならコードを、違えば None を返す。"""
    tables._check_supported(day)
    return _phases_by_day(offset_hours).get(day)


@lru_cache(maxsize=4)
def _phases_by_day(offset_hours: int) -> dict[dt.date, int]:
    tz = dt.timezone(dt.timedelta(hours=offset_hours))
    return {when.astimezone(tz).date(): code for when, code in _phase_instants()}
