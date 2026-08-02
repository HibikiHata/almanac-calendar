<div align="center">

# almanac-calendar

**A monthly calendar as a deterministic SVG** — with the Japanese almanac layer
(rokuyō, the 24 solar terms, moon phase, selection days) and public holidays for
250+ countries.

<img src="tests/golden/en-light.svg" width="312" alt="Calendar, light theme">
<img src="tests/golden/en-dark.svg" width="312" alt="Calendar, dark theme">

<sub>The default: dates and nothing else. Everything below is opt-in.</sub>

</div>

Everything is drawn from tables computed ahead of time, so **rendering needs nothing
but the Python standard library** — no ephemeris download, no API, no network.
The same inputs always produce byte-identical output.

---

## Quick start

### Just paste it (no setup)

Drop this into any Markdown file. Light and dark versions switch with the reader's
GitHub theme.

```html
<picture>
  <source media="(prefers-color-scheme: dark)"
          srcset="https://raw.githubusercontent.com/HibikiHata/almanac-calendar/output/calendar-dark.svg">
  <img alt="Calendar" src="https://raw.githubusercontent.com/HibikiHata/almanac-calendar/output/calendar-light.svg">
</picture>
```

This works because a calendar does not depend on who is looking at it — one shared
image serves everyone.

Six variants are pre-rendered. Swap the filename to pick one:

| Filename | What you get |
|---|---|
| `calendar-{light,dark}.svg` | Plain calendar, Japanese, JST |
| `calendar-en-{light,dark}.svg` | Plain calendar, English, UTC |
| `calendar-rokuyo-{light,dark}.svg` | With rokuyō |
| `calendar-full-{light,dark}.svg` | Holidays, solar terms, rokuyō and moon |
| `calendar-washi-{light,dark}.svg` | `washi` palette with coloured rokuyō |
| `calendar-moon-{light,dark}.svg` | Moon phase below the rokuyō |

They are regenerated four times a day. The timezone is baked into each image, so pick
the variant that matches your audience.

### Generate your own (GitHub Action)

Use this when you want your own options — a different palette, another country's
holidays, or the almanac annotations turned on.

```yaml
- uses: HibikiHata/almanac-calendar@v1
  with:
    out: dist
    rokuyo: "true"
    holidays: "JP"
```

A complete workflow, including committing the result, is in
[`examples/workflow.yml`](examples/workflow.yml).

## Gallery

**Rokuyō** — the six-day cycle, under each date.

<img src="tests/golden/rokuyo-light.svg" width="312" alt="Rokuyō, light theme">
<img src="tests/golden/rokuyo-dark.svg" width="312" alt="Rokuyō, dark theme">

**Moon phase** — drawn from the real illuminated fraction, not interpolated from the
moon's age. Here below the annotation line, in the palette's moon colour.

<img src="tests/golden/moon-amber-below-light.svg" width="312" alt="Moon phase, light theme">
<img src="tests/golden/moon-amber-below-dark.svg" width="312" alt="Moon phase, dark theme">

Palettes are `default` (matches GitHub's canvas), `mono` (no weekday colours) and
`washi` (paper and ink); each ships light and dark.

**[See every option with its image →](docs/gallery.md)**

## Options

All annotations are **off by default**. A calendar's minimum job is to show dates.

| Input | Default | What it does |
|---|---|---|
| `out` | `dist` | Output directory |
| `month` | current | Target month as `YYYY-MM` |
| `timezone` | `Asia/Tokyo` | Which zone decides "today". Runners are on UTC, so this matters |
| `locale` | `ja` | `ja` / `en` |
| `week_start` | `sunday` | `sunday` / `monday` |
| `palette` | `default` | `default` / `mono` / `washi` |
| `border` | `false` | 1px card border |
| `radius` | `8` | Corner radius in px, `0` for square |
| `font` | *(none)* | `noto-sans-jp` embeds a subset so the text looks identical everywhere |
| `rokuyo` | `false` | Six-day cycle (大安, 仏滅, …) |
| `solar_terms` | `false` | The 24 solar terms — 24 days a year |
| `lunar_date` | `false` | The lunisolar date, as `6/20`; a leap month reads `閏6/20` |
| `moon` | `false` | Moon phase drawn in each cell |
| `moon_age` | `false` | Numeric moon age |
| `moon_amber` | `false` | Fill the lit face amber instead of the text colour |
| `holidays` | *(none)* | ISO 3166-1 alpha-2 code — `JP`, `US`, `KR`, … |
| `holiday_names` | `false` | Print the holiday name |
| `lucky_days` | `false` | Auspicious days (一粒万倍日, 天赦日, …) |
| `unlucky_days` | `false` | Inauspicious days (不成就日, 三隣亡, …) |
| `annotation_mode` | `priority` | `priority` shows the top-ranked note; `stack` shows all of them |
| `colorize` | `false` | Colour 大安 and 仏滅/赤口 |

**On `timezone`.** The boundary meridian used for the *calendar itself* is fixed —
the Japanese lunisolar calendar is reckoned at 135°E and does not follow the viewer.
`timezone` only decides which day gets highlighted.

**On `annotation_mode`.** In `priority` mode the ranking is
holiday → solar term → lucky → unlucky → rokuyō → lunisolar date → moon age. In `stack` mode every
applicable note is drawn, packed from the top. Reserved height comes from the
configuration, never the content, so the image is the same height every month.

## Reference — what the annotations mean

You do not need to know any of this to use the calendar, but here is what the words
say.

### Rokuyō (六曜)

A six-day cycle derived from the lunisolar date, widespread in Japan since the late
Edo period. Meanings below follow *Ansei Zassho* as reproduced by Koyomi no Page.

| | Reading | Meaning | |
|---|---|---|---|
| 大安 | taian | Favourable for anything. Weddings are commonly booked on these days | ◎ |
| 友引 | tomobiki | Favourable except around midday (11:00–13:00). Funerals are avoided — the name reads as "pulls a friend along" | ○ |
| 先勝 | senshō | Morning is fine, afternoon is not. "Haste brings luck" | ○ morning |
| 先負 | senbu | Morning is not, afternoon is fine. "Haste brings loss" | ○ afternoon |
| 赤口 | shakkō | Unfavourable, except the hour around noon | ✕ |
| 仏滅 | butsumetsu | The least favourable of the six | ✕✕ |

### Lucky days (吉日)

| | Reading | Where it comes from | How often |
|---|---|---|---|
| 天赦日 | tenshanichi | "The day heaven forgives all" — the most auspicious day in the Japanese almanac | **5–6 days a year** |
| 一粒万倍日 | ichiryū manbai-bi | "One grain, ten thousand times" — one seed becoming a full ear of rice. Good for starting things; traditionally *not* for borrowing, since the debt multiplies too | ~60 days a year |
| 鬼宿日 | kishuku-nichi | The "Ghost" mansion of the 28 lunar mansions. Auspicious for everything except weddings | every 28 days |
| 寅の日 | tora no hi | The tiger travels a thousand *ri* and returns — so money spent comes back | every 12 days |
| 巳の日 / 己巳の日 | mi no hi / tsuchinoto-mi | The snake is Benzaiten's messenger; wealth and the arts. 己巳 is the stronger one | every 12 / 60 days |

### Unlucky days (凶日)

| | Reading | Meaning |
|---|---|---|
| 不成就日 | fujōju-nichi | "Nothing comes to fruition" |
| 三隣亡 | sanrinbō | Unfavourable for building. Older almanacs write 三輪宝 and call it a *good* day for it |
| 受死日 (黒日) | jushi-nichi / kurobi | The most inauspicious. Only funerals are permitted |

### The lunisolar date (旧暦)

Japan used a **lunisolar** calendar until 1873 — months follow the moon, and a leap
month is inserted every few years to keep the year in step with the sun. It is often
called 太陰暦 ("lunar calendar"), but that is a different thing: a purely lunar
calendar has no leap month and drifts about eleven days a year against the seasons.

The dates do not line up with the Gregorian ones at all. 2026-08-02 is the **20th day
of the 6th lunar month**. Months are 29 or 30 days; a year has 12 or 13 of them.

`lunar_date` prints it as `6/20`, and `閏6/20` when the month is intercalary.
**Rokuyō is derived from this** — it is `(month + day) mod 6` — so turning both on
lets you check the rokuyō against the number it came from.

### Solar terms (二十四節気)

Twenty-four points where the sun's apparent ecliptic longitude crosses a multiple of
15°. They mark the seasons — 立春 (start of spring), 夏至 (summer solstice),
立秋 (start of autumn), 冬至 (winter solstice) and twenty more. Two fall in every
month, and 春分 and 秋分 are also Japanese public holidays.

## What it computes

Instants for the moon's four phases and the 24 solar terms are computed at build
time with `ephem` and shipped as CSV, covering **1900-01-01 to 2100-12-31**. At
render time the package reads those tables and applies the calendar rules in pure
Python.

The lunisolar layer follows Tenpō-reki: the day containing the new moon is day 1,
the month is named by the mid-term it contains, a month with no mid-term is
intercalary. Rokuyō is then `(lunar month + lunar day) mod 6`.

### Accuracy

| Layer | Checked against | Scale | Result |
|---|---|---|---|
| Astronomy | National Astronomical Observatory of Japan | 14,842 instants | 5 differ on the JST date (0.03%) |
| Lunisolar rules | Korea Astronomy and Space Science Institute | 1,867 months | 0 unexplained differences |
| Public holidays (JP) | `holidays` 0.101 | 2,408 dates | 0 differences |
| Sexagenary day | KASI, and an independent published implementation | 4 anchors | agree; a 60-day residue is fully determined by them |
| Selection days | Published 2026 almanac values | 4 claims | all reproduce |

Full detail, including why each check was chosen and what the remaining differences
mean, is in [`docs/verification.md`](docs/verification.md).

### Known limits

- **Range.** 1900-01-01 to 2100-12-31. Outside it the code raises rather than
  guessing.
- **2033–2034.** Between 2033-07-26 and 2034-03-20 the Tenpō-reki rules do not
  determine the intercalary month uniquely. This ships the leap-11th-month option,
  which the Japanese Calendar Culture Association, KASI, the Hong Kong Observatory
  and Koyomi no Page all agree on, and flags the affected months in the data.
- **Far-future day boundaries.** ΔT — the difference between terrestrial and
  universal time — cannot be predicted, so instants late in the range drift by up to
  ~2 minutes against other implementations. Two new moons (2074-08 and 2097-01) land
  close enough to midnight that the date differs, which moves a whole month of
  rokuyō. All 64 events within ±3 minutes of the day boundary are pinned by tests.
- **Two traditions for 一粒万倍日.** Table Ⅰ (the common modern one) is the default;
  Table Ⅱ, from *Eitai Ōzassho Manreki Taisei*, is selectable.

## Development

```bash
PYTHONPATH=src python3 -m pytest tests -q          # 403 tests
PYTHONPATH=src python3 tests/preview.py --update   # regenerate goldens + preview
```

Regenerating the astronomical tables needs `ephem`, and the holiday tables need
`holidays`. Neither is imported at render time.

## License

MIT — see [`LICENSE`](LICENSE).

The optional embedded font is a subset of Noto Sans JP under the SIL Open Font
License; details in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md). No
third-party dataset is redistributed — the shipped tables are values this project
computed.
