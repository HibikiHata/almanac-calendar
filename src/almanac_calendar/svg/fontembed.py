"""サブセットフォントの読み込みと `@font-face` への埋め込み（実行時・標準ライブラリのみ）。

fontTools は開発時にサブセットを作るときだけ使う。ここでは出来上がった
バイナリを base64 にして埋めるだけなので、配布物に第三者依存は入らない。

manifest（charset.txt）との照合を描画側で行う理由:
描く文字がサブセットに無いと、ブラウザは黙って豆腐（□）を出す。
gen-image の fonts.py が実グリフを見て検査しているのと同じ目的を、
標準ライブラリだけで達成するために「生成時に実cmapから書き出した一覧」と
突き合わせる。
"""
from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path

FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"


@dataclass(frozen=True)
class FontSubset:
    family: str
    data: bytes
    charset: frozenset[str]
    copyright: str = ""

    def font_face_css(self) -> str:
        """`<style>` に入れる `@font-face` 宣言。

        woff2 ではなく truetype で埋めているのは、圧縮を足しても
        この規模では差が小さく、生成の再現性を優先するため。
        """
        payload = base64.b64encode(self.data).decode("ascii")
        return (
            f"@font-face{{font-family:'{self.family}';font-style:normal;"
            f"src:url(data:font/ttf;base64,{payload}) format('truetype')}}"
        )

    def license_notice(self) -> str:
        """SVGコメントに入れる著作権表示。

        生成SVGはフォント本体を含む＝Font Software の複製であり、raw URL で
        単体配布されるため、リポジトリのLICENSEファイルでは条件を満たさない。
        OFL 1.1 は各複製に著作権表示とライセンスを添えることを求める。
        """
        # コメントに入れるので `--` と山括弧を持ち込まない
        text = self.copyright.replace("--", "-").replace("<", "(").replace(">", ")")
        return (
            f"{text} / This Font Software is licensed under the "
            f"SIL Open Font License, Version 1.1. https://scripts.sil.org/OFL"
        )


def available_subsets() -> list[str]:
    """生成済みサブセットの名前を返す（決定的な順序）。"""
    if not FONTS_DIR.is_dir():
        return []
    return sorted(p.stem for p in FONTS_DIR.glob("*.ttf"))


def load_subset(name: str) -> FontSubset:
    ttf = FONTS_DIR / f"{name}.ttf"
    manifest = FONTS_DIR / f"{name}.charset.txt"
    notice = FONTS_DIR / f"{name}.copyright.txt"
    if not ttf.is_file() or not manifest.is_file():
        raise ValueError(
            f"サブセットが見つかりません: {name}。"
            "PYTHONPATH=src python3 -m almanac_calendar._generate.gen_font_subset を実行してください"
        )
    return FontSubset(
        family=name,
        data=ttf.read_bytes(),
        charset=frozenset(manifest.read_text(encoding="utf-8")),
        copyright=notice.read_text(encoding="utf-8").strip() if notice.is_file() else "",
    )


def missing_characters(text: str, subset: FontSubset) -> set[str]:
    """サブセットが描けない文字を返す。空なら安全。"""
    return {ch for ch in text if ch not in subset.charset}
