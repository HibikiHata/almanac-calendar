"""月齢と輝面比。

**月齢と月の形は別物**。月齢は朔からの経過日数という時間の量で、形は
月と太陽の離角という角度の量。月の軌道が楕円で不等速なため、両者は
比例しない——望（満月）が起きる月齢は13.9〜15.6日の幅で動く。
月齢から線形に形を出すと、この幅ぶんの誤差がそのまま絵に出る。

そこで形は**四相（朔・上弦・望・下弦）の間を離角で補間**して出す。
四相ちょうどでは離角が 0/90/180/270度と厳密に決まっているので、
そこでは輝面比が 0/50/100/50% と誤差なく一致する。
"""

from __future__ import annotations

import datetime as dt

import pytest

from almanac_calendar.koyomi import tables
from almanac_calendar.koyomi.moon import (SYNODIC_MONTH, illumination, is_waxing,
                                 moon_age, phase_code_on)

JST = dt.timezone(dt.timedelta(hours=9))


def d(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


class TestMoonAge:
    def test_朔の日の月齢は0日台か29日台になる(self):
        """**旧暦1日でも月齢が29台になる日がある**。矛盾ではない。

        旧暦の日は日界（0時）で切り替わるのに対し、月齢は正午の値。
        朔が正午より後に起きる日は、正午時点ではまだ前の月の終わりなので
        29日台になる。市販の暦も同じ挙動をする。
        """
        for when in tables.new_moons()[:200]:
            day = when.astimezone(JST).date()
            if not tables.SUPPORTED_RANGE[0] <= day <= tables.SUPPORTED_RANGE[1]:
                continue
            age = moon_age(day)
            after_noon = when.astimezone(JST).hour >= 12
            assert (age > 28) if after_noon else (age < 1.5), f"{day} {age}"

    def test_月齢は朔望月の最大値を超えない(self):
        """平均の29.53は上限にならない。朔望月は29.27〜29.83日で動く。"""
        start, end = tables.SUPPORTED_RANGE
        day = start
        while day <= end:
            assert 0 <= moon_age(day) < 29.9, day
            day += dt.timedelta(days=97)

    def test_翌日の月齢は1日ぶん増えるか朔でリセットされる(self):
        day = d("2026-01-01")
        while day < d("2027-01-01"):
            a, b = moon_age(day), moon_age(day + dt.timedelta(days=1))
            assert b - a == pytest.approx(1.0, abs=1e-9) or b < a, day
            day += dt.timedelta(days=1)

    def test_範囲外は拒否する(self):
        with pytest.raises(ValueError, match="サポート範囲外"):
            moon_age(d("2101-01-01"))


class TestIllumination:
    @pytest.mark.parametrize("code,expected", [(0, 0.0), (1, 0.5), (2, 1.0), (3, 0.5)])
    def test_四相ちょうどでは厳密な値になる(self, code, expected):
        """補間の節点。ここがずれていたら補間の組み立てが誤っている。"""
        found = 0
        for when, c in tables.moon_phases():
            if c != code or when.year != 2026:
                continue
            assert illumination(when) == pytest.approx(expected, abs=1e-6)
            found += 1
        assert found >= 12

    def test_輝面比は0から1に収まる(self):
        day = d("2020-01-01")
        while day < d("2030-01-01"):
            noon = dt.datetime(day.year, day.month, day.day, 12, tzinfo=JST)
            assert 0.0 <= illumination(noon) <= 1.0, day
            day += dt.timedelta(days=11)

    def test_朔から望へ単調に増える(self):
        moons = [w for w, c in tables.moon_phases()
                 if c == 0 and w.year == 2026]
        full = [w for w, c in tables.moon_phases() if c == 2 and w.year == 2026]
        new, nxt = moons[0], next(w for w in full if w > moons[0])
        values = [illumination(new + (nxt - new) * i / 20) for i in range(21)]
        assert values == sorted(values)

    def test_望から朔へ単調に減る(self):
        full = [w for w, c in tables.moon_phases() if c == 2 and w.year == 2026]
        moons = [w for w, c in tables.moon_phases() if c == 0 and w.year == 2026]
        start, end = full[0], next(w for w in moons if w > full[0])
        values = [illumination(start + (end - start) * i / 20) for i in range(21)]
        assert values == sorted(values, reverse=True)

    def test_月齢からの線形近似とは有意にずれる(self):
        """線形近似で足りるなら四相テーブルは要らない。要ることを示す。

        月の軌道は楕円で不等速なため、同じ月齢でも輝面比は年によって違う。
        差が測定誤差程度なら、この実装は複雑さに見合っていない。
        """
        import math
        worst = 0.0
        day = d("2026-01-01")
        while day < d("2027-01-01"):
            noon = dt.datetime(day.year, day.month, day.day, 12, tzinfo=JST)
            linear = (1 - math.cos(2 * math.pi * moon_age(day) / SYNODIC_MONTH)) / 2
            worst = max(worst, abs(illumination(noon) - linear))
            day += dt.timedelta(days=1)
        assert worst > 0.01, f"最大差 {worst:.4f}——線形で十分だった"


class TestWaxing:
    def test_朔から望までは満ちる(self):
        moons = [w for w, c in tables.moon_phases() if c == 0 and w.year == 2026]
        full = next(w for w, c in tables.moon_phases()
                    if c == 2 and w > moons[0])
        assert is_waxing(moons[0] + (full - moons[0]) / 2)

    def test_望から朔までは欠ける(self):
        full = [w for w, c in tables.moon_phases() if c == 2 and w.year == 2026]
        new = next(w for w, c in tables.moon_phases() if c == 0 and w > full[0])
        assert not is_waxing(full[0] + (new - full[0]) / 2)


class TestPhaseCodeOnDay:
    def test_四相の日はコードを返しそれ以外はNone(self):
        got = {}
        for when, code in tables.moon_phases():
            day = when.astimezone(JST).date()
            if day.year == 2026:
                got[day] = code
        assert len(got) >= 48
        for day, code in got.items():
            assert phase_code_on(day) == code, day
        assert phase_code_on(d("2026-08-01")) in (None, *range(4))

    def test_節気と違い四相は必ず月に約4回ある(self):
        days = [day for day in (d("2026-01-01") + dt.timedelta(days=i)
                                for i in range(365))
                if phase_code_on(day) is not None]
        assert 46 <= len(days) <= 52, len(days)
