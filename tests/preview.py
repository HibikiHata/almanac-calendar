"""ゴールデンと目視用プレビューを生成する。

    PYTHONPATH=src python3 tests/preview.py --update

生成物は2つとも `tests/` 配下に置き、Git管理する。

  golden/*.svg   期待値（test_golden.py が比較する）
  preview.html   目視用。golden/ を相対パスで直接参照するのでコピーは作らない

プレビューがゴールデンを直接参照する理由: 別々に生成すると「目で見たもの」と
「テストが比較しているもの」が乖離する。同じ実体を見せる。

確認は `open tests/preview.html`。リポジトリ配下はmacOSの権限保護
（Desktop/Documents/Downloads）の対象外なので、ブラウザからそのまま開ける。
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT))

from tests.variants import (  # noqa: E402
    DARK_VARIANTS,
    PREVIEW_SECTIONS,
    VARIANTS,
    render_variant,
)

HERE = Path(__file__).parent
GOLDEN_DIR = HERE / "golden"
PREVIEW_HTML = HERE / "preview.html"

_CSS = """
  body { font-family: -apple-system, "Hiragino Sans", sans-serif; margin: 32px;
         background: #eef0f3; color: #1f2328; }
  h1 { font-size: 18px; margin: 0 0 6px; }
  h2 { font-size: 14px; margin: 32px 0 10px; color: #59636e; }
  p.note { color:#59636e; font-size:13px; line-height:1.8; margin:0 0 12px; max-width:780px; }
  .row { display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start; }
  figure { margin: 0; }
  figcaption { font-size: 12px; color: #59636e; margin-top: 8px; text-align: center; }
  /* GitHub のキャンバス色をそのまま再現する。padding も枠も付けない＝
     カードの周りに見える色は SVG 自身の背景色との差だけになる */
  .canvas { display: inline-block; line-height: 0; }
  .canvas-light { background: #ffffff; }
  .canvas-dark { background: #0d1117; }
  img { display: block; }
"""


def _figure(name: str) -> str:
    cls = "canvas-dark" if name in DARK_VARIANTS else "canvas-light"
    return (
        f'  <figure><div class="canvas {cls}"><img src="golden/{name}.svg" alt="{name}"></div>'
        f"<figcaption>{name}</figcaption></figure>"
    )


def build_html() -> str:
    parts = [
        "<!doctype html>",
        '<meta charset="utf-8">',
        "<title>calendar widget preview</title>",
        f"<style>{_CSS}</style>",
        "<h1>カレンダーウィジェット プレビュー</h1>",
        '<p class="note">'
        "GitHub と同じく <code>&lt;img&gt;</code> 経由で読み込んでいます。"
        "<strong>枠も余白も付けていません</strong>ので、カードの周りに色が見える場合は "
        "SVG 自身の背景色と GitHub のキャンバス色の差です。<br>"
        "表示しているのは <code>tests/golden/</code> のコミット済みファイルそのもので、"
        "テストが比較しているものと同一です。<br>"
        "更新: <code>PYTHONPATH=src python3 tests/preview.py --update</code>"
        "</p>",
    ]
    for heading, names in PREVIEW_SECTIONS:
        parts.append(f"<h2>{heading}</h2>")
        parts.append('<div class="row">')
        parts.extend(_figure(n) for n in names)
        parts.append("</div>")

    # README に貼る <picture> の実演。上の一覧は light と dark を並べて見せているだけで、
    # 「OSのテーマに応じて自動で切り替わること」は確認できない。ここだけがそのふるまいを見せる。
    parts += [
        "<h2>READMEに貼る &lt;picture&gt; の実演</h2>",
        '<p class="note">'
        "CLI が <code>calendar.html</code> として書き出すスニペットと同じ構造です。"
        "<strong>OSの外観設定をライト／ダークで切り替えると、下の1枚が入れ替わります。</strong>"
        "上の一覧は2枚を並べているだけなので、この切り替えはここでしか確認できません。"
        "</p>",
        '<div class="row">',
        '  <figure><picture>',
        '    <source media="(prefers-color-scheme: dark)" srcset="golden/default-dark.svg">',
        '    <source media="(prefers-color-scheme: light)" srcset="golden/default-light.svg">',
        '    <img alt="2026年8月 の月間カレンダー" src="golden/default-light.svg">',
        "  </picture><figcaption>OSのテーマに追従</figcaption></figure>",
        "</div>",
    ]
    return "\n".join(parts) + "\n"


def update() -> list[str]:
    """ゴールデンと preview.html を現在の出力で更新し、変わったものを返す。"""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    changed: list[str] = []

    for name in sorted(VARIANTS):
        path = GOLDEN_DIR / f"{name}.svg"
        new = render_variant(name)
        if not path.exists() or path.read_bytes() != new:
            path.write_bytes(new)
            changed.append(name)

    # 定義から消えた variant のゴールデンを掃除する
    for stale in sorted({p.stem for p in GOLDEN_DIR.glob("*.svg")} - set(VARIANTS)):
        (GOLDEN_DIR / f"{stale}.svg").unlink()
        changed.append(f"-{stale}")

    html = build_html()
    if not PREVIEW_HTML.exists() or PREVIEW_HTML.read_text(encoding="utf-8") != html:
        PREVIEW_HTML.write_text(html, encoding="utf-8")
        changed.append("preview.html")
    return changed


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ゴールデンとプレビューを生成する")
    p.add_argument("--update", action="store_true",
                   help="現在の出力で更新する（差分を目視してからコミットすること）")
    args = p.parse_args(argv)

    if not args.update:
        print("確認のみ。更新するには --update を付けてください")
        print(f"プレビュー: {PREVIEW_HTML}")
        return 0

    changed = update()
    print("更新なし" if not changed else "更新: " + ", ".join(changed))
    print(f"確認: open {PREVIEW_HTML}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
