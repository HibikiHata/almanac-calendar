"""S3: 今日の強調とタイムゾーン表記。

「今日」は描画の入力として外から渡す。target（どの月を描くか）と
today（どの日を強調するか）を分けているのは、来月のカレンダーを
強調なしで描くといった使い方を潰さないため。

タイムゾーン表記を出す理由: 静的画像なので閲覧者ごとの時刻には追従できない。
「ずれている」ではなく「これは東京の暦です」と読めるようにして誤解を消す。
"""

from __future__ import annotations

from datetime import date

import pytest

from almanac_calendar.config import WidgetConfig
from almanac_calendar.svg.theme import PALETTES, THEMES
from almanac_calendar.calendar import render, render_pair


def _light():
    return THEMES["light"]


class TestTodayHighlight:
    def test_todayを渡さなければ強調しない(self):
        out = render(date(2026, 8, 1), theme=_light(), config=WidgetConfig()).decode()
        assert "data-today" not in out

    def test_todayを渡すと強調マークが1つだけ出る(self):
        out = render(date(2026, 8, 1), theme=_light(), config=WidgetConfig(),
                     today=date(2026, 8, 15)).decode()
        assert out.count('data-today="true"') == 1

    def test_強調の背景色が通常セルと異なる(self):
        theme = _light()
        out = render(date(2026, 8, 1), theme=theme, config=WidgetConfig(),
                     today=date(2026, 8, 15)).decode()
        # 強調セルの塗りはテーマの today_bg で、背景色とは別の値であること
        assert theme.today_bg != theme.bg
        assert theme.today_bg in out

    def test_月外のtodayは強調しない(self):
        out = render(date(2026, 8, 1), theme=_light(), config=WidgetConfig(),
                     today=date(2026, 9, 1)).decode()
        assert "data-today" not in out

    def test_月初と月末も強調できる(self):
        for day in (1, 31):
            out = render(date(2026, 8, 1), theme=_light(), config=WidgetConfig(),
                         today=date(2026, 8, day)).decode()
            assert out.count('data-today="true"') == 1

    def test_todayが違えば出力が変わる(self):
        cfg = WidgetConfig()
        a = render(date(2026, 8, 1), theme=_light(), config=cfg, today=date(2026, 8, 1))
        b = render(date(2026, 8, 1), theme=_light(), config=cfg, today=date(2026, 8, 2))
        assert a != b

    def test_同じtodayなら決定的(self):
        cfg = WidgetConfig()
        args = dict(theme=_light(), config=cfg, today=date(2026, 8, 15))
        assert render(date(2026, 8, 1), **args) == render(date(2026, 8, 1), **args)


class TestTimezoneLabel:
    def test_既定ではタイムゾーン表記を出さない(self):
        # 自分のREADMEに置く分には自明なので、既定は出さない
        out = render(date(2026, 8, 1), theme=_light(), config=WidgetConfig(),
                     today=date(2026, 8, 15)).decode()
        assert "JST" not in out

    def test_オプションを有効にすると表記が出る(self):
        out = render(date(2026, 8, 1), theme=_light(),
                     config=WidgetConfig(show_timezone=True),
                     today=date(2026, 8, 15)).decode()
        assert "JST" in out

    def test_タイムゾーンを変えると表記も変わる(self):
        cfg = WidgetConfig(display_timezone="America/New_York", show_timezone=True)
        out = render(date(2026, 8, 1), theme=_light(), config=cfg,
                     today=date(2026, 8, 15)).decode()
        assert "JST" not in out
        assert "EDT" in out or "EST" in out

    def test_today無しならオプションを有効にしても出ない(self):
        # 「今日」を描かないなら、どの地域の暦かを断る必要がない
        out = render(date(2026, 8, 1), theme=_light(),
                     config=WidgetConfig(show_timezone=True)).decode()
        assert "JST" not in out

    def test_未知のタイムゾーンは拒否する(self):
        with pytest.raises(ValueError):
            WidgetConfig(display_timezone="Mars/Olympus")


class TestPalettes:
    def test_既定パレットが存在する(self):
        assert "default" in PALETTES
        assert set(PALETTES["default"]) == {"light", "dark"}

    def test_全パレットがlightとdarkを持つ(self):
        for name, pair in PALETTES.items():
            assert set(pair) == {"light", "dark"}, name

    def test_全パレットの必須色が埋まっている(self):
        for name, pair in PALETTES.items():
            for mode, theme in pair.items():
                for field in ("bg", "fg", "muted", "grid", "today_bg", "today_fg"):
                    assert getattr(theme, field), f"{name}/{mode}/{field}"

    def test_パレットを切り替えると出力が変わる(self):
        others = [n for n in PALETTES if n != "default"]
        assert others, "既定以外のパレットが1つ以上必要"
        a = render_pair(date(2026, 8, 15), config=WidgetConfig(palette="default"))
        b = render_pair(date(2026, 8, 15), config=WidgetConfig(palette=others[0]))
        assert a.light != b.light

    def test_未知のパレットは拒否する(self):
        with pytest.raises(ValueError):
            WidgetConfig(palette="nonexistent")


class TestRenderPairToday:
    def test_render_pairにtodayを渡せる(self):
        pair = render_pair(date(2026, 8, 1), config=WidgetConfig(), today=date(2026, 8, 15))
        assert b'data-today="true"' in pair.light
        assert b'data-today="true"' in pair.dark


class TestRadius:
    """カード外周の角丸。

    GitHub は README 内の style 属性を全削除するので、CSSで角を丸めることはできない。
    カード風の見た目が要るならSVGの中で描くしかない。
    """

    def test_既定は角丸(self):
        out = render(date(2026, 8, 1), theme=_light(), config=WidgetConfig()).decode()
        assert 'rx="8"' in out

    def test_0を指定すると直角になる(self):
        out = render(date(2026, 8, 1), theme=_light(),
                     config=WidgetConfig(radius=0)).decode()
        # 外周の矩形に rx が付かないこと（曜日帯の rx="4" は残る）
        assert '<rect x="0" y="0" width="312"' in out
        bg = [ln for ln in out.splitlines() if '<rect x="0" y="0" width="312"' in ln][0]
        assert "rx=" not in bg

    def test_半径を変えると出力が変わる(self):
        a = render(date(2026, 8, 1), theme=_light(), config=WidgetConfig(radius=8))
        b = render(date(2026, 8, 1), theme=_light(), config=WidgetConfig(radius=20))
        assert a != b

    def test_負の半径は拒否する(self):
        with pytest.raises(ValueError):
            WidgetConfig(radius=-1)


class TestBorder:
    def test_既定では枠線なし(self):
        out = render(date(2026, 8, 1), theme=_light(), config=WidgetConfig()).decode()
        assert "stroke=" not in out

    def test_有効にすると枠線が出る(self):
        theme = _light()
        out = render(date(2026, 8, 1), theme=theme,
                     config=WidgetConfig(border=True)).decode()
        assert f'stroke="{theme.grid}"' in out

    def test_枠線は内側に0_5pxずらす(self):
        # 輪郭に引くと半分が画像外に出て太さが不揃いに見える
        out = render(date(2026, 8, 1), theme=_light(),
                     config=WidgetConfig(border=True)).decode()
        assert '<rect x="0.5" y="0.5" width="311" height="319"' in out
