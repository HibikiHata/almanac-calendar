"""almanac_calendar CLI。

  PYTHONPATH=src python3 -m almanac_calendar calendar --out <dir> [--month YYYY-MM]

「今日」をどう決めるかがこのCLIの中心的な責務。GitHub Actions のランナーは
UTC で動くため、素直に date.today() を書くと JST の 0時〜9時のあいだ前日を
描き続ける。必ず設定されたタイムゾーンから導く。
"""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from almanac_calendar.calendar import render_pair
from almanac_calendar.config import WidgetConfig


def resolve_today(tz_name: str, *, now: datetime) -> date:
    """指定タイムゾーンでの暦日を返す。

    now は必ずタイムゾーン付きで受け取る。naive を許すとホストのTZが
    暗黙に混入し、「ランナーがUTCだから前日になる」事故が再発する。
    """
    if now.tzinfo is None:
        raise ValueError("now はタイムゾーン付きである必要があります")
    return now.astimezone(ZoneInfo(tz_name)).date()


def _parse_month(value: str) -> date:
    """YYYY-MM を月初の date にする。"""
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as e:
        raise ValueError(f"--month は YYYY-MM 形式で指定してください: {value!r}") from e
    return parsed.date().replace(day=1)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="almanac_calendar", description="READMEに貼るSVGウィジェットを生成する")
    p.add_argument("widget", nargs="?", default="calendar", choices=("calendar",))
    p.add_argument("--out", required=True, help="出力ディレクトリ")
    p.add_argument("--month", help="対象月 YYYY-MM（既定: --timezone における今月）")
    p.add_argument("--locale", default="ja", help="ja | en")
    p.add_argument("--week-start", default="sunday", help="sunday | monday")
    p.add_argument("--palette", default="default", help="配色パレット名")
    p.add_argument("--radius", type=int, default=8, help="カード外周の角丸半径px（0で直角）")
    p.add_argument("--border", action="store_true", help="カード外周に枠線を描く")
    p.add_argument("--timezone", default="Asia/Tokyo", help="「今日」を決めるタイムゾーン")
    p.add_argument("--timezone-label", action="store_true",
                   help="右下に JST / EDT などの略称を出す（既定は出さない）")
    p.add_argument("--base-url", default=".", help="スニペットに埋める公開先のベースURL")
    p.add_argument("--no-today", action="store_true", help="「今日」を強調しない")
    p.add_argument("--font", help="埋め込むサブセットフォント名（省略時は埋め込まない）")

    # 注記。**すべて既定オフ**。カレンダーの最小の役割は日付を並べること
    ann = p.add_argument_group("注記（既定はすべてオフ）")
    ann.add_argument("--rokuyo", action="store_true", help="六曜を出す")
    ann.add_argument("--solar-terms", action="store_true", help="二十四節気を出す")
    ann.add_argument("--lunar-date", action="store_true",
                     help="旧暦（天保暦）の月日を出す。閏月は 閏6/20 の形")
    ann.add_argument("--moon", action="store_true", help="月の満ち欠けを描く")
    ann.add_argument("--moon-age", action="store_true", help="月齢の数値を出す")
    ann.add_argument("--moon-position", default="corner", help="corner | below")
    ann.add_argument("--moon-amber", action="store_true", help="月を黄系で塗る")
    ann.add_argument("--holidays", dest="holiday_country",
                     help="祝日を色分けする国コード（JP / US / KR ...）")
    ann.add_argument("--holiday-names", action="store_true", help="祝日名を出す")
    ann.add_argument("--lucky-days", action="store_true",
                     help="吉日（一粒万倍日・天赦日など）を出す")
    ann.add_argument("--unlucky-days", action="store_true",
                     help="凶日（不成就日・三隣亡など）を出す")
    ann.add_argument("--ichiryu-table", default="I",
                     help="一粒万倍日の選日法 I | II（二通りが併存する）")
    ann.add_argument("--annotation-mode", default="priority",
                     help="priority（最上位1つ）| stack（該当を全部）")
    ann.add_argument("--colorize", action="store_true",
                     help="注記に色を付ける（大安と仏滅・赤口のみ）")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        config = WidgetConfig(
            artifact_base_url=args.base_url,
            locale=args.locale,
            week_start=args.week_start,
            palette=args.palette,
            display_timezone=args.timezone,
            show_timezone=args.timezone_label,
            radius=args.radius,
            border=args.border,
            font=args.font,
            show_rokuyo=args.rokuyo,
            show_solar_terms=args.solar_terms,
            show_lunar_date=args.lunar_date,
            show_moon=args.moon,
            show_moon_age=args.moon_age,
            moon_position=args.moon_position,
            moon_amber=args.moon_amber,
            holiday_country=args.holiday_country,
            show_holiday_names=args.holiday_names,
            show_lucky_days=args.lucky_days,
            show_unlucky_days=args.unlucky_days,
            ichiryu_table=args.ichiryu_table,
            annotation_mode=args.annotation_mode,
            colorize_annotations=args.colorize,
        )
        today = resolve_today(args.timezone, now=datetime.now(timezone.utc))
        target = _parse_month(args.month) if args.month else today.replace(day=1)
    except (ValueError, KeyError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2

    # today が対象月の外なら render 側で強調しない（別の月を明示指定した場合など）
    pair = render_pair(target, config=config, today=None if args.no_today else today)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "calendar-light.svg").write_bytes(pair.light)
    (out / "calendar-dark.svg").write_bytes(pair.dark)
    (out / "calendar.html").write_text(pair.snippet, encoding="utf-8")

    print(f"{target:%Y-%m} を書き出しました: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
