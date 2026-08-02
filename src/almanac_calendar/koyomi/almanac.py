"""暦注（選日）。一粒万倍日・天赦日などの吉日と、不成就日などの凶日。

**天文計算は一切増えない**。すべて (1)日の干支 (2)節月 (3)旧暦の月日 の
組み合わせによる表引きで、3つとも既に手元にある。誤りが入る余地は
**表の転記だけ**なので、表は出典の並びのまま書き、テストで固定する。

出典は こよみのページ（koyomi8.com）の暦注解説。同サイトは選日法の典拠を
『旧暦読本』（岡田芳朗）『こよみ読み解き事典』（岡田芳朗・阿久根末忠編）と
明示している。

**一粒万倍日には二通りの選日法が併存する**（不変条件: ADR-0012）。
現行の暦で主流の表Ⅰを既定にし、『永代大雑書萬暦大成』記載の表Ⅱも選べる。
旧暦の2033年問題と同じで、唯一の正解が存在しない。

**鬼宿日の基準**は、こよみのページの計算コード `SYUKU[(JD + 12) % 28]` から
取り、公表されている2026年の鬼宿日13日と全件照合して確定した。同じコードから
読める干支の基準は、KASIから独立に導いた値と一致する（2系統で一致）。

これらは吉凶を占う迷信であり、六曜と同じ社会的な留保が要る（ADR-0011
事実10）。**既定はすべてオフ**で、吉日と凶日は別々に切り替えられる。
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from almanac_calendar.koyomi.lunisolar import gregorian_to_lunar
from almanac_calendar.koyomi.sexagenary import (day_branch, day_sexagenary, mansion,
                                       season, solar_month)

#: 一粒万倍日 表Ⅰ: 節月 -> 該当する日の十二支。現行の暦で主流
ICHIRYU_I: dict[int, tuple[str, ...]] = {
    1: ("丑", "午"), 2: ("酉", "寅"), 3: ("子", "卯"), 4: ("卯", "辰"),
    5: ("巳", "午"), 6: ("酉", "午"), 7: ("子", "未"), 8: ("卯", "申"),
    9: ("酉", "午"), 10: ("酉", "戌"), 11: ("亥", "子"), 12: ("卯", "子"),
}

#: 一粒万倍日 表Ⅱ: 『永代大雑書萬暦大成』記載。節月ごとに1つだけ
ICHIRYU_II: dict[int, tuple[str, ...]] = {
    1: ("酉",), 2: ("申",), 3: ("未",), 4: ("午",), 5: ("巳",), 6: ("辰",),
    7: ("卯",), 8: ("寅",), 9: ("丑",), 10: ("子",), 11: ("亥",), 12: ("戌",),
}

ICHIRYU_TABLES = {"I": ICHIRYU_I, "II": ICHIRYU_II}

#: 天赦日: 節切りの季節 -> 該当する日の干支。年に5〜6日しかない大吉日
TENSHA: dict[str, str] = {"春": "戊寅", "夏": "甲午", "秋": "戊申", "冬": "甲子"}

#: 不成就日: 旧暦の月 -> 該当する旧暦の日
FUJOJU: dict[int, tuple[int, ...]] = {
    1: (3, 11, 19, 27), 7: (3, 11, 19, 27),
    2: (2, 10, 18, 26), 8: (2, 10, 18, 26),
    3: (1, 9, 17, 25), 9: (1, 9, 17, 25),
    4: (4, 12, 20, 28), 10: (4, 12, 20, 28),
    5: (5, 13, 21, 29), 11: (5, 13, 21, 29),
    6: (6, 14, 22, 30), 12: (6, 14, 22, 30),
}

#: 三隣亡: 節月 -> 日の十二支。
#: 古い暦では「三輪宝」＝家を建てるによい日だった。転記の誤りで
#: 吉日が凶日に転じたと考えられている（出典に明記）
SANRINBO: dict[int, str] = {1: "亥", 4: "亥", 7: "亥", 10: "亥",
                            2: "寅", 5: "寅", 8: "寅", 11: "寅",
                            3: "午", 6: "午", 9: "午", 12: "午"}

#: 受死日（黒日）: 節月 -> 日の十二支。暦注のうち最悪とされる日
JUSHI: dict[int, str] = {1: "戌", 2: "辰", 3: "亥", 4: "巳", 5: "子", 6: "午",
                         7: "丑", 8: "未", 9: "寅", 10: "申", 11: "卯", 12: "酉"}


@dataclass(frozen=True)
class Almanac:
    """その日の暦注。吉日と凶日を分けて持つ。

    重なりは珍しくない——出典も「他の吉日と重なれば効果は倍増、凶日と
    重なると効果半減」と書いている。どちらかに丸めず両方返す。
    """
    lucky: tuple[str, ...]
    unlucky: tuple[str, ...]

    def __bool__(self) -> bool:
        return bool(self.lucky or self.unlucky)


def almanac_of(day: dt.date, *, ichiryu_table: str = "I") -> Almanac:
    """その日の暦注を求める。`ichiryu_table` は "I" か "II"。"""
    if ichiryu_table not in ICHIRYU_TABLES:
        raise ValueError(
            f"未対応の選日法: {ichiryu_table!r}（{tuple(ICHIRYU_TABLES)} のいずれか）")

    month = solar_month(day)
    branch = day_branch(day)
    ganshi = day_sexagenary(day)
    lunar = gregorian_to_lunar(day)

    lucky: list[str] = []
    unlucky: list[str] = []

    # 天赦日を先頭に置く。年5〜6日しかない最上位の吉日で、
    # 重なったときに埋もれさせない
    if TENSHA[season(day)] == ganshi:
        lucky.append("天赦日")
    if branch in ICHIRYU_TABLES[ichiryu_table][month]:
        lucky.append("一粒万倍日")
    if branch == "寅":
        lucky.append("寅の日")
    if ganshi == "己巳":
        lucky.append("己巳の日")
    elif branch == "巳":
        lucky.append("巳の日")
    if mansion(day) == "鬼":
        lucky.append("鬼宿日")

    if lunar.day in FUJOJU[lunar.month]:
        unlucky.append("不成就日")
    if branch == SANRINBO[month]:
        unlucky.append("三隣亡")
    if branch == JUSHI[month]:
        unlucky.append("受死日")

    return Almanac(tuple(lucky), tuple(unlucky))


#: 表示用の略記。**マス幅40pxに「一粒万倍日」は入らない**（9px×5字＝45px）。
#: 2文字に揃えると六曜・節気と同じ幅になり、行が揃う。市販の暦も
#: 「一粒」「天赦」「不成」のように略すので、見た目の慣習とも合う
SHORT: dict[str, str] = {
    "天赦日": "天赦", "一粒万倍日": "一粒", "寅の日": "寅日",
    "巳の日": "巳日", "己巳の日": "己巳",
    "鬼宿日": "鬼宿",
    "不成就日": "不成", "三隣亡": "三隣", "受死日": "受死",
}


def short(name: str) -> str:
    """表示用の略記を返す。未登録ならそのまま返す。"""
    return SHORT.get(name, name)


def all_characters() -> str:
    """暦注の名前に使う文字。フォントサブセット用。略記も正式名も入れる。"""
    return "".join(SHORT) + "".join(SHORT.values())
