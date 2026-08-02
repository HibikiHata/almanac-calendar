"""六曜。旧暦日から求める全域関数。

    index = (旧暦月 + 旧暦日) mod 6

**この配列の順序がこのプロジェクトで最も間違えやすい1行**（ADR-0011 不変条件1）。
六曜は普通「先勝→友引→先負→仏滅→大安→赤口」と唱えるが、それは巡る順序であって
剰余の順序ではない。旧暦1月1日が先勝で `(1+1) mod 6 = 2` なので、
**インデックス2が先勝、インデックス0は大安**。暗誦順をそのまま配列にすると
全日が4つずれる。しかも一目では気づけない。
"""
from __future__ import annotations

from almanac_calendar.koyomi.lunisolar import LunarDate

#: 剰余の順序。暗誦順ではない（モジュールのdocstring参照）
ROKUYO: tuple[str, ...] = ("大安", "赤口", "先勝", "友引", "先負", "仏滅")


def rokuyo_of(lunar: LunarDate) -> str:
    """旧暦日の六曜を返す。

    閏月は前の月と同じ月番号で計算するため、`is_leap_month` は**意図的に
    使っていない**。「フィールドを参照していない＝バグ」と誤解して
    追加しないこと（テストで固定してある）。
    """
    return ROKUYO[(lunar.month + lunar.day) % 6]
