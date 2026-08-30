# Configuration

`raster2svg` settings come from five layers, applied in this order (low to
high precedence):

1. **Engine defaults** — whatever the installed VTracer version uses.
2. **Preset** — `bw`, `photo`, `poster`, or a saved custom preset.
3. **User-level config file** — `config.toml` (or `config.json`) in the
   application data directory. Applies to every invocation on this machine.
4. **`--config` file** — a project config file passed explicitly.
5. **CLI options** — individual flags on the command line.

A higher layer only overrides the keys it actually sets. Keys it does not set
fall through to the layer below. So a preset, a user file, and a project file
can all coexist without clobbering each other.

```
engine defaults  <  preset  <  user config  <  --config file  <  CLI options
```

## Config file format

Config files are TOML (`.toml`) or JSON (`.json`), detected by extension. They
use three optional sections:

```toml
[conversion]
# tracing settings (clustering, mode, ...)

[preprocess]
# image preprocessing (resize, grayscale, ...)

[output]
# output behavior (overwrite, validate_svg, ...)
```

A config file may also be written "flat", where top-level keys are conversion
settings directly (equivalent to putting them under `[conversion]`). Sectioned
form is recommended.

## Finding the user-level config file

The user-level config file lives in the platform application data directory,
next to where custom presets are stored:

| OS | Directory |
| --- | --- |
| Windows | `%APPDATA%\raster2svg\` |
| Linux | `~/.local/share/raster2svg/` |
| macOS | `~/Library/Application Support/raster2svg/` |

The directory honors the `RASTER2SVG_DATA_DIR` environment variable, which lets
you relocate it (and is what the test suite uses to stay hermetic).

To inspect or create your user config:

```powershell
# Show where it resolves to and what it currently resolves to
raster2svg config show

# Generate a commented template to a path of your choosing, then move it
raster2svg config init --output $env:APPDATA\raster2svg\config.toml
```

## Conversion settings

All fields are optional. `None` means "use the engine default" (PRD rule 6),
so the same file stays valid across VTracer versions.

| Key | Type | Range / values | Notes |
| --- | --- | --- | --- |
| `preset` | str | `bw` \| `photo` \| `poster` \| custom | Starting preset (also settable via `--preset`). |
| `clustering` | str | `color-cluster` \| `bw` \| `watershed` | Region clustering strategy. |
| `hierarchical` | str | `stacked` \| `cutout` | Layering mode. |
| `mode` | str | `pixel` \| `polygon` \| `spline` | Curve-fitting mode. |
| `filter_speckle` | int | 1-100 | Speckle filter size. |
| `color_precision` | int | 1-8 | Bits per RGB channel. |
| `layer_difference` | int | 1-255 | Color difference between layers (CLI `--gradient-step`). |
| `corner_threshold` | float | 0-180 | Corner angle in degrees. |
| `length_threshold` | float | 3.5-10 | Segment length (CLI `--segment-length`). |
| `max_iterations` | int | 1-100 | Curve-fitting iterations. |
| `splice_threshold` | float | 0-180 | Splice angle in degrees. |
| `path_precision` | int | 0-8 | Decimal places in path data. |
| `simplify` | float | >0 | Curve simplification tolerance (engine-dependent). |
| `palette` | list[str] | `#rgb` / `#rrggbb` | Hex colors (engine-dependent). |
| `palette_file` | path | one hex per line | Alternative to `palette` (engine-dependent). |
| `max_colors` | int | 1-65536 | Quantize to N colors (engine-dependent). |
| `optimize` | int | 0-2 | Optimization level (engine-dependent). |
| `binary_threshold` | int | 0-255 | Binary threshold (engine-dependent). |
| `adaptive` | bool | — | Adaptive thresholding; implies `clustering = "bw"` (engine-dependent). |
| `adaptive_window` | int | >=3 | Adaptive window size (engine-dependent). |
| `adaptive_t` | int | 0-255 | Adaptive threshold constant (engine-dependent). |
| `watershed_detail` | int | 0-255 | Use with `clustering = "watershed"`. |

`palette` and `palette_file` are mutually exclusive. `adaptive` conflicts with
an explicit `clustering` that is not `bw`.

> **Note:** `color_precision` (bits per RGB channel) and `max_colors` (a hard
> cap on the total number of distinct colors) are *different* settings. On the
> installed VTracer 0.6.15, `color_precision` is supported but `max_colors` is
> not — requesting `max_colors` raises a clear `UnsupportedFeatureError`. See
> the README "Engine feature support" section.

## Preprocessing settings

Applied before tracing. Identity / omitted values leave that aspect untouched.

| Key | Type | Default | Notes |
| --- | --- | --- | --- |
| `auto_orient` | bool | `true` | Apply EXIF orientation before tracing. |
| `resize` | str | — | Fit within `WxH`, aspect preserved (e.g. `1920x1080`). |
| `max_width` | int | — | Shrink so width <= N (aspect preserved). |
| `max_height` | int | — | Shrink so height <= N (aspect preserved). |
| `scale` | float | — | Scale both dimensions by a factor (e.g. `0.5`). |
| `grayscale` | bool | `false` | Convert to grayscale. |
| `denoise` | bool | `false` | Conservative median speckle removal. |
| `contrast` | float | — | Contrast factor, 1.0 = unchanged, range 0-10. |
| `brightness` | float | — | Brightness factor, 1.0 = unchanged, range 0-10. |
| `sharpen` | bool | `false` | Conservative unsharp mask. |

## Output settings

| Key | Type | Default | Notes |
| --- | --- | --- | --- |
| `overwrite` | bool | `false` | Replace an existing output file (else refuse). |
| `validate_svg` | bool | `true` | Validate generated SVG as XML. |
| `create_directories` | bool | `true` | Create the output directory if missing. |

## Generating and inspecting config

```powershell
# Write a commented default template (TOML)
raster2svg config init
raster2svg config init --preset photo --output raster2svg.toml
raster2svg config init --output raster2svg.toml --force

# Print the fully resolved configuration (all layers applied)
raster2svg config show
raster2svg config show --preset photo
raster2svg config show --config raster2svg.toml --format json
```

`--show-config` on `convert` / `batch` prints the same resolved table and exits
without converting.

## Validation and errors

Config is validated with Pydantic (`extra = "forbid"`), so typos and unknown
keys fail fast with an actionable message and exit code **2** rather than being
silently ignored:

```powershell
raster2svg convert photo.jpg --config bad.toml
# ERROR: Invalid configuration value(s).
# clusterng: Extra inputs are not permitted
```

Settings the installed VTracer does not expose are still accepted by the parser
but raise a clear "unsupported" error (exit code **2**) instead of being
silently dropped.

## Sample configs

See the [`examples/`](../examples/) directory for ready-to-copy configs for the
common presets, plus a user-level config example.
