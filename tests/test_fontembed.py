"""S-pub: フォントのサブセット埋め込み。

`<img>` 経由のSVGは外部リソースを一切読み込めないので、フォントは base64 で
中に埋めるしかない。9.1MB をそのまま埋めるのは非現実的なのでサブセット化する。

ここで守る性質は3つ。
  1. 描く文字が manifest に無ければ**描画せずに落ちる**（豆腐を黙って出さない）
  2. 埋め込み結果が決定的（フォント生成のタイムスタンプで毎回変わらない）
  3. OFLの著作権表示がSVGに入る（生成SVGはFont Softwareの複製として単体配布される）
"""

from __future__ import annotations

import base64

import pytest

from almanac_calendar.charset import required_charset
from almanac_calendar.svg.fontembed import (
    FontSubset,
    available_subsets,
    load_subset,
    missing_characters,
)


class TestCharset:
    def test_必要な文字が漏れなく含まれる(self):
        cs = required_charset()
        for ch in "日月火水木金土":          # 曜日
            assert ch in cs, ch
        for ch in "年月":                     # 見出し
            assert ch in cs, ch
        for ch in "0123456789":               # 日付
            assert ch in cs, ch
        for ch in "SunMonTueWedThuFriSat":    # 英語曜日
            assert ch in cs, ch
        for ch in "January":                  # 英語月名
            assert ch in cs, ch

    def test_タイムゾーン略称に備えて英大文字と記号を含む(self):
        # JST / EDT / UTC+09:00 のような任意の略称が来る
        cs = required_charset()
        for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ+-:":
            assert ch in cs, ch

    def test_六曜と月齢の語彙を先に含めておく(self):
        # S4/S5 で作り直さずに済むよう、確定している語彙は先に入れる
        cs = required_charset()
        for ch in "大安赤口先勝友引負仏滅":
            assert ch in cs, ch

    def test_重複がなく決定的(self):
        a, b = required_charset(), required_charset()
        assert a == b
        assert len(a) == len(set(a))


class TestSubsetAssets:
    def test_サブセットが1つ以上生成済み(self):
        assert available_subsets(), (
            "サブセットが未生成。"
            "PYTHONPATH=src python3 -m almanac_calendar._generate.gen_font_subset を実行すること"
        )

    def test_manifestが必要文字を全て覆う(self):
        for name in available_subsets():
            subset = load_subset(name)
            missing = missing_characters(required_charset(), subset)
            assert not missing, f"{name} に不足: {''.join(sorted(missing))}"

    def test_サブセットは元フォントより大幅に小さい(self):
        # 9.1MB を数十KB以下に落とせていること
        for name in available_subsets():
            subset = load_subset(name)
            assert len(subset.data) < 200_000, f"{name} が大きすぎる: {len(subset.data)}B"


class TestMissingCharacters:
    def test_manifestに無い文字を検出する(self):
        subset = FontSubset(family="X", data=b"x", charset=frozenset("abc"))
        assert missing_characters("abcd", subset) == {"d"}

    def test_全て含まれていれば空(self):
        subset = FontSubset(family="X", data=b"x", charset=frozenset("abc"))
        assert missing_characters("cab", subset) == set()


class TestFontFace:
    def _subset(self) -> FontSubset:
        return load_subset(available_subsets()[0])

    def test_font_faceにbase64が埋まる(self):
        css = self._subset().font_face_css()
        assert "@font-face" in css
        assert "base64," in css
        assert "font-family:" in css

    def test_base64が復号するとフォント本体になる(self):
        subset = self._subset()
        css = subset.font_face_css()
        payload = css.split("base64,", 1)[1].split(")", 1)[0]
        assert base64.b64decode(payload) == subset.data

    def test_同じサブセットなら決定的(self):
        assert self._subset().font_face_css() == self._subset().font_face_css()

    def test_OFLの著作権表示を返す(self):
        # 表記は "(c)" だったり "Copyright" だったりフォント次第なので、
        # 語を決め打ちせず「元フォントの著作権行がそのまま入っていること」を見る
        subset = self._subset()
        notice = subset.license_notice()
        assert "SIL Open Font License" in notice
        assert "scripts.sil.org/OFL" in notice
        assert subset.copyright, "元フォントの著作権行が取れていない"
        assert subset.copyright.replace("--", "-") in notice

    def test_予約フォント名を名乗らない(self):
        # OFL 1.1 は改変版が Reserved Font Name を使うことを禁じる。
        # NotoSansJP の RFN は 'Source'
        assert "Source" not in self._subset().family

    def test_著作権表示にXMLを壊す文字が含まれない(self):
        # SVGコメントとして埋めるので -- や < があると壊れる
        notice = self._subset().license_notice()
        assert "--" not in notice
        assert "<" not in notice and ">" not in notice


class TestRenderIntegration:
    def test_フォントを指定すると埋め込まれる(self):
        from datetime import date

        from almanac_calendar.calendar import render
        from almanac_calendar.config import WidgetConfig
        from almanac_calendar.svg.theme import THEMES

        name = available_subsets()[0]
        out = render(date(2026, 8, 1), theme=THEMES["light"],
                     config=WidgetConfig(font=name)).decode()
        assert "@font-face" in out
        assert "SIL Open Font License" in out

    def test_font未指定なら埋め込まない(self):
        from datetime import date

        from almanac_calendar.calendar import render
        from almanac_calendar.config import WidgetConfig
        from almanac_calendar.svg.theme import THEMES

        out = render(date(2026, 8, 1), theme=THEMES["light"],
                     config=WidgetConfig()).decode()
        assert "@font-face" not in out

    def test_未知のフォント名は拒否する(self):
        from almanac_calendar.config import WidgetConfig

        with pytest.raises(ValueError):
            WidgetConfig(font="nonexistent-font")
