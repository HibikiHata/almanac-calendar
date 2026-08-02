"""テスト共通設定。

実行時は PYTHONPATH=<repo>/src で `almanac_calendar` パッケージとして import されるため、
テストでも同じ import 形態に揃える（src. プレフィックスを使わない）。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
