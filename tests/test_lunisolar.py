"""天保暦のルール層。朔と中気のテーブルから旧暦の年月日を組み立てる。

天文層（朔・中気の瞬時）は国立天文台と全件照合できるが、**ルール層には
権威ある正解が存在しない**。日本は明治5年の改暦で旧暦を公的に廃止しており、
現行の旧暦を公表する政府機関がない（国立天文台も朔と節気は出すが旧暦日は
出さない）。そこで検証は二段構えにする。

  1. ここ（構造不変条件）: 出典を必要としない性質だけを固定する。
     朔日が1日であること、二至二分が2/5/8/11月にあること、閏月が前月と
     同番号であること。**これらは天保暦の定義そのもの**なので、
     満たさなければ実装が間違っている。
  2. 別途（KASIとの突き合わせ）: 韓国天文研究院は同じUTC+9で、政府機関で、
     QREKI系の実装から独立している。設計文書 §11.1。

年中行事の日付をアンカーに使うのは、それが「旧暦の何月何日か」を定義に
持つ行事に限る（十五夜＝8月15日、旧正月＝1月1日）。七夕や桃の節句は
新暦で行う地域が多く、アンカーにならない。
"""

from __future__ import annotations

import datetime as dt

import pytest

from almanac_calendar.koyomi import tables
from almanac_calendar.koyomi.lunisolar import LunarDate, gregorian_to_lunar
from almanac_calendar.koyomi.solar_terms import ANCHORS

JST = dt.timezone(dt.timedelta(hours=9))


def d(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


class TestAnchors:
    """旧暦の日付で定義された年中行事。新暦側の日付は広く公表されている。"""

    @pytest.mark.parametrize("day", [
        "2023-09-29", "2024-09-17", "2025-10-06", "2026-09-25", "2027-09-15",
    ])
    def test_中秋の名月は旧暦8月15日(self, day):
        lunar = gregorian_to_lunar(d(day))
        assert (lunar.month, lunar.day) == (8, 15)
        assert not lunar.is_leap_month

    @pytest.mark.parametrize("day", [
        "2024-02-10", "2025-01-29", "2026-02-17", "2027-02-07",
    ])
    def test_旧正月は旧暦1月1日(self, day):
        lunar = gregorian_to_lunar(d(day))
        assert (lunar.month, lunar.day) == (1, 1)
        assert not lunar.is_leap_month

    def test_十三夜は旧暦9月13日(self):
        assert gregorian_to_lunar(d("2025-11-02")) == LunarDate(
            year=2025, month=9, day=13, is_leap_month=False,
            rule_undetermined=False)


class TestNewMoonIsDayOne:
    """朔の瞬間を含む日が、その月の1日。天保暦の第一の規則。"""

    def test_全ての朔日が旧暦1日になる(self):
        start, end = tables.SUPPORTED_RANGE
        for when in tables.new_moons():
            day = when.astimezone(JST).date()
            if start <= day <= end:
                assert gregorian_to_lunar(day).day == 1, day

    def test_朔日の前日は月の末日(self):
        start, end = tables.SUPPORTED_RANGE
        for when in tables.new_moons():
            day = when.astimezone(JST).date() - dt.timedelta(days=1)
            if start <= day <= end:
                assert gregorian_to_lunar(day).day in (29, 30), day


class TestChukiDefinesMonth:
    """月の名前はその月に含まれる中気で決まる。二至二分は最優先の制約。"""

    def test_二至二分は必ず所定の月に入る(self):
        start, end = tables.SUPPORTED_RANGE
        for when, longitude in tables.solar_terms():
            day = when.astimezone(JST).date()
            if not (start <= day <= end):
                continue
            expected = ANCHORS.get(_term_name(longitude))
            if expected is None:
                continue
            lunar = gregorian_to_lunar(day)
            if lunar.rule_undetermined:
                continue  # 2033年問題の区間は規則が定まらない
            assert lunar.month == expected, f"{day} 黄経{longitude}°"


def _term_name(longitude: int) -> str:
    from almanac_calendar.koyomi.solar_terms import term_by_longitude
    return term_by_longitude(longitude).name


class TestLeapMonths:
    def test_閏月は中気を含まない(self):
        """閏月と判定した月に中気があってはならない。"""
        start, end = tables.SUPPORTED_RANGE
        chuki = {when.astimezone(JST).date()
                 for when, lon in tables.solar_terms() if lon % 30 == 0}
        day = start
        while day <= end:
            lunar = gregorian_to_lunar(day)
            if lunar.is_leap_month and not lunar.rule_undetermined:
                assert day not in chuki, f"{day} は閏月なのに中気がある"
            day += dt.timedelta(days=1)

    def test_閏月は前の月と同じ番号を持つ(self):
        start, end = tables.SUPPORTED_RANGE
        day = start
        previous = None
        while day <= end:
            lunar = gregorian_to_lunar(day)
            if lunar.is_leap_month and lunar.day == 1:
                assert previous is not None
                assert lunar.month == previous.month, f"{day}"
                assert not previous.is_leap_month, f"{day} 閏月が連続している"
            if lunar.day == 1:
                previous = lunar
            day += dt.timedelta(days=1)

    def test_閏月は19年に約7回(self):
        """メトン周期。19太陽年 ≒ 235朔望月 = 12*19 + 7。

        実装が閏月を出しすぎ／出さなすぎなら、ここで必ず落ちる。
        """
        start, end = tables.SUPPORTED_RANGE
        leaps = 0
        day = start
        while day <= end:
            lunar = gregorian_to_lunar(day)
            if lunar.is_leap_month and lunar.day == 1:
                leaps += 1
            day += dt.timedelta(days=1)
        years = (end - start).days / 365.2422
        assert leaps == pytest.approx(years * 7 / 19, rel=0.05), leaps


class TestContinuity:
    def test_日は1ずつ増え月境界でリセットされる(self):
        start, end = tables.SUPPORTED_RANGE
        day = start
        previous = gregorian_to_lunar(day)
        while day < end:
            day += dt.timedelta(days=1)
            lunar = gregorian_to_lunar(day)
            if lunar.day == 1:
                assert previous.day in (29, 30), f"{day} 前日が{previous.day}日"
            else:
                assert lunar.day == previous.day + 1, f"{day}"
                assert lunar.month == previous.month, f"{day}"
            previous = lunar

    def test_月の長さは29日か30日(self):
        start, end = tables.SUPPORTED_RANGE
        day, length, lengths = start, 0, []
        while day <= end:
            lunar = gregorian_to_lunar(day)
            if lunar.day == 1 and length:
                lengths.append(length)
                length = 0
            length += 1
            day += dt.timedelta(days=1)
        assert set(lengths[1:]) <= {29, 30}, sorted(set(lengths))

    def test_月番号は1から12を巡回する(self):
        start, end = tables.SUPPORTED_RANGE
        day, seen = start, []
        while day <= end:
            lunar = gregorian_to_lunar(day)
            if lunar.day == 1:
                seen.append((lunar.month, lunar.is_leap_month))
            day += dt.timedelta(days=1)
        for (m1, _), (m2, leap2) in zip(seen, seen[1:]):
            expected = m1 if leap2 else m1 % 12 + 1
            assert m2 == expected, f"{m1}月 -> {'閏' if leap2 else ''}{m2}月"


class TestUndetermined:
    """2033年問題。天保暦の規則では閏月を一意に決められない区間。"""

    @pytest.mark.parametrize("day", ["2033-07-26", "2033-12-31", "2034-03-20"])
    def test_区間内はフラグが立つ(self, day):
        assert gregorian_to_lunar(d(day)).rule_undetermined

    @pytest.mark.parametrize("day", ["2033-07-25", "2034-03-21"])
    def test_区間外はフラグが立たない(self, day):
        assert not gregorian_to_lunar(d(day)).rule_undetermined

    def test_採用したのは閏11月案(self):
        """暦文協・KASI・香港天文台・koyomi8 が一致する案（ADR-0011 不変条件5）。"""
        start = d("2033-12-22")
        while gregorian_to_lunar(start).day != 1:
            start -= dt.timedelta(days=1)
        lunar = gregorian_to_lunar(start)
        assert (lunar.month, lunar.is_leap_month) == (11, True)


class TestRange:
    @pytest.mark.parametrize("day", ["1899-12-31", "2101-01-01"])
    def test_対応範囲外は拒否する(self, day):
        with pytest.raises(ValueError, match="対応範囲"):
            gregorian_to_lunar(d(day))

    @pytest.mark.parametrize("day", ["1900-01-01", "2100-12-31"])
    def test_境界は受け付ける(self, day):
        assert gregorian_to_lunar(d(day)).day >= 1


class TestMeridian:
    """境界子午線は暦法の性質。タイムゾーンではない（ADR-0011 不変条件2）。"""

    def test_2027年の旧正月は中国の春節と1日ずれる(self):
        """**中国の春節の一覧を日本の旧正月のアンカーに流用してはいけない**。

        2027年2月の朔は 2027-02-06 15:56 UTC。日本（UTC+9）では2月7日00:56、
        中国（UTC+8）では2月6日23:56。朔を含む日が1日なので、旧正月は
        日本＝2月7日、中国＝2月6日に分かれる。64分の差が月をまるごと動かす。
        """
        day = dt.date(2027, 2, 7)
        assert (gregorian_to_lunar(day).month, gregorian_to_lunar(day).day) == (1, 1)
        china = gregorian_to_lunar(dt.date(2027, 2, 6), offset_hours=8)
        assert (china.month, china.day) == (1, 1)

    def test_子午線を変えると日付が変わりうる(self):
        """中国式（UTC+8）と日本式（UTC+9）で朔日が1日ずれる年がある。"""
        start, end = tables.SUPPORTED_RANGE
        differs = 0
        day = start
        while day <= end:
            if gregorian_to_lunar(day).day != gregorian_to_lunar(
                    day, offset_hours=8).day:
                differs += 1
            day += dt.timedelta(days=365)
        assert differs > 0, "子午線を無視している疑い"
