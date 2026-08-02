"""ルール層（旧暦の月配置）を韓国天文研究院と照合する（開発時のみ）。

    PYTHONPATH=src python3 -m almanac_calendar._generate.verify_lunisolar_rules [--years 1900 2100]

**なぜKASIなのか**。天文層（朔・中気の瞬時）は国立天文台と全件照合できるが、
ルール層には権威ある正解が存在しない。日本は明治5年の改暦で旧暦を公的に
廃止しており、**現行の旧暦日を公表する政府機関がない**（国立天文台も朔と
節気は出すが旧暦日は出さない）。そこで次の3条件を満たす外部系統を選ぶ。

  - 境界子午線が同じ UTC+9（中国暦のUTC+8だと朔日が1日ずれる年がある。
    実例: 2027年の朔は 02-06 15:56 UTC＝日本2/7 00:56／中国2/6 23:56）
  - 政府機関である（韓国天文研究院。暦の公式編纂機関）
  - QREKI系の実装から独立している（同じ実装の写しを照合しても意味がない）

韓国の現行暦は中国式の置閏（冬至月から次の冬至月に13ヶ月あれば最初の
中気なし月が閏月）で、当実装と同じ規則。天保暦の「二至二分」優先制約は
通常年には出番がないので、ここが食い違うのは2033年問題の区間だけのはず。

**問い合わせ方**。`/life/lunc/between` は「旧暦の (月, 日, 閏フラグ) が
西暦何年何月何日か」を年範囲で一括に返す。dd=01 に固定して mm を1〜12、
閏フラグを両方引けば **24リクエストで全期間の月初がそろう**。月内の日付は
朔日からの加算でしかないので、月初・月番号・閏フラグ・月の長さが一致すれば
暦全体が一致する。1日ずつ引くと2万リクエストになるので使わない。

出力は結果ログのみをコミットする。KASIのデータ自体は再配布しない。
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from almanac_calendar.koyomi import tables
from almanac_calendar.koyomi.lunisolar import UNDETERMINED, _months

BASE = "https://astro.kasi.re.kr"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (almanac_calendar lunisolar rule verification; one-off)",
    "Referer": f"{BASE}/life/pageView/8",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}
#: KASI側の収録範囲。外に出ると空配列が返る（旧暦2050年で終わり）
KASI_RANGE = (1899, 2050)

#: KASIが北京子午線（UTC+8）で計算している区間。実測で確定した境界。
#: 1912年より前の朝鮮は中国暦をそのまま用いており、独自計算に移った
#: のがこの前後。日本は1888年以降ずっとUTC+9なので、ここでの差は
#: **暦法の違いであって実装の誤りではない**。差を握りつぶさずに、
#: 「UTC+8で計算し直せばKASIと一致すること」まで確認して初めて
#: 説明がついたと言える。
CHINESE_MERIDIAN_UNTIL = 1911


def _get(path: str, cache: Path | None = None, **query) -> list[dict]:
    key = urllib.parse.urlencode(sorted(query.items()))
    if cache is not None and (cache / f"{key}.json").exists():
        return json.loads((cache / f"{key}.json").read_text("utf-8"))
    url = f"{BASE}{path}?{urllib.parse.urlencode(query)}"
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read().decode("utf-8")
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f"{key}.json").write_text(body, "utf-8")
    return json.loads(body)


def kasi_month_starts(start: int, end: int, *, pause: float = 0.5,
                      cache: Path | None = None) -> dict[tuple[int, int, bool], dict]:
    """(旧暦年, 月, 閏) -> {開始日, 月の長さ} を集める。24リクエストで済む。"""
    out: dict[tuple[int, int, bool], dict] = {}
    for month in range(1, 13):
        for is_leap in (False, True):
            rows = _get("/life/lunc/between", cache,
                        start_yyyy=start, end_yyyy=end,
                        mm=f"{month:02d}", dd="01",
                        isLeap="true" if is_leap else "false")
            for row in rows:
                # 閏月を持たない年にも平月の行が返るので、返り値側のフラグを見る
                leap = row["LUNC_LEAP_MM"] == "윤"
                if leap is not is_leap:
                    continue
                key = (int(row["LUNC_YYYY"]), int(row["LUNC_MM"]), leap)
                out[key] = {
                    "start": dt.date(int(row["SOLC_YYYY"]), int(row["SOLC_MM"]),
                                     int(row["SOLC_DD"])),
                    "length": int(row["LUNC_EN_DD"]),
                }
            if cache is None:
                time.sleep(pause)
    return out


def mine_month_starts(start: int, end: int, *,
                      offset_hours: int = 9) -> dict[tuple[int, int, bool], dict]:
    months = _months(offset_hours)
    out: dict[tuple[int, int, bool], dict] = {}
    for (begin, year, month, leap), following in zip(months, months[1:]):
        if start <= year <= end:
            out[(year, month, leap)] = {
                "start": begin,
                "length": (following[0] - begin).days,
            }
    return out


def verify(start: int, end: int, *, pause: float = 0.5,
           cache: Path | None = None) -> int:
    start = max(start, KASI_RANGE[0])
    end = min(end, KASI_RANGE[1])
    print(f"KASI と照合します（{start}〜{end}年、旧暦の月初のみ）")

    theirs = kasi_month_starts(start, end, pause=pause, cache=cache)
    mine = mine_month_starts(start, end)
    beijing = mine_month_starts(start, end, offset_hours=8)

    only_theirs = sorted(set(theirs) - set(mine))
    shared = sorted(set(mine) & set(theirs))

    failures, explained, undetermined = [], [], []
    for key in shared:
        a, b = mine[key], theirs[key]
        year, month, leap = key
        label = f"{year}年{'閏' if leap else ''}{month}月"
        if a["start"] == b["start"] and a["length"] == b["length"]:
            continue
        detail = (f"{label} 開始={a['start']}/{b['start']} "
                  f"長さ={a['length']}/{b['length']}（当実装/KASI）")
        if UNDETERMINED[0] <= a["start"] <= UNDETERMINED[1]:
            undetermined.append(detail)
        elif year <= CHINESE_MERIDIAN_UNTIL and beijing.get(key) == b:
            explained.append(f"{label} UTC+8で再計算するとKASIと一致")
        else:
            failures.append(detail)

    print(f"\n照合した月: {len(shared)} ヶ月"
          f"（{start}〜{end}年。KASIの収録は旧暦{KASI_RANGE[1]}年まで）")
    print(f"\n合否: 説明のつかない不一致 = {len(failures)} 件")
    for line in failures[:30]:
        print(f"  {line}")

    print(f"\n子午線の違いで説明がつく差（{CHINESE_MERIDIAN_UNTIL}年以前）"
          f": {len(explained)} 件")
    for line in explained[:15]:
        print(f"  {line}")
    print(f"\n2033年問題の区間（規則が一意に定まらない）: {len(undetermined)} 件")
    for line in undetermined[:15]:
        print(f"  {line}")
    if not undetermined:
        print("  なし。KASIも当実装と同じ閏11月案を採っている")
    if only_theirs:
        print(f"\nKASIにのみ存在する月: {len(only_theirs)} 件 {only_theirs[:5]}")

    print("\n結果:", "不一致あり" if failures or only_theirs else "全一致")
    return 1 if failures or only_theirs else 0


def main(argv: list[str] | None = None) -> int:
    low, high = tables.SUPPORTED_RANGE
    p = argparse.ArgumentParser(description="ルール層を韓国天文研究院と照合する")
    p.add_argument("--years", nargs=2, type=int, default=[low.year, high.year],
                   metavar=("START", "END"))
    p.add_argument("--pause", type=float, default=0.5,
                   help="リクエスト間隔（秒）。公開サービスに配慮する")
    p.add_argument("--cache", type=Path, default=None,
                   help="取得したJSONを置くディレクトリ。リポジトリ外を指すこと")
    args = p.parse_args(argv)
    return verify(args.years[0], args.years[1], pause=args.pause, cache=args.cache)


if __name__ == "__main__":
    sys.exit(main())
