"""旧暦（天保暦）の日付。

規則そのものは短い。

  - 朔（新月）の瞬間を含む日が、その月の1日
  - 月の名前は、その月に含まれる**中気**で決まる（12個の中気が旧暦の各月に
    1対1で対応する。雨水＝正月中気 … 冬至＝11月中気、大寒＝12月中気）
  - 中気を1つも含まない月が閏月で、前の月の名前を引き継ぐ
  - 二至二分（春分・夏至・秋分・冬至）のある月は必ず 2・5・8・11月

最後の「二至二分」は他の3つと性質が違う。**衝突が起きたときの優先制約**で、
通常年には出番がない。衝突は定気法の帰結として起きる: 地球の公転が楕円で
不等速なため中気の間隔が一定でなく、冬至前後は約29.4日と朔望月（29.53日）より
短くなる。すると1つの朔望月に中気が2回入り、前後に中気の無い月が生じて
「どちらを閏月にするか」が決まらなくなる。

2033-07-26〜2034-03-20 はこの優先制約でも解決できない（ADR-0011 不変条件5）。
"""
from __future__ import annotations

import datetime as dt
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache

from almanac_calendar.koyomi import tables

#: 天保暦の規則では閏月を一意に決められない区間（ADR-0011 不変条件5）。
#: 暦文協・KASI・香港天文台・koyomi8 が一致する「閏11月」案を採るが、
#: 唯一の正解ではないので利用側が注記を出せるようフラグで印をつける。
UNDETERMINED = (dt.date(2033, 7, 26), dt.date(2034, 3, 20))


@dataclass(frozen=True)
class LunarDate:
    year: int
    month: int                # 1..12。閏月も前月と同じ番号を持つ
    day: int                  # 1..30
    is_leap_month: bool
    rule_undetermined: bool   # 2033-07-26..2034-03-20 に交差する月

    def __post_init__(self) -> None:
        if not 1 <= self.month <= 12:
            raise ValueError(f"旧暦の月は1〜12です: {self.month}")
        if not 1 <= self.day <= 30:
            raise ValueError(f"旧暦の日は1〜30です: {self.day}")

    def __str__(self) -> str:
        leap = "閏" if self.is_leap_month else ""
        return f"{leap}{self.month}月{self.day}日"


@lru_cache(maxsize=4)
def _months(offset_hours: int) -> tuple[tuple[dt.date, int, int, bool], ...]:
    """朔望月を並べ、各月に (開始日, 旧暦年, 月番号, 閏か) を割り当てる。

    月番号は**冬至を含む月を11月と置いて数える**。中気を1つずつ拾って
    名前をつける素直な実装にすると、中気を2つ含む月（定気法の帰結）で
    番号が競合して破綻する。冬至から数えれば競合しない。

    閏月の位置は「冬至月から次の冬至月までに13ヶ月あるとき、その間で
    最初に中気を含まない月」。これは中国暦の規則だが、2033年を含め
    暦文協の採用案と一致する。
    """
    tz = dt.timezone(dt.timedelta(hours=offset_hours))
    starts = [when.astimezone(tz).date() for when in tables.new_moons()]

    # 各朔望月が含む中気の黄経。中気は30の倍数（節気は15の倍数）
    contained: list[list[int]] = [[] for _ in starts]
    for when, longitude in tables.solar_terms():
        if longitude % 30:
            continue
        index = bisect_right(starts, when.astimezone(tz).date()) - 1
        if 0 <= index < len(starts):
            contained[index].append(longitude)

    solstices = [i for i, lons in enumerate(contained) if 270 in lons]
    numbers: dict[int, tuple[int, bool]] = {}
    for begin, following in zip(solstices, solstices[1:]):
        leap_at = None
        if following - begin == 13:
            leap_at = next((i for i in range(begin + 1, following)
                            if not contained[i]), None)
        month = 11
        numbers[begin] = (month, False)
        for i in range(begin + 1, following):
            if i == leap_at:
                numbers[i] = (month, True)
            else:
                month = month % 12 + 1
                numbers[i] = (month, False)
    # 最後の冬至月は次の冬至で挟めないので配置できない。サポート範囲が
    # その手前で終わっていることを保証する。ここを黙って埋めると、末尾の
    # 月がテーブル終端まで伸びて「31日」のような日付を返す
    low, high = tables.SUPPORTED_RANGE
    if not starts[solstices[0]] <= low or not high < starts[solstices[-1]]:
        raise RuntimeError(
            f"サポート範囲 {low}〜{high} が冬至周期で挟めていません"
            f"（{starts[solstices[0]]}〜{starts[solstices[-1]]}）。"
            "gen_koyomi_tables.py の GEN_START / GEN_END を広げること")

    rows = [[start, None, *numbers[i]]
            for i, start in enumerate(starts) if i in numbers]
    year = None
    for row in rows:
        if row[2] == 1 and not row[3]:
            year = row[0].year            # 旧暦の年は正月で改まる
        row[1] = year
    # 先頭の正月より前の月は、次の正月から遡って前年とする
    head = next((row[1] for row in rows if row[1] is not None), None)
    for row in rows:
        if row[1] is None:
            row[1] = head - 1
    return tuple(tuple(row) for row in rows)


@lru_cache(maxsize=4)
def _starts(offset_hours: int) -> tuple[dt.date, ...]:
    """二分探索用の開始日だけの列。毎回組み直すと変換がO(月数)になる。"""
    return tuple(month[0] for month in _months(offset_hours))


def gregorian_to_lunar(day: dt.date, *, offset_hours: int = 9) -> LunarDate:
    """新暦の日付を旧暦（天保暦）の日付に変換する。

    `offset_hours` は**暦法の境界子午線**であって表示タイムゾーンではない
    （ADR-0011 不変条件2）。日本の天保暦は東経135度＝UTC+9で固定。
    1948〜51年の夏時刻に引きずられるため `ZoneInfo("Asia/Tokyo")` を
    使ってはいけない。中国暦なら8、韓国の現行暦なら9。
    """
    low, high = tables.SUPPORTED_RANGE
    if not low <= day <= high:
        raise ValueError(f"対応範囲は {low}〜{high} です: {day}")

    index = bisect_right(_starts(offset_hours), day) - 1
    if index < 0:
        raise ValueError(f"対応範囲外です: {day}")
    start, year, month, is_leap = _months(offset_hours)[index]
    return LunarDate(
        year=year,
        month=month,
        day=(day - start).days + 1,
        is_leap_month=is_leap,
        rule_undetermined=UNDETERMINED[0] <= day <= UNDETERMINED[1],
    )
