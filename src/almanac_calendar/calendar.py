"""月カレンダーの描画。

グレゴリオ暦の月の形（閏年・月の日数・先頭の曜日）は標準ライブラリの
`calendar` が完全に解いてくれるので、外部ライブラリを入れない。
ここで自前で持つのは配置と配色だけ。

日付の下の注記（六曜・二十四節気）は既定で出さない。暦の計算は
`almanac_calendar.koyomi` に閉じてあり、この層は「何をどこに置くか」しか知らない。
注記を有効にすると対応範囲（1900-01-01〜2100-12-31）に縛られる。
"""
from __future__ import annotations

import calendar as stdcal
from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo

from almanac_calendar.config import WidgetConfig
from almanac_calendar.koyomi.almanac import almanac_of, short
from almanac_calendar.koyomi.lunisolar import gregorian_to_lunar
from almanac_calendar.koyomi.moon import appearance, moon_age
from almanac_calendar.koyomi.publicholidays import holiday_name
from almanac_calendar.koyomi.rokuyo import rokuyo_of
from almanac_calendar.koyomi.solar_terms import term_by_longitude
from almanac_calendar.koyomi.tables import solar_term_on
from almanac_calendar.svg.document import Svg
from almanac_calendar.svg.fontembed import load_subset, missing_characters
from almanac_calendar.svg.moonshape import moon_path
from almanac_calendar.svg.theme import PALETTES, THEMES, Theme

# --- 版面（すべて px） ---
PAD = 16
CELL_W = 40
CELL_H = 34
TITLE_H = 38
WEEKDAY_H = 26
FOOTER_H = 20
# 注記（六曜・節気）1行ぶんの追加高さ。
# 六曜だけ／節気だけ／両方 で値を変えないのは、設定を切り替えるたびに
# 画像の高さが変わるとREADME上で他の要素が上下にずれるため。
ANNOTATION_H = 13
# 行数は月によって4〜6週になるが、常に6行分の高さで描く。
# 月ごとに画像の高さが変わるとREADME上で他の要素が上下にずれるため。
ROWS = 6

WIDTH = PAD * 2 + CELL_W * 7
HEIGHT = PAD * 2 + TITLE_H + WEEKDAY_H + CELL_H * ROWS + FOOTER_H

# 環境にあるものを順に試す指定。S1ではフォントを埋め込まないので、
# 閲覧者の環境のフォントで描画される（公開時にサブセット埋め込みへ移行する）。
FONT_STACK = (
    "ui-sans-serif, -apple-system, BlinkMacSystemFont, 'Hiragino Sans', "
    "'Noto Sans JP', 'Yu Gothic', Meiryo, sans-serif"
)

_WEEKDAYS = {
    "ja": ("日", "月", "火", "水", "木", "金", "土"),
    "en": ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"),
}
_MONTHS_EN = ("January", "February", "March", "April", "May", "June",
              "July", "August", "September", "October", "November", "December")


def _rotation(week_start: str) -> int:
    """日曜始まりの並びを何個ずらすか。"""
    if week_start == "sunday":
        return 0
    if week_start == "monday":
        return 1
    raise ValueError(f"未対応の週開始: {week_start!r}")


def month_grid(target: date, *, week_start: str = "sunday") -> list[list[int]]:
    """対象月を週ごとの2次元配列にする。月に属さないマスは 0。

    返すのは「日付を含む週」だけで、6行への詰め物は描画側で行う。
    """
    rot = _rotation(week_start)
    # stdlib の firstweekday は 月曜=0 … 日曜=6
    cal = stdcal.Calendar(firstweekday=6 if rot == 0 else 0)
    return cal.monthdayscalendar(target.year, target.month)


def _title(target: date, locale: str) -> str:
    if locale == "en":
        return f"{_MONTHS_EN[target.month - 1]} {target.year}"
    return f"{target.year}年{target.month}月"


def _weekday_labels(locale: str, week_start: str) -> tuple[str, ...]:
    labels = _WEEKDAYS[locale]
    rot = _rotation(week_start)
    return labels[rot:] + labels[:rot]


def _weekday_color(col: int, week_start: str, theme: Theme) -> str:
    """日曜を赤、土曜を青にする（日本のカレンダーの慣習）。"""
    rot = _rotation(week_start)
    weekday = (col + rot) % 7  # 0=日曜
    if weekday == 0:
        return theme.sunday
    if weekday == 6:
        return theme.saturday
    return theme.fg


#: 月の絵の半径と、マス右上からの余白（px）
MOON_R = 5
MOON_INSET = 3


def _annotated(config: WidgetConfig) -> bool:
    return (config.show_rokuyo or config.show_solar_terms
            or config.show_moon_age or config.show_holiday_names
            or config.show_lucky_days or config.show_unlucky_days)


def _holiday(day: date, config: WidgetConfig) -> str | None:
    if config.holiday_country is None:
        return None
    return holiday_name(day, config.holiday_country)


def annotation_lines(config: WidgetConfig) -> int:
    """注記に確保する行数。**中身ではなく設定だけで決める**。

    月によって行数が変わると画像の高さが変わり、READMEの他の要素が
    上下にずれる。3種が全部重なるのは年3日ほど（春分の日と秋分の日は
    定義上必ず重なる）だが、そのために毎月ぶんの高さを確保する。
    """
    if not _annotated(config):
        return 0
    if config.annotation_mode == "priority":
        return 1
    # 暦注は1日に3つ以上付きうる（天赦日＋一粒万倍日＋寅の日など）。
    # 起きうる最大ぶん確保すると高さが倍近くになるので、吉凶それぞれ
    # **1行ずつに切る**。あふれた分は描画側が優先順で捨てる
    almanac = int(config.show_lucky_days) + int(config.show_unlucky_days)
    return sum((config.show_holiday_names, config.show_solar_terms,
                config.show_rokuyo, config.show_moon_age)) + almanac


def _cell_height(config: WidgetConfig) -> int:
    extra = ANNOTATION_H * annotation_lines(config)
    if config.moon_position == "below":
        extra += MOON_R * 2 + 4
    return CELL_H + extra


def canvas_size(config: WidgetConfig) -> tuple[int, int]:
    """設定に応じた (幅, 高さ)。幅は注記の有無で変わらない。"""
    return (WIDTH,
            PAD * 2 + TITLE_H + WEEKDAY_H + _cell_height(config) * ROWS + FOOTER_H)


#: 注記の種類。上ほど優先度が高い。祝日を最上位にしているのは、その日に
#: しかなく、かつ予定に直接効く情報だから。月齢は形でも分かるので最下位
def _annotations(day: date, config: WidgetConfig) -> list[tuple[str, str]]:
    """その日に該当する注記を (種類, 文字列) で優先順に返す。

    priority モードでも stack モードでもここは同じものを返し、
    描画側が何行使うかを決める。判定を2箇所に分けない。
    """
    out: list[tuple[str, str]] = []
    if config.show_holiday_names:
        name = _holiday(day, config)
        if name:
            out.append(("holiday", name))
    if config.show_solar_terms:
        longitude = solar_term_on(day)
        if longitude is not None:
            out.append(("term", term_by_longitude(longitude).name))
    if config.show_lucky_days or config.show_unlucky_days:
        reading = almanac_of(day, ichiryu_table=config.ichiryu_table)
        if config.show_lucky_days:
            out += [("lucky", short(n)) for n in reading.lucky]
        if config.show_unlucky_days:
            out += [("unlucky", short(n)) for n in reading.unlucky]
    if config.show_rokuyo:
        out.append(("rokuyo", rokuyo_of(gregorian_to_lunar(day))))
    if config.show_moon_age:
        # 小数第1位まで。整数に丸めると朔と晦日の区別がつかなくなる
        out.append(("moon_age", f"{moon_age(day):.1f}"))
    return out


def _annotation_color(kind: str, text: str, theme: Theme,
                      config: WidgetConfig) -> str:
    """注記の色。**六曜に確立した配色慣習は無い**ので既定は無彩色。

    印刷業界の実務でも六曜は薄い色に置き、主情報と competing させないのが
    定石。色を付ける場合だけ、意味づけがはっきりしている吉凶の二極
    （大安 / 仏滅・赤口）に絞る。中間の3つは無彩色のままにする。
    """
    if not config.colorize_annotations:
        return theme.muted
    if kind == "rokuyo":
        if text == "大安":
            return theme.lucky
        if text in ("仏滅", "赤口"):
            return theme.unlucky
        return theme.muted
    if kind in ("term", "holiday"):
        return theme.fg
    if kind == "lucky":
        return theme.lucky
    if kind == "unlucky":
        return theme.unlucky
    return theme.muted


def timezone_label(tz_name: str, on: date) -> str:
    """その日のタイムゾーン略称（JST / EDT など）。

    夏時間の有無で略称が変わるため、日付を与えて解決する。
    略称を持たない地域では UTC±HH:MM 形式にフォールバックする。
    """
    moment = datetime(on.year, on.month, on.day, 12, tzinfo=ZoneInfo(tz_name))
    name = moment.tzname()
    if name and not name.startswith(("+", "-")):
        return name
    offset = moment.utcoffset()
    total = int(offset.total_seconds()) if offset else 0
    sign = "+" if total >= 0 else "-"
    total = abs(total)
    return f"UTC{sign}{total // 3600:02d}:{total % 3600 // 60:02d}"


def _drawn_text(target, weeks, config, today, mark_day) -> list[str]:
    """このSVGに実際に描く文字を全部集める（manifest照合用）。"""
    out = [_title(target, config.locale)]
    out += list(_weekday_labels(config.locale, config.week_start))
    out += [str(d) for w in weeks for d in w if d]
    out += [note for w in weeks for d in w if d
            for _, note in _annotations(target.replace(day=d), config)]
    if mark_day is not None and config.show_timezone:
        out.append(timezone_label(config.display_timezone, today))
    return out


def render(target: date, *, theme: Theme, config: WidgetConfig,
           today: date | None = None) -> bytes:
    """対象月のカレンダーSVGを1枚返す。

    target は「どの月を描くか」、today は「どの日を強調するか」。分けているのは、
    来月のカレンダーを強調なしで描くといった使い方を潰さないため。
    today が対象月の外にある場合は強調しない。
    """
    weeks = month_grid(target, week_start=config.week_start)
    title = _title(target, config.locale)
    mark_day = today.day if (today and (today.year, today.month) == (target.year, target.month)) else None
    width, height = canvas_size(config)
    cell_h = _cell_height(config)
    lines = annotation_lines(config)

    svg = Svg(
        width, height,
        title=title,
        desc=f"{title} の月間カレンダー",
    )
    # font-family は全要素に書くと出力が数倍に膨らむので、styleで一度だけ指定する。
    # フォントを指定された場合はサブセットを埋め込み、その字面を先頭に置く。
    if config.font:
        subset = load_subset(config.font)
        drawn = "".join(_drawn_text(target, weeks, config, today, mark_day))
        missing = missing_characters(drawn, subset)
        if missing:
            # 豆腐を黙って出さない。描く前に落とす
            raise ValueError(
                f"サブセット {config.font} に無い文字があります: {''.join(sorted(missing))}。"
                "charset.py に追加して再生成してください"
            )
        svg.comment(subset.license_notice())
        svg.raw_style(subset.font_face_css()
                      + f"text{{font-family:'{subset.family}',{FONT_STACK}}}")
    else:
        svg.raw_style(f"text{{font-family:{FONT_STACK}}}")
    # 枠線は内側に0.5pxずらす。矩形の輪郭に線を引くと半分が画像外に出て、
    # 上下左右で太さが不揃いに見えるため。
    if config.border:
        svg.rect(x=0.5, y=0.5, width=width - 1, height=height - 1,
                 fill=theme.bg, rx=config.radius, stroke=theme.grid)
    else:
        svg.rect(x=0, y=0, width=width, height=height, fill=theme.bg, rx=config.radius)

    # 見出し
    svg.text(title, x=width / 2, y=PAD + 25, fill=theme.fg, size=20, weight="600")

    # 曜日行
    wd_y = PAD + TITLE_H
    svg.rect(x=PAD, y=wd_y, width=CELL_W * 7, height=WEEKDAY_H,
             fill=theme.surface, rx=4)
    for col, label in enumerate(_weekday_labels(config.locale, config.week_start)):
        svg.text(
            label,
            x=PAD + CELL_W * col + CELL_W / 2,
            y=wd_y + 18,
            fill=_weekday_color(col, config.week_start, theme),
            size=12,
            weight="600",
        )

    # 日付
    grid_y = wd_y + WEEKDAY_H
    for row in range(ROWS):
        week = weeks[row] if row < len(weeks) else [0] * 7
        for col, day in enumerate(week):
            if not day:
                continue
            cx = PAD + CELL_W * col + CELL_W / 2
            cy = grid_y + cell_h * row
            is_today = day == mark_day
            when = target.replace(day=day)
            notes = _annotations(when, config)
            # 確保した行数を超えたぶんは捨てる。マスからはみ出すより、
            # 優先順位の低いものが出ないほうがまし
            notes = notes[:1 if config.annotation_mode == "priority" else lines]
            # 祝日は日曜と同じ扱いで色を変える。日本のカレンダーの慣習で、
            # 「休み」であることが色で分かるのが第一の役割
            is_holiday = _holiday(when, config) is not None
            if is_today:
                svg.rect(
                    x=PAD + CELL_W * col + 4, y=cy + 3,
                    width=CELL_W - 8, height=cell_h - 8,
                    fill=theme.today_bg, rx=7, data_today=True,
                )
            svg.text(
                str(day),
                x=cx,
                y=cy + 22,
                fill=(theme.today_fg if is_today
                      else theme.sunday if is_holiday
                      else _weekday_color(col, config.week_start, theme)),
                size=15,
                weight="600" if is_today else "normal",
            )
            for i, (kind, note) in enumerate(notes):
                # 注記は日付より小さく淡く。今日のマスの中だけは前景色に
                # 合わせる（強調色の上に muted を置くと読めなくなるため）
                svg.text(
                    note,
                    x=cx,
                    y=cy + 22 + ANNOTATION_H * (i + 1),
                    fill=(theme.today_fg if is_today
                          else _annotation_color(kind, note, theme, config)),
                    size=9,
                )
            if config.show_moon:
                # 暗い下地の円に輝面を重ねる。月が「そこに在る」ことを
                # 朔の日でも示すため、面積0のパスだけを描く形にはしない
                fraction, waxing = appearance(when)
                if config.moon_position == "below":
                    mx = cx
                    my = cy + 22 + ANNOTATION_H * lines + MOON_R + 2
                else:
                    mx = PAD + CELL_W * (col + 1) - MOON_R - MOON_INSET
                    my = cy + MOON_R + MOON_INSET
                svg.circle(cx=mx, cy=my, r=MOON_R, fill=theme.grid)
                svg.path(moon_path(cx=mx, cy=my, r=MOON_R,
                                   fraction=fraction, waxing=waxing),
                         fill=(theme.today_fg if is_today
                               else theme.moon if config.moon_amber
                               else theme.fg))

    # タイムゾーン表記（既定は出さない）。
    # 静的画像なので閲覧者ごとの時刻には追従できない。他地域の閲覧者に
    # 「ずれている」ではなく「これはこの地域の暦です」と伝えたいときに有効にする。
    if mark_day is not None and config.show_timezone:
        svg.text(
            timezone_label(config.display_timezone, today),
            x=width - PAD,
            y=height - PAD + 4,
            fill=theme.muted,
            size=10,
            anchor="end",
        )

    return svg.to_bytes()


@dataclass(frozen=True)
class RenderedPair:
    light: bytes
    dark: bytes
    snippet: str


def render_pair(target: date, *, config: WidgetConfig,
                today: date | None = None) -> RenderedPair:
    """light / dark の2枚と、READMEに貼る `<picture>` スニペットを返す。"""
    base = config.artifact_base_url.rstrip("/")
    title = _title(target, config.locale)
    alt = f"{title} の月間カレンダー" if config.locale == "ja" else f"Calendar for {title}"
    snippet = (
        "<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" srcset="{base}/calendar-dark.svg">\n'
        f'  <source media="(prefers-color-scheme: light)" srcset="{base}/calendar-light.svg">\n'
        f'  <img alt="{alt}" src="{base}/calendar-light.svg">\n'
        "</picture>\n"
    )
    palette = PALETTES[config.palette]
    return RenderedPair(
        light=render(target, theme=palette["light"], config=config, today=today),
        dark=render(target, theme=palette["dark"], config=config, today=today),
        snippet=snippet,
    )
