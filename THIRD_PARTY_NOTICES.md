# Third-party notices

## Noto Sans JP (embedded font subset)

`src/almanac_calendar/assets/fonts/noto-sans-jp.ttf` is a subset of Noto Sans JP,
licensed under the **SIL Open Font License 1.1**. The subset is generated at build
time from the upstream font and contains only the glyphs this project draws.

The same notice is embedded as a comment inside every generated SVG that uses the
font, so the licence travels with the artefact.

- Upstream: https://fonts.google.com/noto/specimen/Noto+Sans+JP
- Licence: https://scripts.sil.org/OFL
- The font's own name table carries `(c) 2014-2021 Adobe (http://www.adobe.com/),
  with Reserved Font Name 'Source'` — Noto Sans JP derives from Source Han Sans.
  This project does not use "Source" in any font name it produces.

Embedding the font is optional. With no font configured, the SVG falls back to the
viewer's system fonts and no third-party font is redistributed.

## Calendar data

Astronomical instants (new/quarter/full moons, the 24 solar terms) are computed at
build time with [`ephem`](https://pypi.org/project/ephem/) (MIT) and shipped as CSV.
Public holidays outside Japan are generated from
[`holidays`](https://github.com/vacanza/holidays) (MIT).

Neither library is imported at render time, and no third-party dataset is
redistributed — only values this project computed.

Results were cross-checked against the National Astronomical Observatory of Japan,
the Korea Astronomy and Space Science Institute, and published Japanese almanac
values. See `docs/verification.md`.
