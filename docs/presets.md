# Presets

A preset is a named bundle of starting values with up to three sections plus
optional display metadata:

- **`[conversion]`** — tracing options, validated against `ConversionConfig`
- **`[preprocess]`** — Pillow preprocessing options, validated against
  `PreprocessConfig`
- **`[postprocess]`** — SVG post-trace options, validated against
  `PostprocessConfig` (currently just `invert`, the negative look)
- **metadata** — `description`, `recommended_for`, `notes`

A preset sets **initial values only** — any config-file value or CLI option
always overrides it, for every section (see
[configuration.md](configuration.md) for the full precedence chain).

```
engine defaults  <  preset  <  user config  <  --config file  <  CLI options
```

## Built-in presets

`raster2svg` ships fourteen built-in presets (PRD 16.1 requires `bw`, `photo`,
and `poster`; the rest extend the set):

| Preset | Description | Best for |
| --- | --- | --- |
| `bw` | High-contrast black-and-white graphics, line work, and technical drawings. | logos, icons, line art, black & white scans |
| `photo` | Photorealistic images as smooth, layered color vector art. | photos, portraits, landscapes |
| `poster` | Bold, flat, few-color poster and screen-print look. | posters, flyers, screen prints |
| `flat-illustration` | Clean flat-design illustration: smooth shapes, limited palette. | flat illustrations, vector art, infographics |
| `clip-art` | Classic clip art: bold colors, smooth curves, minimal speckle. | clip art, scanned drawings, cartoons |
| `clip-art-soft` | Gentler clip-art tracing: keeps more color and detail, lighter cleanup. | detailed clip art, shaded illustrations |
| `clip-art-strong` | Aggressive clip-art cleanup: very few colors, thick clean shapes. | noisy scans, low-res clip art, stamps |
| `comic` | Comic and manga style: crisp shapes, flat cel color, high contrast. | comics, manga, cel shading |
| `line-art` | Ink line drawings: adaptive thresholding keeps strokes under uneven light. | line art, ink drawings, sketches |
| `line-art-inverted` | `line-art` rendered as a negative: light strokes on a dark background. | glowing line art, dark-mode icons, night-sky sketches |
| `silhouette` | Solid single-color silhouettes: the image becomes one flat shape. | silhouettes, stencils, shadow shapes |
| `silhouette-inverted` | `silhouette` rendered as a negative: a light shape on a dark background. | glowing silhouettes, dark-mode badges, light-on-dark stencils |
| `logo-cleanup` | Logos and badges: precise curves, clean edges, small faithful palette. | logos, badges, emblems |
| `pixel-art` | Pixel art and retro sprites: hard edges, no smoothing, one shape per block. | pixel art, retro games, sprites |

Every preset bundles a `[preprocess]` section (e.g. `photo` applies `denoise`,
`poster` applies `denoise` + `posterize` + `autocontrast` + `pre_max_colors`)
plus `[conversion]` values (clustering, layering, curve mode, precision,
speckle filtering, simplification, optimization). The two inverted presets
additionally set `[postprocess]` `invert = true` (see
[configuration.md](configuration.md)). Inspect any preset with:

```powershell
raster2svg preset show clip-art
```

They are application-level bundles over the canonical settings: with the
installed vtracer 0.6.x there is no native preset API, and the 1.0 CLI build
does not expose one either, so presets map onto the shared option surface.
Preset conversion values use 1.0-era options (`simplify`, `optimize`,
`max_colors`, `binary_threshold`, `adaptive`, …); on a machine where only the
0.6.x engine can honour a given combination the conversion fails with a clear
"unsupported feature" error listing exactly which options.

Use one with:

```powershell
raster2svg convert photo.jpg --preset photo
raster2svg convert photo.jpg --preset bw --mode polygon   # CLI still overrides
```

## Custom presets

Save a config file as a reusable preset (PRD 16.4):

```powershell
# From an existing config file (its [conversion] and [preprocess] sections)
raster2svg preset save my-logo --from-config raster2svg.toml
raster2svg preset save my-clip --from-config clip.toml --base clip-art
```

`--base` names the preset to derive from; without it the config file's own
`preset` key (if any) is used.

Custom presets are stored as TOML files in the application data directory
(next to the user-level config file), one file per preset, named
`<preset-name>.toml`:

| OS | Directory |
| --- | --- |
| Windows | `%APPDATA%\raster2svg` |
| Linux | `~/.local/share/raster2svg` |
| macOS | `~/Library/Application Support/raster2svg` |

The directory honors `RASTER2SVG_DATA_DIR`.

Both file shapes are accepted:

```toml
# my-clip.toml — structured (preferred)
description = "My clip art"
base = "clip-art"

[conversion]
mode = "spline"
filter_speckle = 3

[preprocess]
denoise = true
posterize = 5

# Optional — e.g. a negative (light-on-dark) output:
[postprocess]
invert = true
```

```toml
# legacy flat — old files keep working (top-level keys are conversion values)
base = "photo"
mode = "polygon"
```

Rules for a custom preset:

- Name: lowercase letters, digits, and dashes (e.g. `my-logo`).
- Must not shadow a built-in name (`bw`, `photo`, `poster`, …).
- May contain `[conversion]`, `[preprocess]`, and/or `[postprocess]`
  settings, plus the optional `base` key and metadata (`description`,
  `recommended_for`, `notes`). Mixing sectioned and flat values in one file
  is rejected.
- Values are validated against the canonical models before saving, so a saved
  preset can never be silently ignored (PRD 21).

### Inheriting with `base`

A custom preset may declare a `base` key to inherit from another preset
(built-in or custom). The base is resolved recursively, per section; on a
conflict the derived preset's value wins. Metadata (description,
recommended_for, notes) comes from the first preset in the chain that has it.
Cycles and chains deeper than 8 levels are rejected.

### Managing presets

```powershell
# List all presets with their description and recommended inputs
raster2svg preset list

# Show one preset: metadata plus its resolved conversion/preprocess values
raster2svg preset show my-logo

# Convert one image with every preset (or a subset) and compare the results
raster2svg preset compare photo.png
raster2svg preset compare photo.png --presets clip-art,poster,bw --output-dir out
```

`preset compare` writes one SVG per preset plus a `report.json` recording
status, duration, output size, and path count, so values can be tuned quickly.

### Tuning presets

A synthetic test corpus makes tuning reproducible:

```powershell
python scripts/make_corpus.py --out corpus
raster2svg preset compare corpus\clip-art.png
```

## Notes

- Presets never limit the user: every field they set is overridable.
- A preset selects *which* engine settings are pre-filled; it does not change
  validation or the precedence rules.
- In the web UI, selecting a preset shows its description and recommended
  inputs, and the preset's `[preprocess]` and `[postprocess]` values merge
  under any values you set explicitly (e.g. the inverted presets come in with
  invert already on).
