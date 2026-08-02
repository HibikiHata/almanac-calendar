"""確認・回帰の対象にする組み合わせの一覧。

ゴールデンファイル比較（test_golden.py）と目視用プレビュー（preview.py）が
同じ定義を読む。片方だけ増えて見落とすのを防ぐため、ここを唯一の出典にする。

日付を固定しているのは、実行日によって出力が変わるとゴールデン比較が
成立しないため。今日の強調も含めて再現可能にする。
"""
from __future__ import annotations

from datetime import date

# ゴールデンを取る対象月と「今日」。実時刻には一切依存しない。
TARGET = date(2026, 8, 1)
TODAY = date(2026, 8, 1)

# name -> (WidgetConfig のキーワード引数, light|dark)
VARIANTS: dict[str, tuple[dict, str]] = {
    "default-light": ({}, "light"),
    "default-dark": ({}, "dark"),
    "mono-light": ({"palette": "mono"}, "light"),
    "mono-dark": ({"palette": "mono"}, "dark"),
    "washi-light": ({"palette": "washi"}, "light"),
    "washi-dark": ({"palette": "washi"}, "dark"),
    "en-monday-light": ({"locale": "en", "week_start": "monday"}, "light"),
    "timezone-label-light": ({"show_timezone": True}, "light"),
    "square-light": ({"radius": 0}, "light"),
    "border-light": ({"border": True}, "light"),
    "border-dark": ({"border": True}, "dark"),
    "embedded-font-light": ({"font": "noto-sans-jp"}, "light"),
    "rokuyo-light": ({"show_rokuyo": True}, "light"),
    "rokuyo-dark": ({"show_rokuyo": True}, "dark"),
    "solar-terms-light": ({"show_solar_terms": True}, "light"),
    "rokuyo-terms-light": ({"show_rokuyo": True, "show_solar_terms": True},
                           "light"),
    "rokuyo-terms-dark": ({"show_rokuyo": True, "show_solar_terms": True},
                          "dark"),
    "rokuyo-font-light": ({"show_rokuyo": True, "show_solar_terms": True,
                           "font": "noto-sans-jp"}, "light"),
    "moon-light": ({"show_moon": True}, "light"),
    "moon-dark": ({"show_moon": True}, "dark"),
    "moon-age-light": ({"show_moon": True, "show_moon_age": True}, "light"),
    "full-light": ({"show_moon": True, "show_rokuyo": True,
                    "show_solar_terms": True, "border": True}, "light"),
    "full-dark": ({"show_moon": True, "show_rokuyo": True,
                   "show_solar_terms": True, "border": True}, "dark"),
    "holiday-jp-light": ({"holiday_country": "JP",
                          "show_holiday_names": True}, "light"),
    "holiday-jp-dark": ({"holiday_country": "JP",
                         "show_holiday_names": True}, "dark"),
    "holiday-us-light": ({"holiday_country": "US", "locale": "en",
                          "week_start": "monday"}, "light"),
    "everything-light": ({"holiday_country": "JP", "show_holiday_names": True,
                          "show_moon": True, "show_rokuyo": True,
                          "show_solar_terms": True, "border": True,
                          "font": "noto-sans-jp"}, "light"),
    "stack-light": ({"show_rokuyo": True, "show_solar_terms": True,
                     "annotation_mode": "stack"}, "light"),
    "stack-all-light": ({"holiday_country": "JP", "show_holiday_names": True,
                         "show_rokuyo": True, "show_solar_terms": True,
                         "annotation_mode": "stack", "border": True}, "light"),
    "stack-all-dark": ({"holiday_country": "JP", "show_holiday_names": True,
                        "show_rokuyo": True, "show_solar_terms": True,
                        "annotation_mode": "stack", "border": True}, "dark"),
    "colorized-light": ({"show_rokuyo": True, "show_solar_terms": True,
                         "annotation_mode": "stack",
                         "colorize_annotations": True}, "light"),
    "colorized-washi-light": ({"palette": "washi", "show_rokuyo": True,
                               "show_solar_terms": True,
                               "annotation_mode": "stack",
                               "colorize_annotations": True}, "light"),
    "moon-below-light": ({"show_moon": True, "moon_position": "below",
                          "show_rokuyo": True}, "light"),
    "moon-amber-light": ({"show_moon": True, "moon_amber": True}, "light"),
    "moon-amber-dark": ({"show_moon": True, "moon_amber": True}, "dark"),
    "lucky-light": ({"show_lucky_days": True, "show_rokuyo": True,
                     "annotation_mode": "stack",
                     "colorize_annotations": True}, "light"),
    "almanac-light": ({"show_lucky_days": True, "show_unlucky_days": True,
                       "show_rokuyo": True, "annotation_mode": "stack",
                       "colorize_annotations": True, "border": True}, "light"),
    "almanac-dark": ({"show_lucky_days": True, "show_unlucky_days": True,
                      "show_rokuyo": True, "annotation_mode": "stack",
                      "colorize_annotations": True, "border": True}, "dark"),
    "almanac-table2-light": ({"show_lucky_days": True, "ichiryu_table": "II",
                              "annotation_mode": "stack"}, "light"),
}

# プレビューでどう並べるか（見出し -> 並べる variant 名）
PREVIEW_SECTIONS: list[tuple[str, list[str]]] = [
    ("default", ["default-light", "default-dark"]),
    ("mono", ["mono-light", "mono-dark"]),
    ("washi（生成り色。白いREADMEでは輪郭が出る）", ["washi-light", "washi-dark"]),
    ("オプション", ["en-monday-light", "timezone-label-light", "square-light",
                    "border-light", "border-dark"]),
    ("フォント埋め込み（S-pub。CJKフォントの無い環境でも同じ字面になる）",
     ["embedded-font-light"]),
    ("六曜（S4）。既定では出さない",
     ["rokuyo-light", "rokuyo-dark"]),
    ("二十四節気（S5b）。年24日だけに付く。六曜と併用すると節気を優先する",
     ["solar-terms-light", "rokuyo-terms-light", "rokuyo-terms-dark",
      "rokuyo-font-light"]),
    ("月の満ち欠け（S5）。形は各マスの右上、月齢は注記行",
     ["moon-light", "moon-dark", "moon-age-light"]),
    ("全部入り", ["full-light", "full-dark"]),
    ("祝日（S6）。国コードで切り替える。名前は節気より優先",
     ["holiday-jp-light", "holiday-jp-dark", "holiday-us-light",
      "everything-light"]),
    ("併記モード（stack）。優先順位で1つ選ばず、該当するものを上から詰める",
     ["stack-light", "stack-all-light", "stack-all-dark"]),
    ("注記の配色。六曜に確立した慣習は無いので、色を付ける場合だけ"
     "大安と仏滅・赤口の二極に絞る",
     ["colorized-light", "colorized-washi-light"]),
    ("月の位置と色", ["moon-below-light", "moon-amber-light", "moon-amber-dark"]),
    ("暦注（選日）。吉日と凶日は別々に切り替える。既定はどちらもオフ。"
     "最後の1枚は一粒万倍日の選日法をⅡに替えたもの",
     ["lucky-light", "almanac-light", "almanac-dark", "almanac-table2-light"]),
]

DARK_VARIANTS = {name for name, (_, mode) in VARIANTS.items() if mode == "dark"}


def render_variant(name: str) -> bytes:
    """variant 名から SVG を1枚作る。"""
    from almanac_calendar.calendar import render
    from almanac_calendar.config import WidgetConfig
    from almanac_calendar.svg.theme import PALETTES

    kwargs, mode = VARIANTS[name]
    config = WidgetConfig(**kwargs)
    theme = PALETTES[config.palette][mode]
    return render(TARGET, theme=theme, config=config, today=TODAY)
