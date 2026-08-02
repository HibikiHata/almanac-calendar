"""日本の国民の祝日（昭和23年法律第178号）。

**春分の日と秋分の日は法律に日付が書かれていない**。「春分日」「秋分日」と
だけ定められており、実際の日付は国立天文台が前年2月の官報（暦要項）で公表して
初めて確定する。だからここでは近似式を使わず、NAOJと全件照合済みの
節気テーブル（黄経0度・180度の瞬間を含むJSTの日）から直に引く。

残りは日付の規則だが、**1948年からの改正史をそのまま持つ必要がある**。
祝日は増減し、移動し、名前が変わってきた。「今の法律」だけを実装すると
過去の月を描いたときに静かに嘘をつく。改正は下の表に集約してある。

法の施行は1948-07-20。それ以前の年には祝日を返さない（無いのが正しい）。
"""
from __future__ import annotations

import datetime as dt
from calendar import MONDAY
from functools import lru_cache

from almanac_calendar.koyomi import tables

LAW_EFFECTIVE = dt.date(1948, 7, 20)

#: 固定日の祝日: (月, 日, 名前, 開始年, 終了年)。終了年 None は現行
FIXED: tuple[tuple[int, int, str, int, int | None], ...] = (
    (1, 1, "元日", 1949, None),
    (1, 15, "成人の日", 1949, 1999),          # 2000年からハッピーマンデー
    (2, 11, "建国記念の日", 1967, None),
    (2, 23, "天皇誕生日", 2020, None),        # 今上天皇
    (4, 29, "天皇誕生日", 1949, 1988),        # 昭和天皇
    (4, 29, "みどりの日", 1989, 2006),
    (4, 29, "昭和の日", 2007, None),
    (5, 3, "憲法記念日", 1949, None),
    (5, 4, "みどりの日", 2007, None),         # それ以前は国民の休日として成立
    (5, 5, "こどもの日", 1949, None),
    (7, 20, "海の日", 1996, 2002),            # 2003年からハッピーマンデー
    (8, 11, "山の日", 2016, None),
    (9, 15, "敬老の日", 1966, 2002),          # 2003年からハッピーマンデー
    (10, 10, "体育の日", 1966, 1999),         # 2000年からハッピーマンデー
    (11, 3, "文化の日", 1948, None),
    (11, 23, "勤労感謝の日", 1948, None),
    (12, 23, "天皇誕生日", 1989, 2018),       # 平成。2019年は退位により無い
)

#: ハッピーマンデー: (月, 第n月曜, 名前, 開始年, 終了年)
HAPPY_MONDAY: tuple[tuple[int, int, str, int, int | None], ...] = (
    (1, 2, "成人の日", 2000, None),
    (7, 3, "海の日", 2003, None),
    (9, 3, "敬老の日", 2003, None),
    (10, 2, "体育の日", 2000, 2019),
    (10, 2, "スポーツの日", 2020, None),
)

#: 一度きりの祝日。皇室行事と、五輪のための移動。
#: 移動した年は通常の規則を**打ち消す**必要があるので、移動元も持つ
ONE_OFF: dict[dt.date, str] = {
    dt.date(1959, 4, 10): "皇太子明仁親王の結婚の儀",
    dt.date(1989, 2, 24): "昭和天皇の大喪の礼",
    dt.date(1990, 11, 12): "即位礼正殿の儀",
    dt.date(1993, 6, 9): "皇太子徳仁親王の結婚の儀",
    dt.date(2019, 5, 1): "天皇の即位の日",
    dt.date(2019, 10, 22): "即位礼正殿の儀",
    # 2020・2021年の東京五輪特例。開閉会式に合わせて移動した
    dt.date(2020, 7, 23): "海の日",
    dt.date(2020, 7, 24): "スポーツの日",
    dt.date(2020, 8, 10): "山の日",
    dt.date(2021, 7, 22): "海の日",
    dt.date(2021, 7, 23): "スポーツの日",
    dt.date(2021, 8, 8): "山の日",
}

#: 五輪特例で本来の位置から消える祝日: 年 -> {(月, 名前)}
OLYMPIC_MOVED = {
    2020: {"海の日", "スポーツの日", "山の日"},
    2021: {"海の日", "スポーツの日", "山の日"},
}

#: 振替休日の施行日。これ以前は日曜と重なっても振り替えない
SUBSTITUTE_FROM = dt.date(1973, 4, 12)
#: 「その後の最初の平日」に広がった年。それ以前は翌日のみ
SUBSTITUTE_CHAIN_FROM = 2007
#: 国民の休日（祝日に挟まれた平日）の施行年
CITIZENS_HOLIDAY_FROM = 1988


def _nth_monday(year: int, month: int, nth: int) -> dt.date:
    first = dt.date(year, month, 1)
    offset = (MONDAY - first.weekday()) % 7
    return first + dt.timedelta(days=offset + 7 * (nth - 1))


def _equinox(year: int, longitude: int) -> dt.date | None:
    """春分日（黄経0度）または秋分日（180度）。節気テーブルから引く。

    近似式を使わないのは、法が「春分日」としか書いておらず、実体が
    天文現象そのものだから。テーブルはNAOJと全件照合済み。
    """
    jst = dt.timezone(dt.timedelta(hours=9))
    for when, lon in tables.solar_terms():
        if lon != longitude:
            continue
        day = when.astimezone(jst).date()
        if day.year == year:
            return day
    return None


@lru_cache(maxsize=256)
def holidays_in(year: int) -> dict[dt.date, str]:
    """その年の祝日。休日の名前を日付から引ける辞書を返す。

    同じ日に複数の名前が立ちうるが（例: 振替休日と国民の休日）、
    先に決まったほうを残す。表示するのは1つなので。
    """
    if year < LAW_EFFECTIVE.year:
        return {}
    out: dict[dt.date, str] = {}

    def put(day: dt.date, name: str) -> None:
        if day >= LAW_EFFECTIVE and day.year == year:
            out.setdefault(day, name)

    for month, dom, name, since, until in FIXED:
        if since <= year and (until is None or year <= until):
            if name in OLYMPIC_MOVED.get(year, ()):
                continue
            put(dt.date(year, month, dom), name)
    for month, nth, name, since, until in HAPPY_MONDAY:
        if since <= year and (until is None or year <= until):
            if name in OLYMPIC_MOVED.get(year, ()):
                continue
            put(_nth_monday(year, month, nth), name)

    for longitude, name in ((0, "春分の日"), (180, "秋分の日")):
        day = _equinox(year, longitude)
        if day is not None and year >= 1949 or (day and name == "秋分の日"):
            put(day, name)

    for day, name in ONE_OFF.items():
        put(day, name)

    _add_substitutes(out, year)
    _add_citizens_holidays(out, year)
    return dict(sorted(out.items()))


def _add_substitutes(out: dict[dt.date, str], year: int) -> None:
    """振替休日。祝日が日曜なら、その後の最初の非祝日を休みにする。

    2006年までは「翌日」だけ。2007年から連鎖する形に変わった
    （祝日が2日続いて日曜に当たると、翌々日まで動く）。
    """
    for day in sorted(out):
        if day.weekday() != 6 or day < SUBSTITUTE_FROM:
            continue
        nxt = day + dt.timedelta(days=1)
        if year < SUBSTITUTE_CHAIN_FROM:
            if nxt not in out and nxt.year == year:
                out[nxt] = "振替休日"
            continue
        while nxt in out:
            nxt += dt.timedelta(days=1)
        if nxt.year == year:
            out[nxt] = "振替休日"


def _add_citizens_holidays(out: dict[dt.date, str], year: int) -> None:
    """国民の休日。祝日に挟まれた平日を休みにする。

    日曜と振替休日は対象外（もともと休みなので挟まれても増えない）。
    9月の敬老の日と秋分の日が1日空くときに出るのが今の主な出番。
    """
    if year < CITIZENS_HOLIDAY_FROM:
        return
    for day in sorted(out):
        middle = day + dt.timedelta(days=1)
        after = day + dt.timedelta(days=2)
        if (after in out and middle not in out
                and middle.weekday() != 6 and middle.year == year):
            out[middle] = "国民の休日"


def holiday_name(day: dt.date) -> str | None:
    """その日が祝日なら名前を、違えば None を返す。"""
    return holidays_in(day.year).get(day)
