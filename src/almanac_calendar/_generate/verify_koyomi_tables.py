"""生成済みテーブルを国立天文台の公表値と全件照合する（開発時のみ）。

    PYTHONPATH=src python3 -m almanac_calendar._generate.verify_koyomi_tables [--years 1900 2101]

天文層の検証。ルール層（旧暦日）は権威ある正解が存在しないため別扱い
（KASI との照合。設計文書 §11.1）。

**照合先**: 国立天文台 暦計算室の長期版（-2999〜2999年）
  朔弦望       /cgi-bin/koyomi/cande/phenomena_py.cgi
  二十四節気   /cgi-bin/koyomi/cande/phenomena_sy.cgi

これらは「現在の理論やパラメータにもとづいて算出」した値で、暦要項の公表値とは
異なりうると明記されている（二次オラクル）。一次は暦要項HTML（2005〜2027年）。

**判定は2段構え**。

  1. 合否 = **JSTの日が一致すること**。暦の契約はここにしかない。
     朔日が1日ずれれば月がまるごとずれ、六曜も全部変わる。
  2. 参考 = 分差の分布。日単位だけ見ると、視黄経の定義を取り違えて系統的に
     数分ずれていても99%以上を素通りしてしまう（ADR-0011 §Verification
     Strategy）。感度指標として必ず併記する。

分差を合否にしないのは、将来側の差が**ΔT（TT−UT変換）の外挿差**だから。
ΔTは地球自転のゆらぎ次第で原理的に予測できず、NAOJ自身も暦要項の確定値は
約1年半先までしか公表していない。実測すると朔と節気が同量ずれており
（2100年で朔 −120秒 / 節気 −145秒）、太陽の理論誤差ではないことがわかる。
2093年以降の「正解」は存在せず、こちらもNAOJもただの外挿値である。

出力は結果ログのみをコミットする。NAOJのデータ自体は再配布しない。
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import statistics
import sys
import time
import urllib.request
from collections import Counter
from pathlib import Path

from almanac_calendar.koyomi import tables

BASE = "https://eco.mtk.nao.ac.jp/cgi-bin/koyomi/cande"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (almanac_calendar koyomi table verification; one-off)",
    "Referer": "https://eco.mtk.nao.ac.jp/koyomi/cande/",
}
#: 分差がこれを超えたら参考出力に載せる（合否には使わない。docstring参照）
NOTABLE_MINUTES = 2
JST = dt.timezone(dt.timedelta(hours=9))

# 長期版は中央標準時（JST）で返す
# re.S が要る。付けないと `.*?` が改行をまたげず、各ページの最終行を取りこぼす
_ROW = re.compile(
    r"(\d{4})/(\d{2})/(\d{2})\|\s*\|(\d{2}):(\d{2})\|(.*?)(?=\d{4}/\d{2}/\d{2}\||$)",
    re.S,
)


def _fetch(cgi: str, year: int, cache: Path | None = None) -> str:
    if cache is not None:
        path = cache / f"{cgi}-{year}.txt"
        if path.exists():
            return path.read_text("utf-8")
    request = urllib.request.Request(f"{BASE}/{cgi}?year={year}", headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    text = raw.decode("euc_jp", "replace")
    # re.I が要る。大文字の <SCRIPT> を残すと、次の行のタグ除去で中身だけが本文に混ざる
    text = re.sub(r"<script.*?</script>|<style.*?</style>", "", text, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", "|", text))
    text = re.sub(r"[ 　]+", " ", re.sub(r"\|+", "|", text))
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f"{cgi}-{year}.txt").write_text(text, "utf-8")
    return text


def _rows(text: str) -> list[tuple[dt.datetime, str]]:
    """1行を (JSTの瞬時, 行の残り) にする。

    NAOJは**日界の直前を前日の `24:00` と表記する**（1900〜2100で5回）。
    これは「翌日の0時」ではなく「その日の終わり」で、**NAOJは丸めても日付の
    ほうを保持している**——2030年の雨水は真の値が 2月18日 23:59:40 なので、
    分に丸めた 24:00 を2月18日の行に置いている。

    ここを `timedelta(hours=24)` で足して翌日にすると、**NAOJが保持している
    日付を捨てることになる**。日付の一致を見る検証でそれをやると、正しい実装を
    不一致と誤判定する（実際にそうなった）。24時台は「その日の23:59:59」として
    扱い、日付は印字されたとおりに保つ。
    """
    out = []
    for m in _ROW.finditer(text):
        y, mo, d, h, mi, rest = m.groups()
        hour, minute = int(h), int(mi)
        if hour >= 24:
            when = dt.datetime(int(y), int(mo), int(d), 23, 59, 59, tzinfo=JST)
        else:
            when = dt.datetime(int(y), int(mo), int(d), hour, minute, tzinfo=JST)
        out.append((when, rest))
    return out


#: NAOJの表記 -> 月相コード。表記の順に並べない（下弦の「弦」が上弦にも
#: 含まれるので、部分一致の判定順を誤ると全部が上弦になる）
PHASE_LABELS = (("上弦", 1), ("下弦", 3), ("望", 2), ("朔", 0))


def naoj_moon_phases(year: int, cache: Path | None = None
                     ) -> list[tuple[dt.datetime, int]]:
    """朔弦望すべて。朔だけを見ていた頃より照合件数が4倍になる。"""
    out = []
    for when, rest in _rows(_fetch("phenomena_py.cgi", year, cache)):
        for label, code in PHASE_LABELS:
            if label in rest:
                out.append((when, code))
                break
    return out


def naoj_new_moons(year: int, cache: Path | None = None) -> list[dt.datetime]:
    return [w for w, c in naoj_moon_phases(year, cache) if c == 0]


def naoj_solar_terms(year: int, cache: Path | None = None) -> list[dt.datetime]:
    rows = _rows(_fetch("phenomena_sy.cgi", year, cache))
    return [w for w, rest in rows if "二十四節気" in rest]


def _compare(label: str, year: int, mine: list, theirs: list,
             failures: list[str], drift: list[tuple[int, float]],
             notable: list[str]) -> int:
    """合否は「JSTの日が一致するか」。分差は感度指標として集めるだけ。"""
    if len(mine) != len(theirs):
        failures.append(f"{year} {label}: 件数不一致 表={len(mine)} NAOJ={len(theirs)}")
        return 0
    for a, b in zip(mine, theirs):
        seconds = (a - b).total_seconds()
        drift.append((year, seconds))
        if a.date() != b.date():
            failures.append(
                f"{year} {label} 日が不一致 NAOJ={b:%m/%d %H:%M} 表={a:%m/%d %H:%M}")
        elif abs(seconds) > NOTABLE_MINUTES * 60:
            notable.append(
                f"{year} {label} {b:%m/%d %H:%M} vs {a:%m/%d %H:%M} {seconds / 60:+.0f}分")
    return len(mine)


def _drift_table(drift: list[tuple[int, float]]) -> None:
    """分差を年代別に要約する。系統誤差なら単調に増える形で必ず現れる。"""
    buckets: dict[int, list[float]] = {}
    for year, seconds in drift:
        buckets.setdefault(year // 20 * 20, []).append(seconds)
    print("\n分差の推移（合否ではない。感度指標）")
    print(f"  {'年代':<12}{'件数':>6}{'平均':>9}{'最大絶対値':>12}")
    for start in sorted(buckets):
        values = buckets[start]
        print(f"  {start}-{start + 19:<7}{len(values):>6}"
              f"{statistics.mean(values):>8.0f}秒{max(values, key=abs):>10.0f}秒")


def verify(start: int, end: int, *, pause: float = 0.4,
           cache: Path | None = None) -> int:
    def by_year(instants):
        out: dict[int, list[dt.datetime]] = {}
        for when in instants:
            local = when.astimezone(JST)
            out.setdefault(local.year, []).append(local)
        return out

    moons = by_year(when for when, _ in tables.moon_phases())
    terms = by_year(when for when, _ in tables.solar_terms())

    failures: list[str] = []
    notable: list[str] = []
    drift: list[tuple[int, float]] = []
    checked = Counter()
    for year in range(start, end):
        try:
            checked["朔弦望"] += _compare(
                "朔弦望", year, moons.get(year, []),
                [w for w, _ in naoj_moon_phases(year, cache)],
                failures, drift, notable)
            time.sleep(pause)
            checked["節気"] += _compare("節気", year, terms.get(year, []),
                                        naoj_solar_terms(year, cache),
                                        failures, drift, notable)
            time.sleep(pause)
        except Exception as e:  # noqa: BLE001 - 通信断で全体を落とさない
            failures.append(f"{year}: 取得失敗 {type(e).__name__}: {e}")
        if year % 10 == 0:
            print(f"  ... {year} まで完了（照合 {sum(checked.values())} 件 / "
                  f"日不一致 {len(failures)} 件）", flush=True)

    print(f"\n照合 {sum(checked.values())} 件"
          f"（朔弦望 {checked['朔弦望']} / 節気 {checked['節気']}）")
    print(f"合否: JST日付の不一致 = {len(failures)} 件")
    for line in failures[:40]:
        print(f"  {line}")
    if len(failures) > 40:
        print(f"  ... 他 {len(failures) - 40} 件")

    _drift_table(drift)
    print(f"\n参考: 分差が ±{NOTABLE_MINUTES}分 を超えたもの = {len(notable)} 件"
          f"（ΔT外挿差。日が変わらない限り暦には影響しない）")
    for line in notable[:10]:
        print(f"  {line}")
    if len(notable) > 10:
        print(f"  ... 他 {len(notable) - 10} 件")
    return 1 if failures else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="天文テーブルを国立天文台と照合する")
    p.add_argument("--years", nargs=2, type=int, default=[1900, 2101],
                   metavar=("START", "END"))
    p.add_argument("--pause", type=float, default=0.4,
                   help="リクエスト間隔（秒）。公開サービスに配慮する")
    p.add_argument("--cache", type=Path, default=None,
                   help="取得したページを置くディレクトリ。再実行が無料になる。"
                        "NAOJのデータなのでリポジトリ外を指すこと")
    args = p.parse_args(argv)
    return verify(args.years[0], args.years[1], pause=args.pause, cache=args.cache)


if __name__ == "__main__":
    sys.exit(main())
