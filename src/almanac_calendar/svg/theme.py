"""配色。パレット × (light / dark) の2次元で持つ。

SVG内の `@media (prefers-color-scheme)` を使わず2枚出しにしている理由は
設計文書 §4.3 のとおり。あれはGitHubのテーマ切り替えではなくOSの設定に解決され、
Safari ではそもそも効かない。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Theme:
    name: str
    bg: str          # 背景
    surface: str     # 曜日帯など一段沈めた面
    fg: str          # 主要な文字
    muted: str       # 補助的な文字（タイムゾーン表記など）
    grid: str        # 罫線
    sunday: str      # 日曜の文字色
    saturday: str    # 土曜の文字色
    today_bg: str    # 「今日」のセルの塗り
    today_fg: str    # 「今日」の文字色
    lucky: str       # 吉の注記（大安）。既定では使わない
    unlucky: str     # 凶の注記（仏滅・赤口）。既定では使わない
    moon: str        # 月の輝面。既定では fg を使い、これは黄色系の選択肢


# パレットは「名前 → light/dark の対」。利用者は名前で選ぶ。
PALETTES: dict[str, dict[str, Theme]] = {
    # GitHub の既定キャンバスに馴染ませたもの
    "default": {
        "light": Theme(
            name="default-light",
            bg="#ffffff", surface="#f6f8fa", fg="#1f2328", muted="#59636e",
            grid="#d1d9e0", sunday="#cf222e", saturday="#0969da",
            today_bg="#0969da", today_fg="#ffffff",
            lucky="#1a7f37", unlucky="#8250df", moon="#d4a017",
        ),
        "dark": Theme(
            name="default-dark",
            bg="#0d1117", surface="#161b22", fg="#e6edf3", muted="#9198a1",
            grid="#30363d", sunday="#ff7b72", saturday="#79c0ff",
            today_bg="#1f6feb", today_fg="#ffffff",
            lucky="#3fb950", unlucky="#bc8cff", moon="#e3b341",
        ),
    },
    # 曜日で色を変えない無彩色版。他の配色と並べても喧嘩しない
    "mono": {
        "light": Theme(
            name="mono-light",
            bg="#ffffff", surface="#f2f2f2", fg="#1a1a1a", muted="#767676",
            grid="#dcdcdc", sunday="#1a1a1a", saturday="#1a1a1a",
            today_bg="#1a1a1a", today_fg="#ffffff",
            lucky="#1a1a1a", unlucky="#767676", moon="#b8860b",
        ),
        "dark": Theme(
            name="mono-dark",
            bg="#111111", surface="#1c1c1c", fg="#ededed", muted="#9a9a9a",
            grid="#333333", sunday="#ededed", saturday="#ededed",
            today_bg="#ededed", today_fg="#111111",
            lucky="#ededed", unlucky="#9a9a9a", moon="#d4b169",
        ),
    },
    # 紙と墨。和のカレンダーに寄せた配色
    "washi": {
        "light": Theme(
            name="washi-light",
            bg="#fbf7ef", surface="#f2ebdd", fg="#3d3529", muted="#8a7f6d",
            grid="#e0d6c2", sunday="#b03a2e", saturday="#2e6f8e",
            today_bg="#b03a2e", today_fg="#fbf7ef",
            lucky="#4a7c3f", unlucky="#7a5c8d", moon="#c79a2e",
        ),
        "dark": Theme(
            name="washi-dark",
            bg="#1c1a17", surface="#26231e", fg="#ece3d4", muted="#a19683",
            grid="#3b362e", sunday="#e2795f", saturday="#7fb3cc",
            today_bg="#e2795f", today_fg="#1c1a17",
            lucky="#8fbf7f", unlucky="#b799c9", moon="#dcb85f",
        ),
    },
}

# 既定パレットへの近道（S1からの呼び出しを壊さないため）
THEMES: dict[str, Theme] = PALETTES["default"]
