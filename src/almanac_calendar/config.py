"""ウィジェットの設定。

将来はYAML等に外出しして利用者が編集できるようにするが、現時点では
データクラスのまま扱う。不正値は生成時に落とす（描画してから気づくのを避ける）。
"""
from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from almanac_calendar.svg.theme import PALETTES

LOCALES = ("ja", "en")
WEEK_STARTS = ("sunday", "monday")
ANNOTATION_MODES = ("priority", "stack")
MOON_POSITIONS = ("corner", "below")


@dataclass(frozen=True)
class WidgetConfig:
    # 公開先のベースURL。<picture> スニペットの src に入る。
    # 利用者ごとに変わるため埋め込みではなく設定にしている。
    artifact_base_url: str = "."
    locale: str = "ja"
    week_start: str = "sunday"
    palette: str = "default"
    # グリッドの「今日」をどのタイムゾーンの暦日で決めるか。
    # 六曜の計算は別で、常に固定UTC+09:00（ADR-0011 不変条件2）。
    display_timezone: str = "Asia/Tokyo"
    # 右下に JST / EDT などの略称を出すか。
    # 既定は出さない。自分のREADMEに置く分には自明で、
    # 他地域の閲覧者に断りを入れたいときだけ有効にする性質のものなので。
    show_timezone: bool = False
    # カード外周の角丸半径（px）。0 で直角。
    # GitHub は README 内の style 属性を全削除するので、CSSで角を丸めることはできない。
    # カード風の見た目が要るならSVGの中で描くしかないため、設定として持つ。
    radius: int = 8
    # カード外周に1px の枠線を描くか。
    # 角丸だけでは、カード色とGitHubのキャンバス色が同じ場合に丸みが見えない。
    # 「カードらしさ」を出したいときは枠線が要る。
    border: bool = False
    # 埋め込むサブセットフォント名。None なら埋め込まず、閲覧者の環境の
    # フォントに任せる（CJKフォントの無い環境では豆腐になる）。
    font: str | None = None
    # 日付の下に六曜を出すか。既定は出さない（ADR-0011 不変条件8）。
    # カレンダーとしての最小の役割は日付を並べることで、六曜は使う人だけが
    # 使う情報。有効にすると対応範囲（1900-01-01〜2100-12-31）に縛られる。
    show_rokuyo: bool = False
    # 日付の下に二十四節気を出すか。年24日だけに付く。
    # 六曜と同時に有効にした場合は節気を優先する（その日にしかない情報のため）。
    show_solar_terms: bool = False
    # 各マスの右上に月の満ち欠けを小さく描くか。
    # 注記行（六曜・節気）とは別レイヤーなので、文字の優先順位争いに入らない。
    show_moon: bool = False
    # 注記行に月齢の数値を出すか。優先順位は 節気 > 六曜 > 月齢。
    # 形だけで足りることも多いので独立の設定にしている。
    show_moon_age: bool = False
    # 祝日を色分けする国コード（ISO 3166-1 alpha-2）。None で祝日を扱わない。
    # **タイムゾーンでも言語でもなく国**。海外から見る人にも自分の国の
    # 祝日を出せるようにするための設定で、locale とは独立している。
    holiday_country: str | None = None
    # 祝日名を注記行に出すか。優先順位は 祝日 > 節気 > 六曜 > 月齢。
    # その日にしかなく、かつ予定に直接効く情報なので最優先にしている。
    show_holiday_names: bool = False
    # 注記が複数ある日の扱い。
    #   priority: 優先順位の最上位だけを1行で出す（既定）
    #   stack   : 該当するものを全部、上から詰めて複数行で出す
    # 横に並べる案（「赤口・立秋」等）は採らなかった。マス幅40pxに対し
    # 9pxの日本語5〜6文字は45〜54pxで必ずはみ出し、収めるには7px以下まで
    # 縮める必要がある。行を足すほうが読める（設計判断）
    annotation_mode: str = "priority"
    # 注記に色を付けるか。**六曜に確立した配色慣習は無い**ので既定は無彩色。
    # 有効にすると 大安=lucky / 仏滅・赤口=unlucky / 節気=fg になる
    colorize_annotations: bool = False
    # 月をどこに描くか。corner はマスの右上、below は注記行の下。
    # below は日付・注記・月が縦に並ぶので、月を主役にしたいときに使う
    moon_position: str = "corner"
    # 月の輝面をテーマの月色（黄系）で塗るか。既定は文字色と同じ無彩色。
    moon_amber: bool = False
    # 暦注（選日）を出すか。吉日と凶日を別々に切り替える。
    # 吉凶を占う迷信なので、六曜と同じく既定はオフ（ADR-0011 事実10）。
    # 凶日を分けているのは、「最悪の日」を人のREADMEに出すかは
    # 吉日を出すかとは別の判断だから
    show_lucky_days: bool = False
    show_unlucky_days: bool = False
    # 一粒万倍日の選日法。**二通りが併存し、唯一の正解が無い**。
    # I は現行の暦で主流、II は『永代大雑書萬暦大成』記載のもの
    ichiryu_table: str = "I"

    def __post_init__(self) -> None:
        if self.locale not in LOCALES:
            raise ValueError(f"未対応のロケール: {self.locale!r}（{LOCALES} のいずれか）")
        if self.week_start not in WEEK_STARTS:
            raise ValueError(f"未対応の週開始: {self.week_start!r}（{WEEK_STARTS} のいずれか）")
        if self.palette not in PALETTES:
            raise ValueError(
                f"未対応のパレット: {self.palette!r}（{tuple(PALETTES)} のいずれか）"
            )
        if not self.artifact_base_url:
            raise ValueError("artifact_base_url が空です")
        if self.font is not None:
            from almanac_calendar.svg.fontembed import available_subsets

            if self.font not in available_subsets():
                raise ValueError(
                    f"未対応のフォント: {self.font!r}"
                    f"（生成済み: {available_subsets() or 'なし'}）"
                )
        if self.holiday_country is not None:
            from almanac_calendar.koyomi.publicholidays import available_countries

            if self.holiday_country.upper() not in available_countries():
                raise ValueError(
                    f"未対応の国コード: {self.holiday_country!r}"
                    f"（生成済み: {', '.join(available_countries())}）"
                )
        if self.annotation_mode not in ANNOTATION_MODES:
            raise ValueError(
                f"未対応の注記モード: {self.annotation_mode!r}"
                f"（{ANNOTATION_MODES} のいずれか）")
        from almanac_calendar.koyomi.almanac import ICHIRYU_TABLES

        if self.ichiryu_table not in ICHIRYU_TABLES:
            raise ValueError(
                f"未対応の選日法: {self.ichiryu_table!r}"
                f"（{tuple(ICHIRYU_TABLES)} のいずれか）")
        if self.moon_position not in MOON_POSITIONS:
            raise ValueError(
                f"未対応の月の位置: {self.moon_position!r}"
                f"（{MOON_POSITIONS} のいずれか）")
        if self.moon_position == "below" and not self.show_moon:
            raise ValueError("moon_position には show_moon が要ります")
        if self.show_holiday_names and self.holiday_country is None:
            raise ValueError("show_holiday_names には holiday_country が要ります")
        if self.radius < 0:
            raise ValueError(f"radius は0以上である必要があります: {self.radius}")
        # タイムゾーンは描画時ではなく設定時に検証する。
        # Windowsでは tzdata パッケージが無いと解決できないため、
        # 失敗したことが分かるメッセージにしておく。
        try:
            ZoneInfo(self.display_timezone)
        except (ZoneInfoNotFoundError, ValueError) as e:
            raise ValueError(
                f"未知のタイムゾーン: {self.display_timezone!r}（{e}）"
            ) from e
