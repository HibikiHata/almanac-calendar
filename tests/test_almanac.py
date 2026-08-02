"""暦注（選日）。吉日と凶日。

**天文計算は増えない**。日の干支・節月・旧暦の月日という既にある3つの
組み合わせで機械的に決まる。誤りが入る余地は表の転記だけなので、
表そのものと、公表値との突き合わせを固定する。

日の干支は60日周期の剰余しかないので、**離れた4点で基準が一致すれば
全期間が決まる**。その4点を韓国天文研究院の日辰（LUNC_ILJIN）から取り、
ここに残してある。
"""

from __future__ import annotations

import datetime as dt

import pytest

from almanac_calendar.koyomi.almanac import (ICHIRYU_I, ICHIRYU_II, almanac_of, short)
from almanac_calendar.koyomi.sexagenary import (BRANCHES, MANSIONS, STEMS,
                                       day_sexagenary, mansion, season,
                                       solar_month)


def d(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


class TestSexagenary:
    #: 韓国天文研究院の日辰。60日周期なので、離れた4点が合えば全期間決まる
    KASI_ANCHORS = {
        "1900-01-01": "甲戌",
        "2000-02-29": "丁巳",
        "2026-08-02": "戊申",
        "2050-12-31": "乙酉",
    }

    @pytest.mark.parametrize("day,expected", sorted(KASI_ANCHORS.items()))
    def test_日の干支が韓国天文研究院と一致する(self, day, expected):
        assert day_sexagenary(d(day)) == expected

    def test_60日で一巡する(self):
        base = d("2026-01-01")
        assert day_sexagenary(base) == day_sexagenary(base + dt.timedelta(days=60))
        for gap in (1, 10, 12, 30, 59):
            assert day_sexagenary(base) != day_sexagenary(
                base + dt.timedelta(days=gap)), gap

    def test_60通りすべてが現れる(self):
        base = d("2026-01-01")
        got = {day_sexagenary(base + dt.timedelta(days=i)) for i in range(60)}
        assert len(got) == 60

    def test_十干と十二支の組は偶奇が揃う(self):
        """甲子・乙丑…と進むので、十干と十二支の偶奇は必ず一致する。

        甲丑のような組み合わせは60干支に存在しない。
        """
        base = d("2026-01-01")
        for i in range(60):
            g = day_sexagenary(base + dt.timedelta(days=i))
            assert STEMS.index(g[0]) % 2 == BRANCHES.index(g[1]) % 2, g


class TestSolarMonth:
    """節月は節切り。旧暦の月とは別物で、境界は中気ではなく節。"""

    @pytest.mark.parametrize("day,expected", [
        ("2026-02-03", 12),   # 立春の前日はまだ十二月
        ("2026-02-04", 1),    # 立春から正月
        ("2026-08-06", 6),    # 立秋の前日
        ("2026-08-07", 7),    # 立秋から七月
    ])
    def test_節で切り替わる(self, day, expected):
        assert solar_month(d(day)) == expected

    def test_季節も節切り(self):
        assert season(d("2026-02-03")) == "冬"
        assert season(d("2026-02-04")) == "春"

    def test_1年で12ヶ月すべてを通る(self):
        got = {solar_month(d("2026-01-01") + dt.timedelta(days=i))
               for i in range(365)}
        assert got == set(range(1, 13))


class TestPublishedValues:
    """公表されている2026年の値と突き合わせる。

    天赦日・一粒万倍日・不成就日・寅の日が同時に確かめられる。
    """

    def test_2026年の天赦日は6日(self):
        got = [day.isoformat() for day in _year_days(2026)
               if "天赦日" in almanac_of(day).lucky]
        assert got == ["2026-03-05", "2026-05-04", "2026-05-20",
                       "2026-07-19", "2026-10-01", "2026-12-16"]

    def test_天赦日と一粒万倍日が重なる日(self):
        got = [day.isoformat() for day in _year_days(2026)
               if {"天赦日", "一粒万倍日"} <= set(almanac_of(day).lucky)]
        assert got == ["2026-03-05", "2026-07-19", "2026-10-01", "2026-12-16"]

    def test_7月19日は不成就日も重なる(self):
        """公表側が「最強開運日」から除外している理由。"""
        assert "不成就日" in almanac_of(d("2026-07-19")).unlucky

    def test_3月5日は寅の日でもある(self):
        assert "寅の日" in almanac_of(d("2026-03-05")).lucky


def _year_days(year: int):
    day = dt.date(year, 1, 1)
    while day.year == year:
        yield day
        day += dt.timedelta(days=1)


class TestMansions:
    """二十八宿。28日周期を回すだけだが、**基準が1日ずれても一見わからない**。

    28は7の倍数なので、宿と曜日の対応は永久に固定される。鬼宿が常に金曜で
    あることが、基準のずれを検出する最も安いテスト。
    """

    def test_2026年の鬼宿日は公表値と一致する(self):
        got = [day.isoformat() for day in _year_days(2026) if mansion(day) == "鬼"]
        assert got == ["2026-01-02", "2026-01-30", "2026-02-27", "2026-03-27",
                       "2026-04-24", "2026-05-22", "2026-06-19", "2026-07-17",
                       "2026-08-14", "2026-09-11", "2026-10-09", "2026-11-06",
                       "2026-12-04"]

    @pytest.mark.parametrize("year", [1900, 2000, 2026, 2050, 2100])
    def test_鬼宿は常に金曜(self, year):
        """基準が1日ずれるとここが木曜か土曜に変わる。"""
        days = [day for day in _year_days(year) if mansion(day) == "鬼"]
        assert {day.strftime("%a") for day in days} == {"Fri"}, year

    def test_28日で一巡する(self):
        base = d("2026-01-01")
        assert mansion(base) == mansion(base + dt.timedelta(days=28))
        got = {mansion(base + dt.timedelta(days=i)) for i in range(28)}
        assert got == set(MANSIONS)

    def test_鬼宿日は年13回前後(self):
        for year in (2026, 2027, 2028):
            days = [day for day in _year_days(year)
                    if "鬼宿日" in almanac_of(day).lucky]
            assert 12 <= len(days) <= 14, (year, len(days))

    def test_節気にも旧暦にも依存しない(self):
        """周期を回すだけなので、暦の他の層が変わっても影響を受けない。"""
        base = d("2026-01-01")
        for i in range(0, 400, 7):
            day = base + dt.timedelta(days=i)
            assert mansion(day) == MANSIONS[(day.toordinal() + 24) % 28]


class TestTables:
    def test_表Ⅰは節月ごとに2つ(self):
        assert all(len(v) == 2 for v in ICHIRYU_I.values())

    def test_表Ⅱは節月ごとに1つで逆順に巡る(self):
        assert all(len(v) == 1 for v in ICHIRYU_II.values())
        order = [v[0] for v in ICHIRYU_II.values()]
        indexes = [BRANCHES.index(b) for b in order]
        for a, b in zip(indexes, indexes[1:]):
            assert (a - b) % 12 == 1, order

    def test_選日法を替えると日が変わる(self):
        days_i = {day for day in _year_days(2026)
                  if "一粒万倍日" in almanac_of(day).lucky}
        days_ii = {day for day in _year_days(2026)
                   if "一粒万倍日" in almanac_of(day, ichiryu_table="II").lucky}
        assert days_i != days_ii
        assert len(days_i) > len(days_ii), "表Ⅱは月1つなので少ないはず"

    def test_未対応の選日法は拒否する(self):
        with pytest.raises(ValueError, match="選日法"):
            almanac_of(d("2026-01-01"), ichiryu_table="III")


class TestFrequency:
    def test_寅の日と巳の日は12日ごと(self):
        """巳の日は己巳の日と足して数える。

        己巳（60日ごと）は巳の日のうち特別なものなので、実装は別名で
        返す。片方だけ数えると年24日になり「12日ごと」に見えなくなる。
        """
        for names in (("寅の日",), ("巳の日", "己巳の日")):
            days = [day for day in _year_days(2026)
                    if set(names) & set(almanac_of(day).lucky)]
            assert 28 <= len(days) <= 32, (names, len(days))

    def test_己巳の日は年5から6回(self):
        days = [day for day in _year_days(2026)
                if "己巳の日" in almanac_of(day).lucky]
        assert 5 <= len(days) <= 7, len(days)

    def test_己巳の日は巳の日と二重計上しない(self):
        for day in _year_days(2026):
            lucky = almanac_of(day).lucky
            assert not ("己巳の日" in lucky and "巳の日" in lucky), day

    def test_不成就日は年48日前後(self):
        days = [day for day in _year_days(2026)
                if "不成就日" in almanac_of(day).unlucky]
        assert 44 <= len(days) <= 52, len(days)


class TestShort:
    def test_略記は2文字に揃う(self):
        """マス幅40pxに9px×5字の「一粒万倍日」は入らない。"""
        for name in ("天赦日", "一粒万倍日", "不成就日", "三隣亡", "受死日"):
            assert len(short(name)) == 2, name

    def test_未登録の名前はそのまま返す(self):
        assert short("大安") == "大安"
