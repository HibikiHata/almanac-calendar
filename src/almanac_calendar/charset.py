"""ウィジェットが描きうる文字の集合。

サブセット生成器（開発時）が「何を残すか」を、描画側（実行時）が
「manifestが足りているか」を判断する共通の出典。

**新しい文言を足したらここも足すこと。** 足し忘れても描画時に
manifest 照合で落ちるので豆腐は出ないが、落ちてから気づくことになる。

含めているもの:
  - 現在描いているもの（曜日・年月・数字・英語月名）
  - タイムゾーン略称に備えた英大文字と記号（JST / EDT / UTC+09:00 など任意）
  - S4/S5 で確定している語彙（六曜・月齢・二十四節気）。後で作り直さずに済ませるため
  - S6 の日本の祝日名（定数から機械的に集める）

含めていないもの:
  - 2033年問題の開示文（文面が未確定。S4で確定したらここへ追加し、
    サブセットを再生成する）
"""
from __future__ import annotations

# 曜日（日本語・英語）
_WEEKDAYS_JA = "日月火水木金土"
_WEEKDAYS_EN = "SunMonTueWedThuFriSat"

# 見出し
_TITLE_JA = "年月"
_MONTHS_EN = (
    "JanuaryFebruaryMarchAprilMayJuneJulyAugustSeptemberOctoberNovemberDecember"
)

_DIGITS = "0123456789"

# タイムゾーン略称は任意の3〜5文字（JST/EDT/CEST…）または UTC±HH:MM。
# 個別に列挙できないので英大文字と記号をまとめて入れる。
_TZ = "ABCDEFGHIJKLMNOPQRSTUVWXYZ+-:"

# S4: 六曜（大安・赤口・先勝・友引・先負・仏滅）
_ROKUYO = "大安赤口先勝友引負仏滅"

# S5: 月齢まわり。「旧暦」「閏」は旧暦表示（v3）で使う。
# **半角ピリオドは月齢の小数点**。全角の ． とは別の符号なので
# _PUNCT 側に入っていても足りない
_MOON = "月齢新満旧暦閏."


def _holiday_chars() -> str:
    """日本の祝日名に使われる文字。定数から機械的に集める。

    手で書き写すと、祝日名を足したときに必ず漏れる。他国の祝日名は
    文字種が定まらないので入れない（埋め込みフォントを使う場合、
    描画前に不足として落ちる）。
    """
    from almanac_calendar.koyomi.almanac import all_characters as _almanac
    from almanac_calendar.koyomi.holidays_jp import FIXED, HAPPY_MONDAY, ONE_OFF

    names = [row[2] for row in FIXED] + [row[2] for row in HAPPY_MONDAY]
    names += list(ONE_OFF.values()) + ["振替休日", "国民の休日", _almanac()]
    return "".join(names)


def _solar_term_chars() -> str:
    """二十四節気の名前に使われる文字。将来の表示に備えて先に入れておく。"""
    from almanac_calendar.koyomi.solar_terms import all_characters

    return all_characters()

# 区切りや記号（見出しやスニペットで使いうる）
_PUNCT = " ．・/()"


def required_charset() -> str:
    """必要な文字を重複なく、決定的な順序で返す。"""
    seen: dict[str, None] = {}
    for chunk in (_WEEKDAYS_JA, _TITLE_JA, _DIGITS, _WEEKDAYS_EN, _MONTHS_EN,
                  _TZ, _ROKUYO, _MOON, _solar_term_chars(),
                  _holiday_chars(), _PUNCT):
        for ch in chunk:
            seen.setdefault(ch, None)
    return "".join(seen)
