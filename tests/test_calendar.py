"""カレンダーのグリッド計算と描画。

S1 の範囲は「素の月グリッド」まで。今日の強調は S3、六曜は S4。
ここで固定するのは、グレゴリオ暦の月の形が全パターンで正しいことと、
描画が決定的であることの2点。
"""

from __future__ import annotations

from datetime import date

import pytest

from almanac_calendar.config import WidgetConfig
from almanac_calendar.svg.theme import THEMES
from almanac_calendar.calendar import month_grid, render, render_pair


class TestMonthGrid:
    def test_通常の月(self):
        # 2026-08-01 は土曜。日曜始まりなので先頭に6個の空白が入る
        weeks = month_grid(date(2026, 8, 1), week_start="sunday")
        assert weeks[0] == [0, 0, 0, 0, 0, 0, 1]
        assert weeks[-1][-1] == 0 or weeks[-1][-1] == 31
        assert max(d for w in weeks for d in w) == 31

    def test_平年の2月は28日(self):
        weeks = month_grid(date(2026, 2, 1), week_start="sunday")
        assert max(d for w in weeks for d in w) == 28

    def test_閏年の2月は29日(self):
        weeks = month_grid(date(2028, 2, 1), week_start="sunday")
        assert max(d for w in weeks for d in w) == 29

    def test_100年ルール_1900年は閏年でない(self):
        weeks = month_grid(date(1900, 2, 1), week_start="sunday")
        assert max(d for w in weeks for d in w) == 28

    def test_400年ルール_2000年は閏年(self):
        weeks = month_grid(date(2000, 2, 1), week_start="sunday")
        assert max(d for w in weeks for d in w) == 29

    def test_月曜始まりに切り替わる(self):
        # 2026-08-01 は土曜。月曜始まりなら先頭に5個の空白
        weeks = month_grid(date(2026, 8, 1), week_start="monday")
        assert weeks[0] == [0, 0, 0, 0, 0, 1, 2]

    def test_全ての週が7要素(self):
        for month in range(1, 13):
            for start in ("sunday", "monday"):
                weeks = month_grid(date(2026, month, 1), week_start=start)
                assert all(len(w) == 7 for w in weeks)

    def test_日付が重複も欠落もしない(self):
        import calendar as _cal

        for year in (1900, 2000, 2026, 2028, 2100):
            for month in range(1, 13):
                weeks = month_grid(date(year, month, 1), week_start="sunday")
                days = [d for w in weeks for d in w if d]
                expected = _cal.monthrange(year, month)[1]
                assert days == list(range(1, expected + 1))

    def test_月内のどの日を渡しても同じ月グリッドになる(self):
        a = month_grid(date(2026, 8, 1), week_start="sunday")
        b = month_grid(date(2026, 8, 31), week_start="sunday")
        assert a == b

    def test_未知の週開始は拒否する(self):
        with pytest.raises(ValueError):
            month_grid(date(2026, 8, 1), week_start="tuesday")


class TestRender:
    def _cfg(self, **kw) -> WidgetConfig:
        return WidgetConfig(**kw)

    def test_バイト列を返す(self):
        out = render(date(2026, 8, 15), theme=THEMES["light"], config=self._cfg())
        assert isinstance(out, bytes)
        assert out.startswith(b"<svg")

    def test_同じ入力なら同じバイト列(self):
        args = dict(theme=THEMES["light"], config=self._cfg())
        assert render(date(2026, 8, 15), **args) == render(date(2026, 8, 15), **args)

    def test_テーマが違えば出力が違う(self):
        cfg = self._cfg()
        light = render(date(2026, 8, 15), theme=THEMES["light"], config=cfg)
        dark = render(date(2026, 8, 15), theme=THEMES["dark"], config=cfg)
        assert light != dark

    def test_月内の全日で同じ絵になる(self):
        # S1 では「今日」を描かないので、同じ月なら日が変わっても同一
        cfg = self._cfg()
        a = render(date(2026, 8, 1), theme=THEMES["light"], config=cfg)
        b = render(date(2026, 8, 31), theme=THEMES["light"], config=cfg)
        assert a == b

    def test_日本語ロケールの曜日が入る(self):
        out = render(date(2026, 8, 15), theme=THEMES["light"], config=self._cfg()).decode()
        for wd in "日月火水木金土":
            assert f">{wd}<" in out

    def test_英語ロケールに切り替わる(self):
        cfg = self._cfg(locale="en")
        out = render(date(2026, 8, 15), theme=THEMES["light"], config=cfg).decode()
        assert ">Sun<" in out
        assert ">日<" not in out

    def test_全ての日付が描かれる(self):
        out = render(date(2026, 8, 15), theme=THEMES["light"], config=self._cfg()).decode()
        for day in range(1, 32):
            assert f">{day}<" in out

    def test_タイトルに年月が入る(self):
        out = render(date(2026, 8, 15), theme=THEMES["light"], config=self._cfg()).decode()
        assert "2026" in out and "8" in out

    def test_システムクロックを読まない(self, monkeypatch):
        # date.today() を壊しても描画できること＝クロック非依存の証明
        import almanac_calendar.calendar as mod

        class Boom:
            @staticmethod
            def today():
                raise AssertionError("render がシステムクロックを読んだ")

        monkeypatch.setattr(mod, "date", Boom, raising=False)
        render(date(2026, 8, 15), theme=THEMES["light"], config=self._cfg())


class TestRenderPair:
    def test_light_dark_スニペットの3つを返す(self):
        pair = render_pair(date(2026, 8, 15), config=WidgetConfig())
        assert pair.light.startswith(b"<svg")
        assert pair.dark.startswith(b"<svg")
        assert pair.light != pair.dark
        assert "<picture>" in pair.snippet

    def test_スニペットが両方のファイルを参照する(self):
        pair = render_pair(date(2026, 8, 15), config=WidgetConfig(artifact_base_url="https://example.com/o"))
        assert "https://example.com/o/calendar-light.svg" in pair.snippet
        assert "https://example.com/o/calendar-dark.svg" in pair.snippet

    def test_スニペットのaltに年月が入る(self):
        pair = render_pair(date(2026, 8, 15), config=WidgetConfig())
        assert "2026" in pair.snippet
