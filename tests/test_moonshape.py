"""月の形のSVGパス。

図形なので目視が要るが、目視できない性質は自動で押さえる。
面積は**多角形近似して数値積分**で測る——パスの文字列を睨んでも
「本当に三日月の形か」は分からないため。
"""

from __future__ import annotations

import math
import re

import pytest

from almanac_calendar.svg.moonshape import moon_path


def sample_area(fraction: float, waxing: bool = True, *, steps: int = 2000) -> float:
    """パスが囲む面積を、2本の弧を離散化して測る（半径1に正規化）。

    パスを解釈し直すのではなく、**同じ幾何をこのテスト側で独立に
    組み立てて**面積を出す。実装の式をコピーすると、式が間違っていても
    テストが通ってしまう。
    """
    m = re.fullmatch(
        r"M([\d.-]+),([\d.-]+)"
        r"A([\d.-]+),([\d.-]+) 0 0,(\d) ([\d.-]+),([\d.-]+)"
        r"A([\d.-]+),([\d.-]+) 0 0,(\d) ([\d.-]+),([\d.-]+)Z",
        moon_path(cx=0, cy=0, r=1, fraction=fraction, waxing=waxing))
    assert m, "パスの形が想定と違う"
    limb_sweep, rx, term_sweep = int(m.group(5)), float(m.group(8)), int(m.group(10))

    def arc(radius_x: float, side: int) -> list[tuple[float, float]]:
        """上(0,-1)から下(0,1)への半弧。`side` は +1で右、-1で左を通る。"""
        return [(side * radius_x * math.sin(math.pi * i / steps),
                 -math.cos(math.pi * i / steps)) for i in range(steps + 1)]

    # **sweepフラグと通過側の対応は弧の向きで逆になる**。sweep=1 は常に
    # 時計回りだが、1本目は上→下（時計回り＝右）、2本目は下→上
    # （時計回り＝左）に描かれるため。ここを揃えると三日月の面積が
    # 満月と同じになり、それでもパス文字列は正しく見える
    points = (arc(1.0, 1 if limb_sweep else -1)
              + list(reversed(arc(rx, -1 if term_sweep else 1))))
    area = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        area += x1 * y2 - x2 * y1
    return abs(area) / 2


class TestArea:
    """輝面比fの面積は、円の面積 π のちょうど f 倍になるはず。"""

    @pytest.mark.parametrize("fraction", [0.0, 0.125, 0.25, 0.5, 0.75, 0.875, 1.0])
    def test_面積は輝面比に比例する(self, fraction):
        assert sample_area(fraction) == pytest.approx(math.pi * fraction, abs=0.01)

    def test_朔は面積0(self):
        assert sample_area(0.0) == pytest.approx(0.0, abs=1e-6)

    def test_望は真円(self):
        assert sample_area(1.0) == pytest.approx(math.pi, abs=1e-3)

    def test_上弦は半円(self):
        assert sample_area(0.5) == pytest.approx(math.pi / 2, abs=1e-3)

    def test_欠ける側も面積は同じ(self):
        for fraction in (0.2, 0.5, 0.8):
            assert sample_area(fraction, waxing=False) == pytest.approx(
                sample_area(fraction, waxing=True), abs=1e-6)


class TestOrientation:
    def test_満ちる側は右が輝く(self):
        """北半球の見え方。三日月の膨らみが右にあること。"""
        path = moon_path(cx=0, cy=0, r=10, fraction=0.25, waxing=True)
        assert "0,1 0,10" in path, path

    def test_欠ける側は左が輝く(self):
        path = moon_path(cx=0, cy=0, r=10, fraction=0.25, waxing=False)
        assert "0,0 0,10" in path, path

    def test_半月をまたぐと膨らむ向きが反転する(self):
        thin = moon_path(cx=0, cy=0, r=10, fraction=0.4, waxing=True)
        fat = moon_path(cx=0, cy=0, r=10, fraction=0.6, waxing=True)
        assert thin[-14:] != fat[-14:], "sweepフラグが変わっていない"


class TestGuards:
    @pytest.mark.parametrize("fraction", [-0.01, 1.01])
    def test_範囲外の輝面比は拒否する(self, fraction):
        with pytest.raises(ValueError, match="輝面比"):
            moon_path(cx=0, cy=0, r=5, fraction=fraction, waxing=True)

    @pytest.mark.parametrize("r", [0, -1])
    def test_非正の半径は拒否する(self, r):
        with pytest.raises(ValueError, match="半径"):
            moon_path(cx=0, cy=0, r=r, fraction=0.5, waxing=True)


class TestDeterminism:
    def test_同じ入力は同じ文字列(self):
        args = dict(cx=20, cy=17.5, r=4.5, fraction=1 / 3, waxing=True)
        assert moon_path(**args) == moon_path(**args)

    def test_座標の桁が固定されている(self):
        path = moon_path(cx=20, cy=17.5, r=4.5, fraction=1 / 3, waxing=True)
        for number in re.findall(r"[\d.]+", path):
            if "." in number:
                assert len(number.split(".")[1]) <= 3, number
