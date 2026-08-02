"""ゴールデンファイル比較。

見た目の変化を検知するための回帰テスト。デザインを意図的に変えたときは
ゴールデンを更新する必要があるが、**更新前に必ず差分を目視すること**。
差分が大きいからと中身を見ずに再生成すると、この仕組みは意味を失う。

更新方法:
    PYTHONPATH=src python3 tests/preview.py --update
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.variants import VARIANTS, render_variant

GOLDEN_DIR = Path(__file__).parent / "golden"

UPDATE_HINT = (
    "デザインを変えたなら "
    "`PYTHONPATH=src python3 tests/preview.py --update` "
    "で更新し、差分を目視してからコミットすること"
)


@pytest.mark.parametrize("name", sorted(VARIANTS))
def test_ゴールデンと一致する(name: str):
    golden = GOLDEN_DIR / f"{name}.svg"
    assert golden.exists(), f"ゴールデンが未生成: {golden}。{UPDATE_HINT}"
    assert render_variant(name) == golden.read_bytes(), f"{name} の出力が変わった。{UPDATE_HINT}"


def test_ゴールデンに余計なファイルがない():
    """定義から消した variant のゴールデンが残り続けるのを防ぐ。"""
    on_disk = {p.stem for p in GOLDEN_DIR.glob("*.svg")}
    assert on_disk == set(VARIANTS), f"定義とゴールデンがずれている: {on_disk ^ set(VARIANTS)}"


def test_全ゴールデンが有効なSVG():
    for path in sorted(GOLDEN_DIR.glob("*.svg")):
        head = path.read_bytes()[:4]
        assert head == b"<svg", f"{path.name} がSVGとして始まっていない"


def test_preview_htmlがゴールデンと同期している():
    """生成物である preview.html が、現在の定義から作れるものと一致すること。

    生成してコミットするファイルは生成器から乖離しうるので、ゴールデンと
    同じ仕組みで縛る。
    """
    from tests.preview import PREVIEW_HTML, build_html

    assert PREVIEW_HTML.exists(), f"preview.html が未生成。{UPDATE_HINT}"
    assert PREVIEW_HTML.read_text(encoding="utf-8") == build_html(), (
        f"preview.html が定義とずれている。{UPDATE_HINT}"
    )


def test_preview_htmlが参照する画像が全て存在する():
    import re

    from tests.preview import PREVIEW_HTML

    # src だけでなく <picture> の srcset も見る（片方だけ壊れても気づけるように）
    html = PREVIEW_HTML.read_text(encoding="utf-8")
    refs = set(re.findall(r'(?:src|srcset)="golden/([^"]+)"', html))
    assert refs, "プレビューが画像を1枚も参照していない"
    for ref in sorted(refs):
        assert (GOLDEN_DIR / ref).exists(), f"参照先が無い: golden/{ref}"


def test_preview_htmlがpictureの切り替えを実演している():
    """light/darkを並べるだけでは、OSテーマ追従の確認ができない。

    READMEに実際に貼る形（<picture> + prefers-color-scheme）を1つ載せて、
    切り替えを目視できる状態を保つ。
    """
    from tests.preview import PREVIEW_HTML

    html = PREVIEW_HTML.read_text(encoding="utf-8")
    assert "<picture>" in html
    assert 'media="(prefers-color-scheme: dark)"' in html
    assert 'media="(prefers-color-scheme: light)"' in html


def test_gallery_mdがゴールデンと同期している():
    """公開向けの docs/gallery.md が、現在の定義から作れるものと一致すること。

    利用者の大半はリポジトリをcloneしないので、gallery.md がGitHub上で読める
    唯一の一覧になる。**手で書くと必ず陳腐化する**ので preview.html と同じ
    定義から生成し、ずれていればここで落とす。
    """
    from tests.preview import GALLERY_MD, build_gallery

    assert GALLERY_MD.exists(), f"docs/gallery.md が未生成。{UPDATE_HINT}"
    assert GALLERY_MD.read_text(encoding="utf-8") == build_gallery(), \
        f"docs/gallery.md が定義とずれている。{UPDATE_HINT}"


def test_gallery_mdが参照する画像が全て存在する():
    import re
    html = GALLERY_MD_TEXT = (Path(__file__).parents[1] / "docs" / "gallery.md").read_text()
    refs = set(re.findall(r'src="\.\./tests/golden/([^"]+)"', html))
    assert refs, "gallery.md が画像を1枚も参照していない"
    for ref in sorted(refs):
        assert (GOLDEN_DIR / ref).exists(), f"参照先が無い: {ref}"
