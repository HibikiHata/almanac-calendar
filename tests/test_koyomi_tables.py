"""生成済み天文テーブルの読み込みと整合性。

テーブルは開発時に ephem で生成してコミットする（ADR-0011）。実行時は
標準ライブラリで読むだけなので、ここで縛るのは「読めること」と
「データとして筋が通っていること」の2点。

天文的な正しさ（国立天文台との一致）はテーブル生成時に検証し、
その結果ログを別途コミットする。ここでは検証しない。
"""

from __future__ import annotations

import datetime as dt

import pytest

from almanac_calendar.koyomi import tables


class TestLoad:
    def test_朔のテーブルが読める(self):
        assert len(tables.new_moons()) > 2000

    def test_二十四節気のテーブルが読める(self):
        assert len(tables.solar_terms()) > 4000

    def test_全てタイムゾーン付きのUTC(self):
        # 子午線に依存しない形で持つ（暦日の割り当てだけが地域依存）
        for row in tables.new_moons()[:50]:
            assert row.tzinfo == dt.timezone.utc
        for row, _ in tables.solar_terms()[:50]:
            assert row.tzinfo == dt.timezone.utc

    def test_時刻順に並んでいる(self):
        moons = tables.new_moons()
        assert list(moons) == sorted(moons)
        terms = [t for t, _ in tables.solar_terms()]
        assert terms == sorted(terms)

    def test_秒を保持する(self):
        """**分に丸めてはいけない。** 丸めると日界をまたぐ現象で日付が動く。

        2030年の雨水は真の値が 2月18日 23:59:40 JST。分に丸めると 00:00 に
        なり2月19日へ移る。国立天文台は同じ分単位でも `2030/02/18 24:00` と
        書いて**日付のほうを保持する**。日付の割り当ては暦の契約そのもの
        （節月の境界・月相の表示日が動く）なので、丸めた値を根拠にしない。
        """
        seconds = {row.second for row in tables.new_moons()}
        assert len(seconds) > 1, "秒がすべて0——分に丸められている"


class TestRange:
    def test_サポート範囲を覆う(self):
        # 1900-01-01 の月名を決めるには1899年の冬至が要る（ADR-0011 不変条件6）
        moons = tables.new_moons()
        assert moons[0] < dt.datetime(1899, 12, 1, tzinfo=dt.timezone.utc)
        assert moons[-1] > dt.datetime(2101, 1, 1, tzinfo=dt.timezone.utc)

    def test_サポート範囲が公開されている(self):
        lo, hi = tables.SUPPORTED_RANGE
        assert lo == dt.date(1900, 1, 1)
        assert hi == dt.date(2100, 12, 31)


class TestNewMoons:
    def test_間隔が朔望月の範囲に収まる(self):
        # 朔望月は平均29.53日だが、軌道が楕円なので29.27〜29.83日で変動する
        moons = tables.new_moons()
        gaps = [(b - a).total_seconds() / 86400 for a, b in zip(moons, moons[1:])]
        assert 29.2 < min(gaps) < 29.4, f"最小間隔が異常: {min(gaps)}"
        assert 29.6 < max(gaps) < 29.9, f"最大間隔が異常: {max(gaps)}"

    def test_1年あたり12回か13回(self):
        from collections import Counter

        per_year = Counter(m.year for m in tables.new_moons())
        for year in range(1900, 2101):
            assert per_year[year] in (12, 13), f"{year}年の朔が{per_year[year]}回"


class TestSolarTerms:
    def test_黄経は15度刻みの24種(self):
        longs = {lon for _, lon in tables.solar_terms()}
        assert longs == set(range(0, 360, 15))

    def test_1年に24個ちょうど(self):
        from collections import Counter

        per_year = Counter(t.year for t, _ in tables.solar_terms())
        for year in range(1900, 2101):
            assert per_year[year] == 24, f"{year}年の節気が{per_year[year]}個"

    def test_中気は12個で30度の倍数(self):
        chuki = [(t, lon) for t, lon in tables.solar_terms() if lon % 30 == 0]
        from collections import Counter

        per_year = Counter(t.year for t, _ in chuki)
        for year in range(1900, 2101):
            assert per_year[year] == 12, f"{year}年の中気が{per_year[year]}個"

    def test_黄経が単調に進む(self):
        # 1年で0→345まで進み、翌年また0へ戻る
        terms = tables.solar_terms()
        for (ta, la), (tb, lb) in zip(terms, terms[1:]):
            assert (lb - la) % 360 == 15, f"{ta} {la}° → {tb} {lb}°"

    def test_中気の間隔は季節で変わる(self):
        """定気法の帰結。冬至前後は約29.4日、夏至前後は約31.4日。

        朔望月（29.53日）より短くなる冬に、1つの月へ中気が2回入りうる
        ——これが閏月判定を難しくしている原因（ADR-0011 §Context）。
        """
        chuki = [(t, lon) for t, lon in tables.solar_terms() if lon % 30 == 0]
        gaps = {}
        for (ta, la), (tb, _) in zip(chuki, chuki[1:]):
            gaps.setdefault(la, []).append((tb - ta).total_seconds() / 86400)
        winter = sum(gaps[270]) / len(gaps[270])   # 冬至→大寒
        summer = sum(gaps[90]) / len(gaps[90])     # 夏至→大暑
        assert winter < 29.53 < summer, f"冬{winter:.2f}日 / 夏{summer:.2f}日"


class TestProvenance:
    def test_生成条件が記録されている(self):
        meta = tables.provenance()
        assert meta["longitude"], "黄経の定義が未記録"
        assert "apparent" in meta["longitude"].lower()
        assert meta["ephem"], "ephemのバージョンが未記録"
        assert meta["range"], "生成範囲が未記録"

    def test_未知のキーは拒否しない(self):
        assert isinstance(tables.provenance(), dict)


class TestLookups:
    def test_ある日付を含む朔月を引ける(self):
        # 2026-08-13 02:36 JST が朔なので、8/13以降8月末までは同じ朔月
        start = tables.new_moon_on_or_before(dt.date(2026, 8, 20))
        assert start.astimezone(dt.timezone(dt.timedelta(hours=9))).date() == dt.date(2026, 8, 13)

    def test_範囲外は拒否する(self):
        with pytest.raises(ValueError):
            tables.new_moon_on_or_before(dt.date(1800, 1, 1))


class TestDayBoundaryEvents:
    """JSTの日界に貼り付いた事象。国立天文台と日付が割れる既知の3件。

    1900〜2101年の全14,842事象（朔弦望9,994＋節気4,848）をNAOJと照合した
    結果、**日付が食い違うのはこれだけ**（0.03%）。いずれも真の瞬時が
    日界の±2分にあり、分単位に丸めた時点でどちらの日になるか決まらない類。

    原因はΔT（TT−UT変換）の外挿差。地球自転のゆらぎ次第で原理的に予測できず、
    NAOJ自身も暦要項の確定値は約1年半先までしか公表していない。2074年・
    2097年の「正しい朔日」は現時点では決まらない。実測した年代別の平均差は
    2060年代 −74秒、2080年代 −111秒、2100年代 −133秒で、下の2件の差
    （−60秒・−120秒）はこれで完全に説明がつく。

    直しに行かないのは、NAOJのΔTモデルに寄せることが精度向上ではなく
    追従にすぎないため。代わりにここで固定し、**テーブルを再生成したときに
    この3件以外へ増えていないこと**を担保する。増えたら定義を壊している。
    """

    #: (日付, 種別, NAOJの公表時刻) — 当実装はこの日付、NAOJは隣の日
    KNOWN = (
        (dt.date(1913, 12, 13), "望（月の形が1日ずれる。暦日には効かない）",
         "12/14 00:00"),
        (dt.date(2064, 12, 1), "弦または望（同上）", "12/02 00:00"),
        (dt.date(2074, 8, 22), "朔（旧暦7月1日が1日ずれる）", "08/23 00:00"),
        (dt.date(2095, 12, 21), "冬至（中気。ただし旧暦の月配置は変わらない）",
         "12/22 00:02"),
        (dt.date(2097, 1, 13), "朔（旧暦12月1日が1日ずれる）", "01/14 00:01"),
    )

    def test_既知の境界事象は日界の2分以内にある(self):
        JST = dt.timezone(dt.timedelta(hours=9))
        instants = [w for w, _ in tables.moon_phases()]
        instants += [w for w, _ in tables.solar_terms()]
        for day, label, _ in self.KNOWN:
            match = [w.astimezone(JST) for w in instants
                     if w.astimezone(JST).date() == day
                     and (w.astimezone(JST).hour, w.astimezone(JST).minute)
                     in ((23, 57), (23, 58), (23, 59), (0, 0), (0, 1), (0, 2))]
            assert match, f"{day} {label} が日界から離れた。定義が変わった疑い"

    def test_境界事象の総数が増えていない(self):
        """日界±3分に入る事象の数。テーブルの性質そのものなので固定できる。"""
        JST = dt.timezone(dt.timedelta(hours=9))
        low, high = tables.SUPPORTED_RANGE
        near = 0
        for when in ([w for w, _ in tables.moon_phases()]
                     + [w for w, _ in tables.solar_terms()]):
            local = when.astimezone(JST)
            if not low <= local.date() <= high:
                continue
            # 秒まで見る。分だけで測ると 23:59:40 と 23:59:05 が同じになり、
            # 丸めが日付を動かしていた頃の数え方に戻ってしまう
            minutes = local.hour * 60 + local.minute + local.second / 60
            if min(minutes, 1440 - minutes) <= 3:
                near += 1
        assert near == 56, f"日界±3分の事象が {near} 件（既知は56件）"
