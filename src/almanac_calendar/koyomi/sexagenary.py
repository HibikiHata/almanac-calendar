"""干支（十干十二支）と節月。暦注の土台になる2つの量。

**どちらも新しい天文計算を要らない**。干支は60日周期の剰余だけ、節月は
既存の節気テーブルから引くだけ。暦注（一粒万倍日・天赦日など）はすべて
この2つと旧暦日の組み合わせで機械的に決まる。

節月は**節切り**の月で、旧暦の月とは別物。立春から啓蟄の前日までが正月、
啓蟄から清明の前日までが二月、と続く。境界は中気（黄経30の倍数）ではなく
**節**（黄経15の倍数のうち30の倍数でないもの）。ここを取り違えると
暦注が約半月ずれる。
"""
from __future__ import annotations

import datetime as dt
from bisect import bisect_right
from functools import lru_cache

from almanac_calendar.koyomi import tables

STEMS = "甲乙丙丁戊己庚辛壬癸"
BRANCHES = "子丑寅卯辰巳午未申酉戌亥"

#: 日の干支の基準。`(date.toordinal() + DAY_OFFSET) % 60` が甲子起点の通番。
#: 韓国天文研究院の日辰（LUNC_ILJIN）から求め、1900・2000・2026・2050年の
#: 4点で同じ値になることを確認した。全期間の照合は
#: `_generate/verify_sexagenary.py` が行う
DAY_OFFSET = 14


def day_index(day: dt.date) -> int:
    """甲子を0とする60日周期の通番。"""
    return (day.toordinal() + DAY_OFFSET) % 60


def day_stem(day: dt.date) -> str:
    return STEMS[day_index(day) % 10]


def day_branch(day: dt.date) -> str:
    return BRANCHES[day_index(day) % 12]


def day_sexagenary(day: dt.date) -> str:
    """その日の干支（例: 戊申）。"""
    return day_stem(day) + day_branch(day)


@lru_cache(maxsize=4)
def _setsu_boundaries(offset_hours: int) -> tuple[tuple[dt.date, int], ...]:
    """節（中気でないほうの節気）の開始日を並べる。

    黄経が30の倍数のものは中気なので除く。残る12個が節月の境目。
    """
    tz = dt.timezone(dt.timedelta(hours=offset_hours))
    out = [(when.astimezone(tz).date(), longitude)
           for when, longitude in tables.solar_terms() if longitude % 30]
    return tuple(sorted(out))


def solar_month(day: dt.date, *, offset_hours: int = 9) -> int:
    """節月（1〜12）。立春から啓蟄の前日までが1。

    旧暦の月ではない。暦注の多くはこちらを使う。
    """
    tables._check_supported(day)
    boundaries = _setsu_boundaries(offset_hours)
    index = bisect_right([d for d, _ in boundaries], day) - 1
    if index < 0:
        raise ValueError(f"節のデータが足りません: {day}")
    longitude = boundaries[index][1]
    # 立春（黄経315度）を正月とし、30度ごとに1ヶ月進む
    return (longitude - 315) % 360 // 30 + 1


#: 二十八宿。中国流（貞享暦以後の日本もこれ）。**28日周期を回すだけ**で、
#: 節気にも旧暦にも依存しない
MANSIONS = ("角", "亢", "氏", "房", "心", "尾", "箕", "斗", "牛", "女",
            "虚", "危", "室", "壁", "奎", "婁", "胃", "昴", "畢", "觜",
            "参", "井", "鬼", "柳", "星", "張", "翼", "軫")

#: 二十八宿の基準。`(date.toordinal() + MANSION_OFFSET) % 28` が MANSIONS の添字。
#: こよみのページの計算コード `SYUKU[(JD + 12) % 28]` から導いた（同サイトは
#: 典拠を『旧暦読本』と明示）。公表されている2026年の鬼宿日13日と全件一致する。
#: **28は7の倍数なので、宿と曜日の対応は永久に固定される**——鬼宿は常に金曜。
#: この性質が基準のずれを検出する最も安いテストになる
MANSION_OFFSET = 24


def mansion(day: dt.date) -> str:
    """その日の二十八宿。"""
    return MANSIONS[(day.toordinal() + MANSION_OFFSET) % 28]


#: 季節（天赦日の判定に使う）。節月から引く
SEASONS = {1: "春", 2: "春", 3: "春", 4: "夏", 5: "夏", 6: "夏",
           7: "秋", 8: "秋", 9: "秋", 10: "冬", 11: "冬", 12: "冬"}


def season(day: dt.date, *, offset_hours: int = 9) -> str:
    """節切りの季節。立春から春、立夏から夏（暦の上の季節）。"""
    return SEASONS[solar_month(day, offset_hours=offset_hours)]
