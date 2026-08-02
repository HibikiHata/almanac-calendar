# Third-party notices

## Noto Sans JP (embedded font subset)

`src/almanac_calendar/assets/fonts/noto-sans-jp.ttf` is a **subset of Noto Sans JP**,
licensed under the **SIL Open Font License 1.1**. The full licence text is bundled at
[`licenses/OFL.txt`](licenses/OFL.txt).

**The MIT licence of this project does not apply to that file.** Per OFL clause 5 the
font — modified or unmodified, in part or in whole — is distributed entirely under the
OFL and under no other licence. Everything else in this repository is MIT.

The subset is generated at build time from the upstream font and keeps only the glyphs
this project draws.

- Upstream: https://fonts.google.com/noto/specimen/Noto+Sans+JP
- Licence: https://openfontlicense.org

### How the OFL conditions are met

| Clause | Requirement | How |
|---|---|---|
| 1 | The font may not be sold on its own | It is not sold, and ships only as part of this software |
| 2 | Every copy carries the copyright notice **and this licence** | `licenses/OFL.txt` holds the full text. The notice also survives inside the font's own `name` table (IDs 0, 13, 14), which the clause explicitly permits as a machine-readable metadata field, and it is written as a comment into every SVG that embeds the font — so it travels with the artefact |
| 3 | A modified version may not use a Reserved Font Name | The declared Reserved Font Name is **`Source`**: Noto Sans JP derives from Source Han Sans, and the font's copyright string reads `(c) 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'`. The subset carries no family name of its own — the subsetter keeps only name IDs 0/13/14 — and this project refers to it as `noto-sans-jp`. **No name this project produces contains "Source"** |
| 4 | The copyright holders' names may not be used to promote | They are not |
| 5 | The font must be distributed entirely under the OFL | Stated above; the font sits in its own path with the licence bundled alongside |

### Embedding is optional

With no `font` configured — the default — nothing is embedded and no third-party font
is redistributed. The SVG then falls back to the viewer's system fonts, which shows
tofu where no CJK font is installed. Embedding trades that risk for the obligations
above.

## Calendar data

Astronomical instants (new/quarter/full moons, the 24 solar terms) are computed at
build time with [`ephem`](https://pypi.org/project/ephem/) (MIT) and shipped as CSV.
Public holidays outside Japan are generated from
[`holidays`](https://github.com/vacanza/holidays) (MIT).

**Neither library is imported at render time, and no third-party dataset is
redistributed** — the shipped tables are values this project computed.

Results were cross-checked against the National Astronomical Observatory of Japan, the
Korea Astronomy and Space Science Institute, and published Japanese almanac values.
See [`docs/verification.md`](docs/verification.md).
