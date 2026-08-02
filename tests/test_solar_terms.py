"""二十四節気の定義表。

天文計算はまだ無く、ここで固定するのは表そのものの整合性。
出典は大阪市立科学館「旧暦をつくろう」の二十四節気表と国立天文台 暦Wiki。
"""

from __future__ import annotations

import pytest

from almanac_calendar.koyomi.solar_terms import (
    ANCHORS,
    CHUKI,
    SOLAR_TERMS,
    all_characters,
    chuki_for_month,
    term_by_longitude,
)


class TestTable:
    def test_24個ある(self):
        assert len(SOLAR_TERMS) == 24

    def test_黄経は15度刻みで重複しない(self):
        longs = [t.longitude for t in SOLAR_TERMS]
        assert len(set(longs)) == 24
        assert sorted(longs) == list(range(0, 360, 15))

    def test_中気は12個で30度の倍数(self):
        assert len(CHUKI) == 12
        for term in CHUKI:
            assert term.longitude % 30 == 0, term.name

    def test_節気は30度の倍数ではない(self):
        for term in SOLAR_TERMS:
            if not term.is_chuki:
                assert term.longitude % 30 != 0, term.name

    def test_中気は旧暦の各月に1対1で対応する(self):
        assert sorted(t.chuki_month for t in CHUKI) == list(range(1, 13))

    def test_全ての名前と読みが埋まっている(self):
        for term in SOLAR_TERMS:
            assert term.name and term.reading, term


class TestKnownValues:
    """出典の表と一致すること。"""

    @pytest.mark.parametrize("name,longitude,month", [
        ("春分", 0, 2),      # 二至二分
        ("夏至", 90, 5),
        ("秋分", 180, 8),
        ("冬至", 270, 11),
        ("雨水", 330, 1),    # 正月中気
        ("大寒", 300, 12),
        ("穀雨", 30, 3),
        ("小満", 60, 4),
        ("大暑", 120, 6),
        ("処暑", 150, 7),
        ("霜降", 210, 9),
        ("小雪", 240, 10),
    ])
    def test_中気の黄経と月(self, name, longitude, month):
        term = chuki_for_month(month)
        assert term.name == name
        assert term.longitude == longitude

    @pytest.mark.parametrize("name,longitude", [
        ("立春", 315), ("啓蟄", 345), ("清明", 15), ("立夏", 45),
        ("芒種", 75), ("小暑", 105), ("立秋", 135), ("白露", 165),
        ("寒露", 195), ("立冬", 225), ("大雪", 255), ("小寒", 285),
    ])
    def test_節気の黄経(self, name, longitude):
        assert term_by_longitude(longitude).name == name
        assert not term_by_longitude(longitude).is_chuki


class TestAnchors:
    def test_二至二分の4つ(self):
        assert ANCHORS == {"春分": 2, "夏至": 5, "秋分": 8, "冬至": 11}

    def test_アンカーは中気の対応表と矛盾しない(self):
        # アンカーは特別扱いだが、通常の中気→月の対応と同じ値であること
        for name, month in ANCHORS.items():
            assert chuki_for_month(month).name == name


class TestLookups:
    def test_範囲外の月は拒否する(self):
        for month in (0, 13):
            with pytest.raises(ValueError):
                chuki_for_month(month)

    def test_節気に対応しない黄経は拒否する(self):
        with pytest.raises(ValueError):
            term_by_longitude(7)

    def test_360度は0度と同じ(self):
        assert term_by_longitude(360).name == "春分"


class TestCharacters:
    def test_節気名の文字を返す(self):
        chars = all_characters()
        for ch in "立春雨水啓蟄分冬至":
            assert ch in chars, ch

    def test_重複がなく決定的(self):
        a, b = all_characters(), all_characters()
        assert a == b == "".join(sorted(set(a)))

    def test_フォントのcharsetに含まれている(self):
        # 節気名を描けるようサブセットに入っていること
        from almanac_calendar.charset import required_charset

        cs = required_charset()
        missing = [ch for ch in all_characters() if ch not in cs]
        assert not missing, f"charset.py に不足: {''.join(missing)}"
