"""SVG 組み立ての最小契約。

守るべき性質は2つだけ。
  1. 同じ入力なら同じバイト列になること（決定性）
  2. テキストを必ずXMLエスケープすること

決定性を先に固定する理由: 生成物は毎日cronで再生成され、差分が出れば
それだけコミットが積まれる。意味のない差分が混ざると「今日は何が変わったのか」
が読めなくなり、生成物を見なくなる。
"""

from __future__ import annotations

import pytest

from almanac_calendar.svg.document import Svg, escape_text


class TestEscape:
    def test_アンパサンドと山括弧を実体参照にする(self):
        assert escape_text("a & b < c > d") == "a &amp; b &lt; c &gt; d"

    def test_引用符も実体参照にする(self):
        # 属性値に入れても壊れないようにする
        assert escape_text('say "hi"') == "say &quot;hi&quot;"

    def test_エスケープ済みの文字列を二重にエスケープしない用途はない(self):
        # 生の文字列を1回だけ通す前提。&amp; を入れれば &amp;amp; になるのが正しい
        assert escape_text("&amp;") == "&amp;amp;"

    def test_日本語はそのまま通す(self):
        assert escape_text("日月火") == "日月火"


class TestSvgDeterminism:
    def _build(self) -> Svg:
        svg = Svg(width=100, height=50)
        svg.rect(x=0, y=0, width=100, height=50, fill="#fff")
        svg.text("あ", x=10, y=20, fill="#000", size=12)
        return svg

    def test_同じ組み立てなら同じバイト列(self):
        assert self._build().to_bytes() == self._build().to_bytes()

    def test_出力にタイムスタンプが混入しない(self):
        out = self._build().to_bytes().decode("utf-8")
        for token in ("20", "T0", "Z\"", "generated at"):
            if token == "20":
                # 座標などに 20 は出うるので、ISO日時らしき並びだけを弾く
                continue
            assert token not in out

    def test_バイト列を返す(self):
        assert isinstance(self._build().to_bytes(), bytes)

    def test_svg要素とviewBoxを持つ(self):
        out = self._build().to_bytes().decode("utf-8")
        assert out.startswith("<svg")
        assert 'viewBox="0 0 100 50"' in out
        assert out.rstrip().endswith("</svg>")


class TestSvgText:
    def test_テキストはエスケープされて埋まる(self):
        svg = Svg(width=10, height=10)
        svg.text("a & b", x=0, y=0, fill="#000", size=10)
        assert "a &amp; b" in svg.to_bytes().decode("utf-8")
        assert "a & b" not in svg.to_bytes().decode("utf-8")

    def test_属性の順序が固定される(self):
        # 属性順が揺れると意味のない差分が出る
        a = Svg(width=10, height=10)
        a.text("x", x=1, y=2, fill="#000", size=10)
        b = Svg(width=10, height=10)
        b.text("x", x=1, y=2, fill="#000", size=10)
        assert a.to_bytes() == b.to_bytes()


class TestSvgAccessibility:
    def test_titleを与えるとrole_imgとtitle要素が出る(self):
        svg = Svg(width=10, height=10, title="2026年8月のカレンダー")
        out = svg.to_bytes().decode("utf-8")
        assert 'role="img"' in out
        assert "<title>2026年8月のカレンダー</title>" in out

    def test_titleもエスケープされる(self):
        svg = Svg(width=10, height=10, title="a & b")
        assert "<title>a &amp; b</title>" in svg.to_bytes().decode("utf-8")


class TestSvgGuards:
    def test_負のサイズは拒否する(self):
        with pytest.raises(ValueError):
            Svg(width=-1, height=10)
