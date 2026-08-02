"""SVG を組み立てる最小の道具。

外部ライブラリを使わない理由は設計文書 §2 のとおり（配布物の実行時依存をゼロにする）。
属性の並び順を各メソッド内で固定しているのは、順序が揺れると意味のない差分が
毎日のcronで積み上がり、「今日は何が変わったのか」が読めなくなるため。
"""
from __future__ import annotations

# 置換順は & が先。後にすると既に入れた &amp; の & を二重に置換してしまう。
_ESCAPES = (
    ("&", "&amp;"),
    ("<", "&lt;"),
    (">", "&gt;"),
    ('"', "&quot;"),
    ("'", "&apos;"),
)


def escape_text(value: str) -> str:
    """SVGに埋める文字列をXMLエスケープする。

    設定値・ロケール文字列・将来のユーザー入力がそのまま流れ込むため、
    描画側で一括して通す（呼び出し側の記憶に頼らない）。
    """
    out = str(value)
    for src, dst in _ESCAPES:
        out = out.replace(src, dst)
    return out


def _num(value: float) -> str:
    """座標の文字列化。整数はそのまま、小数は固定桁で丸める。

    浮動小数の既定表現に任せると環境やバージョンで揺れうるので、桁を固定する。
    """
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return f"{value:.3f}".rstrip("0").rstrip(".")


class Svg:
    """要素を追加した順に直列化するだけの器。"""

    def __init__(self, width: int, height: int, title: str | None = None,
                 desc: str | None = None) -> None:
        if width <= 0 or height <= 0:
            raise ValueError(f"サイズは正の数である必要があります: {width}x{height}")
        self.width = width
        self.height = height
        self.title = title
        self.desc = desc
        self._parts: list[str] = []

    def rect(self, *, x: float, y: float, width: float, height: float,
             fill: str, rx: float = 0, data_today: bool = False,
             stroke: str | None = None, stroke_width: float = 1) -> None:
        attrs = (f'x="{_num(x)}" y="{_num(y)}" width="{_num(width)}" '
                 f'height="{_num(height)}" fill="{escape_text(fill)}"')
        if rx:
            attrs += f' rx="{_num(rx)}"'
        if stroke:
            attrs += f' stroke="{escape_text(stroke)}" stroke-width="{_num(stroke_width)}"'
        if data_today:
            # 「今日」を機械的に判定できるようにする印。
            # 見た目の差だけだと自動テストで確認できない（設計文書 AC-S3-1）。
            attrs += ' data-today="true"'
        self._parts.append(f"  <rect {attrs}/>")

    def text(self, content: str, *, x: float, y: float, fill: str, size: float,
             anchor: str = "middle", weight: str = "normal",
             family: str | None = None, opacity: float | None = None) -> None:
        attrs = (f'x="{_num(x)}" y="{_num(y)}" fill="{escape_text(fill)}" '
                 f'font-size="{_num(size)}" text-anchor="{escape_text(anchor)}"')
        if weight != "normal":
            attrs += f' font-weight="{escape_text(weight)}"'
        if family:
            attrs += f' font-family="{escape_text(family)}"'
        if opacity is not None:
            attrs += f' opacity="{_num(opacity)}"'
        self._parts.append(f"  <text {attrs}>{escape_text(content)}</text>")

    def line(self, *, x1: float, y1: float, x2: float, y2: float,
             stroke: str, width: float = 1) -> None:
        self._parts.append(
            f'  <line x1="{_num(x1)}" y1="{_num(y1)}" x2="{_num(x2)}" y2="{_num(y2)}" '
            f'stroke="{escape_text(stroke)}" stroke-width="{_num(width)}"/>'
        )

    def circle(self, *, cx: float, cy: float, r: float, fill: str,
               stroke: str | None = None, stroke_width: float = 1) -> None:
        attrs = (f'cx="{_num(cx)}" cy="{_num(cy)}" r="{_num(r)}" '
                 f'fill="{escape_text(fill)}"')
        if stroke:
            attrs += f' stroke="{escape_text(stroke)}" stroke-width="{_num(stroke_width)}"'
        self._parts.append(f"  <circle {attrs}/>")

    def path(self, d: str, *, fill: str) -> None:
        """パス。`d` は呼び出し側が組み立てた座標列。

        属性値に割り込める文字を弾く。ここだけは文字列をそのまま流すので、
        エスケープではなく**拒否**にしている（壊れた図形を黙って出すより、
        組み立て側の誤りとして落ちるほうがよい）。
        """
        if any(ch in d for ch in '<>"&'):
            raise ValueError(f"パスに使えない文字が含まれています: {d!r}")
        self._parts.append(f'  <path d="{d}" fill="{escape_text(fill)}"/>')

    def comment(self, text: str) -> None:
        """XMLコメントを1つ置く。ライセンス表示など。"""
        if "--" in text or "<" in text or ">" in text:
            raise ValueError("コメントに -- や山括弧は入れられません")
        self._parts.append(f"  <!-- {text} -->")

    def raw_style(self, css: str) -> None:
        """`<style>` を1つ置く。CSSはエスケープしない（`<` を含めない前提）。"""
        if "<" in css or "&" in css:
            raise ValueError("style に < や & は入れられません")
        self._parts.append(f"  <style>{css}</style>")

    def to_bytes(self) -> bytes:
        head = [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {self.width} {self.height}" '
            f'width="{self.width}" height="{self.height}"'
            + (' role="img"' if self.title else "")
            + ">"
        ]
        if self.title:
            head.append(f"  <title>{escape_text(self.title)}</title>")
        if self.desc:
            head.append(f"  <desc>{escape_text(self.desc)}</desc>")
        body = head + self._parts + ["</svg>", ""]
        return "\n".join(body).encode("utf-8")
