"""六曜の写像。旧暦日から六曜を出すだけの全域関数。

**最も間違えやすい1行**なので、独立したテストで固定する。
暗誦順（先勝→友引→先負→仏滅→大安→赤口）は巡る順序であって
剰余の順序ではない。インデックス0は**大安**（ADR-0011 不変条件1）。
"""

from __future__ import annotations

import pytest

from almanac_calendar.koyomi.lunisolar import LunarDate
from almanac_calendar.koyomi.rokuyo import ROKUYO, rokuyo_of


def ld(month: int, day: int, *, leap: bool = False) -> LunarDate:
    return LunarDate(year=2026, month=month, day=day, is_leap_month=leap,
                     rule_undetermined=False)


class TestOrder:
    def test_インデックス0は大安(self):
        # 暗誦順の先勝ではない。誤ると全日4つずれる
        assert ROKUYO[0] == "大安"

    def test_6種そろっている(self):
        assert set(ROKUYO) == {"大安", "赤口", "先勝", "友引", "先負", "仏滅"}
        assert len(ROKUYO) == 6

    def test_剰余の順序(self):
        assert ROKUYO == ("大安", "赤口", "先勝", "友引", "先負", "仏滅")


class TestAnchors:
    """各月の朔日（1日）の六曜。出典の法則と一致すること。"""

    @pytest.mark.parametrize("month,expected", [
        (1, "先勝"), (2, "友引"), (3, "先負"), (4, "仏滅"), (5, "大安"), (6, "赤口"),
        (7, "先勝"), (8, "友引"), (9, "先負"), (10, "仏滅"), (11, "大安"), (12, "赤口"),
    ])
    def test_朔日の六曜(self, month, expected):
        assert rokuyo_of(ld(month, 1)) == expected

    @pytest.mark.parametrize("month,day,expected,label", [
        (11, 15, "先勝", "七五三"),
        (1, 15, "先負", "元服"),
        (1, 7, "先勝", "人日"),
        (3, 3, "大安", "桃の節句"),
        (5, 5, "先負", "菖蒲の節句"),
        (7, 7, "先勝", "七夕"),
        (9, 9, "大安", "重陽"),
        (8, 15, "仏滅", "十五夜"),
        (9, 13, "先負", "十三夜"),
    ])
    def test_年中行事の六曜(self, month, day, expected, label):
        assert rokuyo_of(ld(month, day)) == expected, label


class TestProgression:
    def test_月の中では1日ごとに1つ進む(self):
        for month in range(1, 13):
            for day in range(1, 29):
                a = ROKUYO.index(rokuyo_of(ld(month, day)))
                b = ROKUYO.index(rokuyo_of(ld(month, day + 1)))
                assert (b - a) % 6 == 1, f"{month}月{day}日"

    def test_月境界では飛ぶ(self):
        """六曜は旧暦の月ごとにリセットされる。

        月は29日か30日で6の倍数ではないため、境界で必ず不連続になる。
        これが「六曜の順番が飛ぶ」の正体で、仕様どおりの挙動。
        """
        for last in (29, 30):
            end = ROKUYO.index(rokuyo_of(ld(3, last)))
            nxt = ROKUYO.index(rokuyo_of(ld(4, 1)))
            assert (nxt - end) % 6 != 1, f"{last}日の月で飛んでいない"


class TestLeapMonth:
    def test_閏月は前月と同じ月番号で計算する(self):
        # is_leap_month は意図的に使わない。「使っていない＝バグ」と
        # 誤解して修正されるのを防ぐため、テストで固定する
        for day in (1, 15, 29):
            assert rokuyo_of(ld(3, day, leap=True)) == rokuyo_of(ld(3, day, leap=False))

    def test_閏月の翌月は番号が進む(self):
        assert rokuyo_of(ld(4, 1)) != rokuyo_of(ld(3, 1, leap=True))


class TestExhaustive:
    def test_全ての月日で6種のいずれかを返す(self):
        for month in range(1, 13):
            for day in range(1, 31):
                assert rokuyo_of(ld(month, day)) in ROKUYO

    def test_周期を網羅する(self):
        got = {rokuyo_of(ld(1, d)) for d in range(1, 7)}
        assert got == set(ROKUYO)


class TestGuards:
    @pytest.mark.parametrize("month,day", [(0, 1), (13, 1), (1, 0), (1, 31)])
    def test_範囲外は拒否する(self, month, day):
        with pytest.raises(ValueError):
            LunarDate(year=2026, month=month, day=day,
                      is_leap_month=False, rule_undetermined=False)
