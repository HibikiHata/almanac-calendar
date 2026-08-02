# Verification

A rokuyō calendar is the kind of artefact where being wrong is invisible: the output
looks entirely normal whether or not it is correct. So the calendar layers are each
checked against an independent source, and the checks are reproducible.

| Layer | Source | Scale | Result |
|---|---|---|---|
| Astronomy — moon phases and solar terms | National Astronomical Observatory of Japan (NAOJ) | 14,842 instants, 1900–2101 | 5 differ on the JST date (0.03%) |
| Lunisolar rules — month placement | Korea Astronomy and Space Science Institute (KASI) | 1,867 months, 1899–2050 | 0 unexplained differences |
| Public holidays (Japan) | `holidays` 0.101 | 2,408 dates, 1949–2099 | 0 date differences |
| Sexagenary day (干支) | KASI 日辰, plus an independent published implementation | 4 spaced anchors | agree |
| Selection days (選日) | Published 2026 almanac values | 4 coincidence claims | all reproduce |

Reproduce with:

```
PYTHONPATH=src python3 -m almanac_calendar._generate.verify_koyomi_tables --years 1900 2102
PYTHONPATH=src python3 -m almanac_calendar._generate.verify_lunisolar_rules
PYTHONPATH=src python3 -m almanac_calendar._generate.verify_holidays_jp
```

No third-party dataset is redistributed. Only the outcome is recorded here.

## Why the astronomy is checked at minute level but graded by day

The calendar's only real contract is the **JST calendar date**: if a new moon lands
on the wrong day, the whole lunar month shifts and every rokuyō in it changes.

But grading only by day is unsafe. Using geometric instead of *apparent* solar
longitude biases every mid-term by about eight minutes — a day-level comparison
passes on more than 99% of instants and fails only on the handful that straddle
midnight, which are exactly the ones that then move a month name. The minute-level
difference is therefore reported alongside as a sensitivity indicator.

That check earned its place immediately: on its first run it caught two definition
errors, a ~9-hour offset from `ephem.Ecliptic()` defaulting to J2000, and a further
~6 minutes from using astrometric rather than apparent geocentric coordinates.

## The five remaining astronomy differences

| Date | Event | Effect on the calendar |
|---|---|---|
| 1964-09-08 | 白露 | **None.** A 節, not a 中気, so it does not place months |
| 2064-12-01 | quarter or full moon | **None.** Only the drawn phase shifts |
| 2069-07-11 | quarter or full moon | Same |
| 2074-08-22 | new moon | Lunar 7/1 shifts; that month's rokuyō all change |
| 2097-01-13 | new moon | Lunar 12/1, likewise |

All five sit within two minutes of the JST day boundary. The cause is **ΔT**, the
difference between terrestrial and universal time: it depends on the Earth's
rotation and cannot be predicted, and NAOJ itself publishes confirmed values only
about 18 months ahead. Measured mean offsets grow monotonically — +1 s in the 2000s,
−36 s in the 2040s, −111 s in the 2080s, −133 s past 2100 — and both event types
drift by the same amount, which identifies it as a time-scale difference rather than
a solar-theory error.

**No correction is applied.** Matching NAOJ's ΔT model would be conformance, not
accuracy; there is no ground truth to be accurate against for a date in 2097.

### This is not peculiar to this implementation

SuikaWiki records that `qreki` — the most widely ported Japanese implementation —
"can no longer return correct results" and lists the lunar months where it is known
to be problematic: 1884-04, 1908-09, 2017-02, 2033-11, 2051-10, 2074-07, 2177-07.
**Four of the five that fall inside this project's range are precisely the months
flagged here** as having a new moon within two minutes of the boundary; the fifth,
2033-11, is the intercalary-month ambiguity below.

The established tools do not solve this — they accumulate a list of months where
implementations disagree. What is different here is that the list is derived up
front and pinned: all 64 events within ±3 minutes of the day boundary are fixed by
tests, so regenerating the tables cannot quietly move one.

## Why KASI for the rules layer

No authoritative lunar-date oracle exists in Japan. The calendar was abolished in
1872 and no government body publishes current lunar dates — NAOJ publishes the
astronomical instants but explicitly not the calendar built from them.

KASI was chosen on three criteria: the same UTC+9 boundary meridian (a Chinese-style
UTC+8 reckoning shifts new-moon days in some years), a government institute
computing independently, and no descent from the QREKI lineage — comparing against
a copy of the same implementation proves nothing.

Its endpoint returns, for a lunar (month, day, leap) triple, the Gregorian date
across a year range. Fixing day = 1 and sweeping month 1–12 × leap true/false covers
**every lunar month start in the whole range in 24 requests**. Month starts are
sufficient: days within a month are addition from the new moon.

Sixteen records differ, all before 1912, and all reproduce exactly when recomputed
at UTC+8 — KASI reckons those years on the Beijing meridian, because Korea used the
Chinese calendar directly until around then. The script classifies them as explained
only after confirming that recomputation; a merely plausible explanation is still
counted as a failure.

## Known limits

- **Supported range** is 1900-01-01 to 2100-12-31. Requests outside it raise.
- **2033-07-26 to 2034-03-20**: the Tenpō-reki rules do not determine the
  intercalary month uniquely. The leap-11th-month option is used — agreed on by the
  Japanese Calendar Culture Association, KASI, the Hong Kong Observatory and
  Koyomi no Page — and the affected months carry a flag in the data.
- **After 2050** the rules layer has no external oracle (KASI's data ends there). It
  rests on exhaustive structural invariants instead: new moon = day 1, the solstices
  and equinoxes landing in months 11/2/5/8, intercalary months containing no
  mid-term, and the intercalary count matching the Metonic 7-in-19.
- **一粒万倍日** has two selection tables in current use. Table Ⅰ is the default;
  Table Ⅱ (*Eitai Ōzassho Manreki Taisei*) is selectable.
- **二十八宿** uses the anchor `(ordinal + 24) % 28`, confirmed against the published
  2026 鬼宿日 list. Because 28 is a multiple of 7, a given mansion falls on the same
  weekday forever — 鬼宿 is always a Friday, which is asserted across 1900–2100 and
  is what would expose an off-by-one anchor.

## Sources

- National Astronomical Observatory of Japan, 暦計算室 — moon phases and solar terms
- Korea Astronomy and Space Science Institute — lunisolar conversion and 日辰
- Koyomi no Page (こよみのページ) — almanac selection rules, citing 『旧暦読本』
  (岡田芳朗) and 『こよみ読み解き事典』(岡田芳朗・阿久根末忠編)
- `vacanza/holidays` — public holidays outside Japan
