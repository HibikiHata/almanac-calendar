"""日本の祝日を `holidays` ライブラリと全件照合する（開発時のみ）。

    PYTHONPATH=src python3 -m almanac_calendar._generate.verify_holidays_jp [--years 1949 2100]

日本の祝日だけ自前実装にしているので、その分だけ照合先が要る。

**なぜ自前にするのか**。春分の日と秋分の日は法律に日付が書かれておらず、
「春分日」「秋分日」とだけ定められている。実体は天文現象で、日付は国立天文台が
前年2月の官報（暦要項）で公表して初めて確定する。近似式を持つより、NAOJと
全件照合済みの節気テーブルから引くほうが確実。副次的に、`holidays` の日本対応は
2099年で切れるが、節気テーブルは2100年まである。

**なぜ照合するのか**。祝日法は1948年以降くり返し改正されている——ハッピー
マンデーへの移行、天皇誕生日の3度の移動、みどりの日と昭和の日の入れ替え、
五輪特例。これを全部書き下せば必ずどこかを間違える。日付の規則については
`holidays` が独立した写しになるので、そこを突き合わせる。

**差の扱い**。日付が食い違えばこちらの誤りを疑う。ただし名前の表記ゆれは
差として数えない（皇室行事の正式名称は「〜の行われる日」まで含むが、
カレンダーのマスに収めるには長すぎる）。

出力は結果ログのみをコミットする。
"""
from __future__ import annotations

import argparse
import sys

from almanac_calendar.koyomi.holidays_jp import holidays_in

try:
    import holidays as _library
except ImportError:  # pragma: no cover - 開発時のみ使う
    _library = None


def verify(start: int, end: int) -> int:
    if _library is None:
        print("holidays が入っていません: python3 -m pip install holidays")
        return 1

    only_mine: list[str] = []
    only_theirs: list[str] = []
    name_diff: list[str] = []
    beyond: list[int] = []
    compared = 0

    for year in range(start, end + 1):
        mine = holidays_in(year)
        theirs = dict(_library.country_holidays("JP", years=[year]))
        if not theirs:
            # ライブラリ側の収録が切れている年。差ではなく範囲外として扱う
            beyond.append(year)
            continue
        compared += len(mine)
        for day in sorted(set(mine) - set(theirs)):
            only_mine.append(f"{day} {mine[day]}")
        for day in sorted(set(theirs) - set(mine)):
            only_theirs.append(f"{day} {theirs[day]}")
        for day in sorted(set(mine) & set(theirs)):
            if mine[day] != theirs[day]:
                name_diff.append(f"{day} 当実装={mine[day]} / holidays={theirs[day]}")

    print(f"照合 {compared} 件（{start}〜{end}年、"
          f"holidays {_library.__version__}）")
    print(f"\n合否: 日付の不一致 = {len(only_mine) + len(only_theirs)} 件")
    for line in only_mine[:20]:
        print(f"  当実装のみ: {line}")
    for line in only_theirs[:20]:
        print(f"  holidaysのみ: {line}")

    print(f"\n参考: 名前の表記ゆれ = {len(name_diff)} 件（合否に数えない）")
    for line in name_diff[:10]:
        print(f"  {line}")

    if beyond:
        print(f"\nholidays 側に収録の無い年: {len(beyond)} 件 "
              f"（{beyond[0]}〜{beyond[-1]}）。"
              "当実装は節気テーブルがあるぶん先まで出せる")

    failed = bool(only_mine or only_theirs)
    print("\n結果:", "不一致あり" if failed else "日付は全一致")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="日本の祝日を holidays と照合する")
    p.add_argument("--years", nargs=2, type=int, default=[1949, 2100],
                   metavar=("START", "END"))
    args = p.parse_args(argv)
    return verify(args.years[0], args.years[1])


if __name__ == "__main__":
    sys.exit(main())
