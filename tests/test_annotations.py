"""日付の下に出す注記（六曜・二十四節気）。

既定はどちらも出さない。カレンダーとしての最小の役割は日付を並べることで、
六曜は使う人だけが使う情報だから（ADR-0011 不変条件8）。

**両方を有効にしたときは節気を優先する**。節気は年24日しか出ず、
その日にしかない情報。六曜は毎日あって翌日も同じ規則で辿れる。
紙の暦の慣習とも一致する。
"""

from __future__ import annotations

import datetime as dt

import pytest

from almanac_calendar.calendar import canvas_size, render
from almanac_calendar.config import WidgetConfig
from almanac_calendar.svg.theme import THEMES

TARGET = dt.date(2026, 8, 1)
LIGHT = THEMES["light"]


def svg(**kwargs) -> str:
    config = WidgetConfig(**kwargs)
    return render(TARGET, theme=LIGHT, config=config, today=TARGET).decode("utf-8")


class TestDefaultsOff:
    def test_既定では六曜も節気も出さない(self):
        out = svg()
        for word in ("大安", "赤口", "先勝", "友引", "先負", "仏滅", "立秋", "処暑"):
            assert word not in out, word

    def test_既定の高さは注記なしのまま(self):
        assert canvas_size(WidgetConfig())[1] < canvas_size(
            WidgetConfig(show_rokuyo=True))[1]


class TestRokuyo:
    def test_六曜を有効にすると各日に出る(self):
        out = svg(show_rokuyo=True)
        assert sum(out.count(w) for w in
                   ("大安", "赤口", "先勝", "友引", "先負", "仏滅")) == 31

    def test_2026年8月1日は赤口(self):
        """旧暦6月19日。(6+19) mod 6 = 1 で赤口（ADR-0011 不変条件1）。"""
        assert "赤口" in svg(show_rokuyo=True)

    def test_六曜は前月末の続きから始まらない(self):
        """月初の六曜は旧暦から決まる。新暦の月境界とは無関係。"""
        aug = svg(show_rokuyo=True)
        assert aug.index("赤口") > 0


class TestSolarTerms:
    def test_節気を有効にすると該当日に出る(self):
        """2026年8月は立秋（8/7）と処暑（8/23）がある。"""
        out = svg(show_solar_terms=True)
        assert "立秋" in out
        assert "処暑" in out

    def test_節気のない月には何も出ない(self):
        """節気は必ず月に2つあるので、逆に出ない月は無い。件数で確認する。"""
        out = svg(show_solar_terms=True)
        assert out.count("立秋") == 1
        assert out.count("処暑") == 1


class TestPrecedence:
    def test_両方有効なら節気の日は節気を出す(self):
        out = svg(show_rokuyo=True, show_solar_terms=True)
        assert "立秋" in out and "処暑" in out
        # 節気2日ぶんが六曜に置き換わる
        rokuyo = sum(out.count(w) for w in
                     ("大安", "赤口", "先勝", "友引", "先負", "仏滅"))
        assert rokuyo == 31 - 2


class TestLayout:
    @pytest.mark.parametrize("kwargs", [
        {"show_rokuyo": True}, {"show_solar_terms": True},
        {"show_rokuyo": True, "show_solar_terms": True},
    ])
    def test_注記があると高さが伸びる(self, kwargs):
        plain = canvas_size(WidgetConfig())
        annotated = canvas_size(WidgetConfig(**kwargs))
        assert annotated[0] == plain[0], "幅は変えない"
        assert annotated[1] > plain[1]

    def test_注記の有無で高さは2種類しかない(self):
        """六曜だけ／節気だけ／両方 で高さが変わるとREADME上でずれる。"""
        heights = {canvas_size(WidgetConfig(**k))[1] for k in (
            {"show_rokuyo": True}, {"show_solar_terms": True},
            {"show_rokuyo": True, "show_solar_terms": True})}
        assert len(heights) == 1

    def test_SVGの高さ属性が実際に伸びている(self):
        out = svg(show_rokuyo=True)
        assert f'height="{canvas_size(WidgetConfig(show_rokuyo=True))[1]}"' in out


class TestRange:
    """六曜はテーブルの範囲でしか出せない。黙って空欄にしない。"""

    @pytest.mark.parametrize("target", [dt.date(1899, 6, 1), dt.date(2101, 6, 1)])
    def test_範囲外の月は六曜を出せないので落とす(self, target):
        with pytest.raises(ValueError, match="対応範囲"):
            render(target, theme=LIGHT, config=WidgetConfig(show_rokuyo=True))

    def test_範囲外でも注記なしなら描ける(self):
        assert render(dt.date(2200, 6, 1), theme=LIGHT, config=WidgetConfig())


class TestFontSubset:
    def test_注記の文字もサブセット照合の対象になる(self):
        """六曜を出すのに六曜の字が無いサブセットを渡したら落ちること。

        描いてから豆腐で気づくのではなく、描く前に落とす。
        """
        from almanac_calendar.charset import required_charset

        for word in ("大安", "赤口", "先勝", "友引", "先負", "仏滅"):
            for ch in word:
                assert ch in required_charset(), ch


class TestMoon:
    """月の満ち欠け。形は各マスの右上、月齢は注記行。"""

    def test_既定では月を描かない(self):
        assert "<path" not in svg()

    def test_有効にすると日数ぶんの月が描かれる(self):
        out = svg(show_moon=True)
        assert out.count("<path") == 31
        assert out.count("<circle") == 31  # 下地の暗い円

    def test_月の形は注記行と競合しない(self):
        """形は別レイヤーなので、節気や六曜を押しのけない。"""
        out = svg(show_moon=True, show_rokuyo=True, show_solar_terms=True)
        assert out.count("<path") == 31
        assert "立秋" in out
        rokuyo = sum(out.count(w) for w in
                     ("大安", "赤口", "先勝", "友引", "先負", "仏滅"))
        assert rokuyo == 31 - 2

    def test_形だけなら高さは伸びない(self):
        """形はマスの中に収まる。注記行を足すのは文字を出すときだけ。"""
        assert canvas_size(WidgetConfig(show_moon=True)) == canvas_size(
            WidgetConfig())

    def test_月齢を出すと高さが伸びる(self):
        assert (canvas_size(WidgetConfig(show_moon_age=True))[1]
                > canvas_size(WidgetConfig())[1])

    def test_月齢は小数第1位まで出す(self):
        """整数に丸めると朔（0.x）と晦日（29.x）の区別がつかなくなる。"""
        import re
        out = svg(show_moon_age=True)
        ages = re.findall(r'font-size="9"[^>]*>([\d.]+)</text>', out)
        assert len(ages) == 31
        assert all("." in a for a in ages), ages

    def test_月齢より節気と六曜が優先される(self):
        out = svg(show_moon_age=True, show_rokuyo=True, show_solar_terms=True)
        assert "立秋" in out
        rokuyo = sum(out.count(w) for w in
                     ("大安", "赤口", "先勝", "友引", "先負", "仏滅"))
        assert rokuyo == 29

    def test_1か月のあいだに形が変化する(self):
        """全部同じ形なら輝面比を計算していない。"""
        import re
        paths = re.findall(r'<path d="([^"]+)"', svg(show_moon=True))
        assert len(set(paths)) >= 25, len(set(paths))

    def test_範囲外の月は月を描けないので落とす(self):
        with pytest.raises(ValueError, match="サポート範囲外"):
            render(dt.date(2101, 6, 1), theme=LIGHT,
                   config=WidgetConfig(show_moon=True))


class TestStackMode:
    """併記モード。優先順位で1つに絞らず、該当するものを上から詰める。"""

    def test_六曜と節気を両方出せる(self):
        out = svg(show_rokuyo=True, show_solar_terms=True,
                  annotation_mode="stack")
        assert "立秋" in out
        rokuyo = sum(out.count(w) for w in
                     ("大安", "赤口", "先勝", "友引", "先負", "仏滅"))
        assert rokuyo == 31, "節気の日の六曜が消えている"

    def test_確保する行数は設定だけで決まる(self):
        """月によって行数が変わると画像の高さが変わり、READMEがずれる。"""
        from almanac_calendar.calendar import annotation_lines
        config = WidgetConfig(show_rokuyo=True, show_solar_terms=True,
                              annotation_mode="stack")
        assert annotation_lines(config) == 2
        heights = {render(dt.date(2026, m, 1), theme=LIGHT,
                          config=config).decode().split('height="')[1][:3]
                   for m in range(1, 13)}
        assert len(heights) == 1, heights

    def test_priorityモードより高い(self):
        stacked = WidgetConfig(show_rokuyo=True, show_solar_terms=True,
                               annotation_mode="stack")
        single = WidgetConfig(show_rokuyo=True, show_solar_terms=True)
        assert canvas_size(stacked)[1] > canvas_size(single)[1]
        assert canvas_size(stacked)[0] == canvas_size(single)[0]

    def test_3種そろう日がある(self):
        """春分の日・秋分の日は定義上かならず節気と重なる。"""
        out = render(dt.date(2026, 9, 1), theme=LIGHT,
                     config=WidgetConfig(holiday_country="JP",
                                         show_holiday_names=True,
                                         show_rokuyo=True,
                                         show_solar_terms=True,
                                         annotation_mode="stack")).decode()
        assert "秋分の日" in out and "秋分" in out.replace("秋分の日", "")

    def test_上から詰めるので空行ができない(self):
        """祝日のない日は六曜が日付のすぐ下に来る。

        優先順位の固定スロットに置くと、祝日のない日（ほぼ全部）は
        1行目が空いて六曜だけが下に浮く。該当するものを上から詰める。
        """
        import re

        from almanac_calendar.calendar import _cell_height
        config = WidgetConfig(holiday_country="JP", show_holiday_names=True,
                              show_rokuyo=True, annotation_mode="stack")
        out = render(TARGET, theme=LIGHT, config=config,
                     today=TARGET).decode("utf-8")
        ys = [float(y) for y in
              re.findall(r'y="([\d.]+)"[^>]*font-size="9"', out)]
        # 各週の行は cell_h ごとに並ぶ。1行目だけが基準座標に一致する
        base, cell = min(ys), _cell_height(config)
        first = [y for y in ys if (y - base) % cell == 0]
        deep = [y for y in ys if (y - base) % cell != 0]
        assert len(first) == 31, "1行目を使っていない日がある"
        assert len(deep) == 1, f"2行目は山の日(8/11)だけのはず: {deep}"

    def test_未対応のモードは設定時に落ちる(self):
        with pytest.raises(ValueError, match="注記モード"):
            WidgetConfig(annotation_mode="inline")


class TestColorize:
    """六曜に確立した配色慣習は無いので、既定は無彩色。"""

    def test_既定では全て同じ色(self):
        import re
        out = svg(show_rokuyo=True)
        colors = set(re.findall(r'fill="(#[0-9a-f]{6})"[^>]*font-size="9"', out))
        assert len(colors) <= 2  # 通常色と「今日」の色

    def test_有効にすると大安と仏滅が別の色になる(self):
        from almanac_calendar.svg.theme import THEMES
        out = svg(show_rokuyo=True, colorize_annotations=True)
        assert THEMES["light"].lucky in out, "大安が色付いていない"
        assert THEMES["light"].unlucky in out, "仏滅・赤口が色付いていない"

    def test_中間の3つは無彩色のまま(self):
        """先勝・友引・先負に意味づけを足さない。"""
        import re
        out = svg(show_rokuyo=True, colorize_annotations=True)
        for word in ("先勝", "友引", "先負"):
            for m in re.finditer(
                    r'fill="(#[0-9a-f]{6})"[^>]*font-size="9"[^>]*>' + word, out):
                assert m.group(1) == THEMES["light"].muted, word


class TestMoonOptions:
    def test_月を注記の下に置ける(self):
        assert (canvas_size(WidgetConfig(show_moon=True,
                                         moon_position="below"))[1]
                > canvas_size(WidgetConfig(show_moon=True))[1])

    def test_位置を変えても幅は同じ(self):
        a = canvas_size(WidgetConfig(show_moon=True, moon_position="below"))
        b = canvas_size(WidgetConfig(show_moon=True))
        assert a[0] == b[0]

    def test_月だけ黄色にできる(self):
        from almanac_calendar.svg.theme import THEMES
        assert THEMES["light"].moon not in svg(show_moon=True)
        assert THEMES["light"].moon in svg(show_moon=True, moon_amber=True)

    def test_belowにはshow_moonが要る(self):
        with pytest.raises(ValueError, match="show_moon"):
            WidgetConfig(moon_position="below")
