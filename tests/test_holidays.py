"""祝日。日本は法の規則として実装し、他国は生成済みテーブルを読む。

日本を自前にしている理由は**春分の日と秋分の日**。法律には日付が書かれておらず
「春分日」「秋分日」とだけ定められている。実体は天文現象なので、NAOJと全件
照合済みの節気テーブルから引く。近似式には寄らない。

日付の規則のほうは `holidays` ライブラリと1949〜2099年で全件照合してあり
（`_generate/verify_holidays_jp.py`）、ここでは**改正史の要所**を固定する。
「今の法律」だけ実装すると過去の月を描いたときに静かに嘘をつくため。
"""

from __future__ import annotations

import datetime as dt

import pytest

from almanac_calendar.calendar import render
from almanac_calendar.config import WidgetConfig
from almanac_calendar.koyomi.holidays_jp import holiday_name, holidays_in
from almanac_calendar.koyomi.publicholidays import available_countries
from almanac_calendar.koyomi.publicholidays import holiday_name as country_holiday
from almanac_calendar.svg.theme import THEMES


def d(text: str) -> dt.date:
    return dt.date.fromisoformat(text)


class TestEquinox:
    """法律に日付が無い2つ。節気テーブルから引けていること。"""

    @pytest.mark.parametrize("day", [
        "2024-03-20", "2025-03-20", "2026-03-20", "2027-03-21",
    ])
    def test_春分の日(self, day):
        assert holiday_name(d(day)) == "春分の日"

    @pytest.mark.parametrize("day", [
        "2024-09-22", "2025-09-23", "2026-09-23", "2027-09-23",
    ])
    def test_秋分の日(self, day):
        assert holiday_name(d(day)) == "秋分の日"

    def test_春分の日は年によって20日と21日を行き来する(self):
        days = {holidays_in(y).get(d(f"{y}-03-20")) for y in range(2020, 2060)}
        assert days == {"春分の日"} or None in days
        march21 = [y for y in range(1949, 2101)
                   if holidays_in(y).get(d(f"{y}-03-21")) == "春分の日"]
        assert march21, "常に3/20固定になっている。近似式に寄っている疑い"

    def test_ライブラリの上限を超えても出せる(self):
        """holidays の日本対応は2099年まで。節気テーブルは2100年まである。"""
        assert holiday_name(d("2100-03-20")) == "春分の日"


class TestLawHistory:
    """改正史。今の法律だけを実装すると過去が静かに狂う。"""

    def test_法施行前には祝日が無い(self):
        assert holidays_in(1947) == {}
        # 1948年は施行日（7/20）より後だけ
        assert all(day >= d("1948-07-20") for day in holidays_in(1948))

    def test_成人の日は2000年にハッピーマンデーへ移った(self):
        assert holiday_name(d("1999-01-15")) == "成人の日"
        assert holiday_name(d("2000-01-15")) is None
        assert holiday_name(d("2000-01-10")) == "成人の日"  # 第2月曜

    def test_天皇誕生日は3回動いている(self):
        assert holiday_name(d("1988-04-29")) == "天皇誕生日"
        assert holiday_name(d("1990-12-23")) == "天皇誕生日"
        assert holiday_name(d("2021-02-23")) == "天皇誕生日"

    def test_2019年には天皇誕生日が無い(self):
        """退位と即位の年。12/23はもう祝日でなく、2/23はまだ祝日でない。"""
        assert holiday_name(d("2019-12-23")) is None
        assert holiday_name(d("2019-02-23")) is None
        assert holiday_name(d("2019-05-01")) == "天皇の即位の日"

    def test_4月29日は名前が2度変わった(self):
        assert holiday_name(d("1988-04-29")) == "天皇誕生日"
        assert holiday_name(d("2000-04-29")) == "みどりの日"
        assert holiday_name(d("2010-04-29")) == "昭和の日"

    def test_山の日は2016年から(self):
        assert holiday_name(d("2015-08-11")) is None
        assert holiday_name(d("2016-08-11")) == "山の日"

    def test_五輪特例で祝日が動いた年がある(self):
        assert holiday_name(d("2021-08-08")) == "山の日"
        assert holiday_name(d("2021-08-11")) is None
        assert holiday_name(d("2020-07-23")) == "海の日"


class TestSubstitute:
    def test_振替休日は1973年から(self):
        """1972-01-01 は土曜なので、日曜に当たる古い例で確認する。"""
        before = [y for y in range(1950, 1973)
                  if d(f"{y}-05-03").weekday() == 6]
        for year in before:
            assert holiday_name(d(f"{year}-05-04")) is None, year

    def test_日曜の祝日は翌日に振り替わる(self):
        assert d("2026-05-03").weekday() == 6
        assert holiday_name(d("2026-05-06")) == "振替休日"

    def test_2007年から振替が連鎖する(self):
        """5/3が日曜なら5/4も5/5も祝日なので、振替は5/6まで送られる。"""
        assert holiday_name(d("2026-05-04")) == "みどりの日"
        assert holiday_name(d("2026-05-05")) == "こどもの日"
        assert holiday_name(d("2026-05-06")) == "振替休日"


class TestCitizensHoliday:
    def test_祝日に挟まれた平日は国民の休日になる(self):
        """2026年は敬老の日9/21と秋分の日9/23に挟まれて9/22が休みになる。"""
        assert holiday_name(d("2026-09-21")) == "敬老の日"
        assert holiday_name(d("2026-09-22")) == "国民の休日"
        assert holiday_name(d("2026-09-23")) == "秋分の日"

    def test_1988年より前には無い(self):
        assert all("国民の休日" not in v
                   for y in range(1949, 1988) for v in holidays_in(y).values())


class TestOtherCountries:
    def test_複数の国が使える(self):
        assert "JP" in available_countries()
        assert len(available_countries()) >= 5

    def test_米国の独立記念日(self):
        assert country_holiday(d("2026-07-04"), "US") is not None

    def test_国によって祝日が違う(self):
        day = d("2026-07-04")
        assert country_holiday(day, "US") is not None
        assert country_holiday(day, "JP") is None

    def test_韓国は旧正月が祝日(self):
        """2026年の旧正月は2/17。日本では祝日ではない。"""
        assert country_holiday(d("2026-02-17"), "KR") is not None
        assert country_holiday(d("2026-02-17"), "JP") is None

    def test_範囲外は黙って祝日なしにせず落とす(self):
        with pytest.raises(ValueError, match="祝日テーブル"):
            country_holiday(d("1990-01-01"), "US")

    def test_未生成の国は使えるものを挙げて落ちる(self):
        with pytest.raises(ValueError, match="祝日テーブルがありません"):
            country_holiday(d("2026-01-01"), "ZZ")


class TestConfig:
    def test_未対応の国コードは設定時に落ちる(self):
        with pytest.raises(ValueError, match="未対応の国コード"):
            WidgetConfig(holiday_country="ZZ")

    def test_名前だけ有効にはできない(self):
        with pytest.raises(ValueError, match="holiday_country"):
            WidgetConfig(show_holiday_names=True)


class TestRender:
    def out(self, **kwargs) -> str:
        return render(dt.date(2026, 5, 1), theme=THEMES["light"],
                      config=WidgetConfig(**kwargs)).decode("utf-8")

    def test_祝日は日曜と同じ色になる(self):
        plain = self.out().count(THEMES["light"].sunday)
        marked = self.out(holiday_country="JP").count(THEMES["light"].sunday)
        assert marked > plain

    def test_祝日名を注記行に出せる(self):
        out = self.out(holiday_country="JP", show_holiday_names=True)
        for name in ("憲法記念日", "みどりの日", "こどもの日", "振替休日"):
            assert name in out, name

    def test_祝日名は節気より優先される(self):
        """その日にしかなく、予定に直接効く情報なので最優先。"""
        out = render(dt.date(2026, 9, 1), theme=THEMES["light"],
                     config=WidgetConfig(holiday_country="JP",
                                         show_holiday_names=True,
                                         show_solar_terms=True,
                                         show_rokuyo=True)).decode("utf-8")
        assert "秋分の日" in out
        assert "秋分" not in out.replace("秋分の日", "")

    def test_国を変えると色の付く日が変わる(self):
        assert (self.out(holiday_country="JP").count(THEMES["light"].sunday)
                != self.out(holiday_country="US").count(THEMES["light"].sunday))
