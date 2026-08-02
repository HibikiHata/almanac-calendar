"""CLI と「今日」の決め方。

ここが守る性質は1つ。**ホストのタイムゾーンに依存しないこと**。
GitHub Actions のランナーは UTC で動くため、素直に date.today() を書くと
JSTの0時〜9時のあいだ前日を「今日」として描き続ける。日次cronの実行時刻次第で
恒常的にずれるので、設定されたタイムゾーンから導くことをここで固定する。
"""

from __future__ import annotations

import os
import time
from datetime import date, datetime, timezone

import pytest

from almanac_calendar.__main__ import main, resolve_today
from almanac_calendar.config import WidgetConfig


class TestResolveToday:
    def test_JSTの暦日を返す(self):
        # 2026-08-15 23:00 UTC は JST では 08-16
        now = datetime(2026, 8, 15, 23, 0, tzinfo=timezone.utc)
        assert resolve_today("Asia/Tokyo", now=now) == date(2026, 8, 16)

    def test_UTCの暦日を返す(self):
        now = datetime(2026, 8, 15, 23, 0, tzinfo=timezone.utc)
        assert resolve_today("UTC", now=now) == date(2026, 8, 15)

    def test_ニューヨークの暦日を返す(self):
        now = datetime(2026, 8, 15, 2, 0, tzinfo=timezone.utc)
        assert resolve_today("America/New_York", now=now) == date(2026, 8, 14)

    def test_境界_JSTの真夜中直後(self):
        now = datetime(2026, 8, 14, 15, 1, tzinfo=timezone.utc)  # JST 08-15 00:01
        assert resolve_today("Asia/Tokyo", now=now) == date(2026, 8, 15)

    def test_境界_JSTの真夜中直前(self):
        now = datetime(2026, 8, 14, 14, 59, tzinfo=timezone.utc)  # JST 08-14 23:59
        assert resolve_today("Asia/Tokyo", now=now) == date(2026, 8, 14)

    def test_naiveなnowは拒否する(self):
        with pytest.raises(ValueError):
            resolve_today("Asia/Tokyo", now=datetime(2026, 8, 15, 23, 0))


class TestHostTimezoneIndependence:
    """同じ瞬間なら、ホストのTZが何であっても結果が変わらないこと。"""

    def _with_tz(self, tz: str, fn):
        old = os.environ.get("TZ")
        os.environ["TZ"] = tz
        time.tzset()
        try:
            return fn()
        finally:
            if old is None:
                os.environ.pop("TZ", None)
            else:
                os.environ["TZ"] = old
            time.tzset()

    def test_UTCホストとNYホストで同じ結果(self):
        now = datetime(2026, 8, 15, 23, 0, tzinfo=timezone.utc)
        a = self._with_tz("UTC", lambda: resolve_today("Asia/Tokyo", now=now))
        b = self._with_tz("America/New_York", lambda: resolve_today("Asia/Tokyo", now=now))
        assert a == b == date(2026, 8, 16)

    def test_描画結果もホストTZに依存しない(self):
        from almanac_calendar.svg.theme import THEMES
        from almanac_calendar.calendar import render

        target = date(2026, 8, 15)
        cfg = WidgetConfig()
        a = self._with_tz("UTC", lambda: render(target, theme=THEMES["light"], config=cfg))
        b = self._with_tz("America/New_York", lambda: render(target, theme=THEMES["light"], config=cfg))
        assert a == b


class TestCli:
    def test_2枚のSVGとスニペットを書き出す(self, tmp_path):
        code = main(["--month", "2026-08", "--out", str(tmp_path)])
        assert code == 0
        assert (tmp_path / "calendar-light.svg").exists()
        assert (tmp_path / "calendar-dark.svg").exists()
        assert (tmp_path / "calendar.html").exists()

    def test_再実行してもバイト列が変わらない(self, tmp_path):
        main(["--month", "2026-08", "--out", str(tmp_path)])
        first = (tmp_path / "calendar-light.svg").read_bytes()
        main(["--month", "2026-08", "--out", str(tmp_path)])
        assert (tmp_path / "calendar-light.svg").read_bytes() == first

    def test_月の指定が不正なら異常終了(self, tmp_path):
        assert main(["--month", "2026-13", "--out", str(tmp_path)]) != 0

    def test_週開始を切り替えられる(self, tmp_path):
        main(["--month", "2026-08", "--out", str(tmp_path), "--week-start", "monday"])
        a = (tmp_path / "calendar-light.svg").read_bytes()
        main(["--month", "2026-08", "--out", str(tmp_path), "--week-start", "sunday"])
        assert (tmp_path / "calendar-light.svg").read_bytes() != a

    def test_ロケールを切り替えられる(self, tmp_path):
        main(["--month", "2026-08", "--out", str(tmp_path), "--locale", "en"])
        assert b"Sun" in (tmp_path / "calendar-light.svg").read_bytes()
