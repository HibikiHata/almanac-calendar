"""月の満ち欠けをSVGパスにする。

輝いている側の境界は2本の弧でできている。**外側は必ず半径rの半円**
（月の縁そのもの）で、**内側は明暗境界線**。明暗境界線は球面上の大円を
真横から見たものなので、画面上では半径rの円を横方向に潰した半楕円になる。

潰し具合は輝面比fだけで決まり、横半径は `r*|1-2f|`。

  f=0   （朔）  横半径r・右に膨らむ → 面積0
  f=0.25（三日月）横半径r/2・右に膨らむ → 細い弧
  f=0.5 （半月）横半径0 → 直線。ここで膨らむ向きが反転する
  f=0.75（凸月）横半径r/2・左に膨らむ
  f=1   （望）  横半径r・左に膨らむ → 真円

向きの反転を境界条件として持たせず、SVGの sweep フラグ1つに畳んである
（`f > 0.5` かどうか）。北半球の見え方を基準にし、満ちる側は右が輝く。
"""
from __future__ import annotations

from almanac_calendar.svg.document import _num


def moon_path(*, cx: float, cy: float, r: float, fraction: float,
              waxing: bool) -> str:
    """輝面のパス。`fraction` は輝面比 0〜1。

    朔（fraction≈0）は面積0のパスになる。呼び出し側で「描かない」判断を
    するのではなく空に近いパスを返すのは、月が確かにそこに在ることを
    暗い円で示す描き方（下地の円＋この上塗り）を壊さないため。
    """
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"輝面比は0〜1です: {fraction}")
    if r <= 0:
        raise ValueError(f"半径は正の数です: {r}")

    # 明暗境界線の横半径。半月でちょうど0になり、そこで膨らむ向きが変わる
    rx = r * abs(1 - 2 * fraction)
    # 満ちる側は右、欠ける側は左が輝く（北半球）
    limb_sweep = 1 if waxing else 0
    # 凸（f>0.5）なら明暗境界線は反対側へ膨らむ
    term_sweep = limb_sweep if fraction > 0.5 else 1 - limb_sweep

    top, bottom = _num(cy - r), _num(cy + r)
    x, rr = _num(cx), _num(r)
    return (f"M{x},{top}"
            f"A{rr},{rr} 0 0,{limb_sweep} {x},{bottom}"
            f"A{_num(rx)},{rr} 0 0,{term_sweep} {x},{top}Z")
