"""OFLフォントを必要な文字だけに削り、埋め込み用のサブセットを作る（開発時のみ）。

    PYTHONPATH=src python3 -m almanac_calendar._generate.gen_font_subset \
        --source-dir <元フォントを置いたディレクトリ>

元フォントはリポジトリに含めない（9MBあり、成果物は生成済みサブセットで足りる）。
Noto Sans JP の可変フォントを https://fonts.google.com/noto/specimen/Noto+Sans+JP
から取得し、そのディレクトリを --source-dir に渡すか、環境変数
`ALMANAC_FONT_SOURCE_DIR` に設定する。

配布物には入らない。fontTools を使うのはここだけで、実行時（利用者のランナー）は
標準ライブラリのみで動く。

決定性のために `head.modified` を固定する。fontTools は既定でビルド時刻を
書き込むため、これをしないと**毎回バイト列が変わり**、ゴールデン比較も
`output` ブランチの差分も無意味になる。

manifest は「要求した文字」ではなく **生成後のcmapから** 書き出す。要求から
書くと、元フォントに存在しない文字が manifest に載り、実行時チェックを
すり抜けて豆腐が出る。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

from almanac_calendar.charset import required_charset

#: 元フォントの置き場。**リポジトリ内に固定の場所を持たない**。
#: 元フォント自体を同梱しないため、どこから取るかは実行する人が決める。
ENV_SOURCE_DIR = "ALMANAC_FONT_SOURCE_DIR"
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"

# 出力名 -> (元ファイル, 可変フォントの軸を固定する値)
# 可変軸を残すと fvar/gvar/HVAR が付いて想定より膨らむので、weight を固定する。
TARGETS: dict[str, tuple[str, dict[str, float]]] = {
    "noto-sans-jp": ("NotoSansJP-Variable.ttf", {"wght": 500}),
}


def _instantiate(font: TTFont, axes: dict[str, float]) -> TTFont:
    if "fvar" not in font:
        return font
    from fontTools.varLib import instancer

    return instancer.instantiateVariableFont(font, axes, inplace=False)


def build(name: str, source: str, axes: dict[str, float],
          source_dir: Path) -> tuple[int, int]:
    src = source_dir / source
    if not src.is_file():
        raise SystemExit(
            f"元フォントがありません: {src}\n"
            f"Noto Sans JP の可変フォントを取得して置き、--source-dir か "
            f"環境変数 {ENV_SOURCE_DIR} でそのディレクトリを指定してください。\n"
            "https://fonts.google.com/noto/specimen/Noto+Sans+JP")

    wanted = required_charset()
    # recalcTimestamp は TTFont 側の属性。Options.recalc_timestamp は
    # サブセッタ用で、save() 時の再計算はこちらで止める必要がある。
    font = _instantiate(TTFont(str(src), recalcTimestamp=False), axes)

    options = subset.Options()
    # layout_features は既定のまま（標準機能のみ）にする。実測:
    #   全機能保持 61,920B / 既定 16,776B / GSUB+GPOS削除 12,884B
    # 全機能はCJKの縦組み等を丸ごと抱えて4倍近くなる。逆に GSUB/GPOS を捨てると
    # 英語月名のカーニングを失うので、その差 4KB は払う。
    options.name_IDs = [0, 13, 14]     # copyright / license / license URL のみ残す
    options.notdef_outline = True
    options.recalc_timestamp = False   # ビルド時刻を書き込ませない（決定性）
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(text=wanted)
    subsetter.subset(font)

    # 保存時の再計算を止めたうえで、元フォントの更新でバイト列が動かないよう
    # created/modified を固定する。checkSumAdjustment はこれらから導かれる。
    font.recalcTimestamp = False
    font["head"].created = 0
    font["head"].modified = 0

    produced = set()
    for table in font["cmap"].tables:
        produced.update(chr(cp) for cp in table.cmap)

    missing = sorted(set(wanted) - produced)
    if missing:
        raise SystemExit(
            f"{name}: 元フォントに無い文字があります: {''.join(missing)}\n"
            "charset.py を見直すか、別のフォントを使ってください"
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    font.save(str(OUT_DIR / f"{name}.ttf"))

    # manifest は実cmapから。要求集合ではなく「実際に描ける文字」を記録する
    usable = "".join(sorted(produced & set(wanted)))
    (OUT_DIR / f"{name}.charset.txt").write_text(usable, encoding="utf-8")

    # 著作権表示（name table ID 0 = copyright）
    copyright_text = ""
    for record in font["name"].names:
        if record.nameID == 0:
            copyright_text = str(record).strip()
            break
    (OUT_DIR / f"{name}.copyright.txt").write_text(
        copyright_text or f"Font: {source}", encoding="utf-8"
    )

    return src.stat().st_size, (OUT_DIR / f"{name}.ttf").stat().st_size


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="埋め込み用フォントサブセットを作る")
    p.add_argument("--source-dir", type=Path,
                   default=Path(os.environ[ENV_SOURCE_DIR])
                   if os.environ.get(ENV_SOURCE_DIR) else None,
                   help=f"元フォントのあるディレクトリ（環境変数 {ENV_SOURCE_DIR} でも可）")
    args = p.parse_args(argv)
    if args.source_dir is None:
        raise SystemExit(
            f"--source-dir か 環境変数 {ENV_SOURCE_DIR} で元フォントの場所を"
            "指定してください。\nhttps://fonts.google.com/noto/specimen/Noto+Sans+JP")

    for name, (source, axes) in TARGETS.items():
        before, after = build(name, source, axes, args.source_dir)
        print(f"{name}: {before / 1_048_576:.1f}MB -> {after / 1024:.1f}KB "
              f"({len(required_charset())}文字)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
