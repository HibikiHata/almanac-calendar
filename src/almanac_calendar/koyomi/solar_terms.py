"""二十四節気の定義表（純粋なデータ。天文計算は含まない）。

二十四節気は**太陽の位置だけ**で決まる。太陽の視黄経（地球から見た見かけの
黄経）を15度ずつ24等分し、その各点を太陽が通過する瞬間が各節気になる。
月とは無関係で、完全に太陽の暦。

そのうち**黄経が30度の倍数にあたる12個が「中気」**で、旧暦の月名を決めるのに
使う。残り12個は「節気」で、月名の決定には使わない（ADR-0011 不変条件3）。

**視黄経であることが重要**。光行差と章動を含まない幾何黄経を使うと全ての節気が
系統的に約8分ずれ、日付境界をまたぐ数件で月名が丸ごと動く（不変条件4）。

**定気法を採る**。実際の太陽が各点を通過する瞬間を節気とする方式で、天保暦が
採用したもの。地球の公転が楕円で不等速なため中気の間隔が一定でなく、
冬至前後は約29日11時間、夏至前後は約31日11時間になる。朔望月（約29.5日）より
短くなる冬に、1つの朔望月へ中気が2回入りうる——これが閏月判定を難しくしている
原因であり、2033年問題の震源でもある。
（対して、等速運動する仮想太陽を使う「平気法／恒気法」ならこの例外は起きない。）

出典: 大阪市立科学館「旧暦をつくろう」の二十四節気表と、国立天文台 暦Wiki。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SolarTerm:
    name: str
    reading: str
    longitude: int          # 太陽の視黄経（度）
    chuki_month: int | None  # 中気なら対応する旧暦の月。節気なら None

    @property
    def is_chuki(self) -> bool:
        return self.chuki_month is not None


# 春分（黄経0度）から始めず、慣例に従って立春（315度）から並べる。
# longitude は0〜345の範囲で、30の倍数が中気。
SOLAR_TERMS: tuple[SolarTerm, ...] = (
    SolarTerm("立春", "りっしゅん", 315, None),
    SolarTerm("雨水", "うすい", 330, 1),
    SolarTerm("啓蟄", "けいちつ", 345, None),
    SolarTerm("春分", "しゅんぶん", 0, 2),
    SolarTerm("清明", "せいめい", 15, None),
    SolarTerm("穀雨", "こくう", 30, 3),
    SolarTerm("立夏", "りっか", 45, None),
    SolarTerm("小満", "しょうまん", 60, 4),
    SolarTerm("芒種", "ぼうしゅ", 75, None),
    SolarTerm("夏至", "げし", 90, 5),
    SolarTerm("小暑", "しょうしょ", 105, None),
    SolarTerm("大暑", "たいしょ", 120, 6),
    SolarTerm("立秋", "りっしゅう", 135, None),
    SolarTerm("処暑", "しょしょ", 150, 7),
    SolarTerm("白露", "はくろ", 165, None),
    SolarTerm("秋分", "しゅうぶん", 180, 8),
    SolarTerm("寒露", "かんろ", 195, None),
    SolarTerm("霜降", "そうこう", 210, 9),
    SolarTerm("立冬", "りっとう", 225, None),
    SolarTerm("小雪", "しょうせつ", 240, 10),
    SolarTerm("大雪", "たいせつ", 255, None),
    SolarTerm("冬至", "とうじ", 270, 11),
    SolarTerm("小寒", "しょうかん", 285, None),
    SolarTerm("大寒", "だいかん", 300, 12),
)

CHUKI: tuple[SolarTerm, ...] = tuple(t for t in SOLAR_TERMS if t.is_chuki)

# 二至二分。1つの朔望月に中気が2回入る年に、月名を確定させるための優先制約
# （ADR-0011 不変条件3）。これを持たない中国式（冬至のみ）とは結果が分かれうる。
ANCHORS: dict[str, int] = {"春分": 2, "夏至": 5, "秋分": 8, "冬至": 11}


def term_by_longitude(longitude: int) -> SolarTerm:
    for term in SOLAR_TERMS:
        if term.longitude == longitude % 360:
            return term
    raise ValueError(f"二十四節気に対応しない黄経です: {longitude}")


def chuki_for_month(month: int) -> SolarTerm:
    """旧暦の月番号から、その月を定義する中気を返す。"""
    for term in CHUKI:
        if term.chuki_month == month:
            return term
    raise ValueError(f"旧暦の月は1〜12です: {month}")


def all_characters() -> str:
    """節気名に使われる文字（フォントのサブセット生成用）。"""
    return "".join(sorted({ch for t in SOLAR_TERMS for ch in t.name}))
