# Presets

A preset is a named bundle of starting values for the tracing engine. It sets
**initial values only** — any config-file value or CLI option always overrides
it (see [configuration.md](configuration.md) for the full precedence chain).

```
engine defaults  <  preset  <  user config  <  --config file  <  CLI options
```

## Built-in presets

`raster2svg` ships three built-in presets (PRD 16.1):

| Preset | clustering | hierarchical | mode | Other starting values |
| --- | --- | --- | --- | --- |
| `bw` | `bw` | `stacked` | `spline` | `filter_speckle = 2`, `path_precision = 3` |
| `photo` | `color-cluster` | `stacked` | `spline` | `color_precision = 6`, `layer_difference = 12`, `path_precision = 3` |
| `poster` | `color-cluster` | `cutout` | `spline` | `color_precision = 4`, `layer_difference = 24`, `path_precision = 3` |

They are deliberately close to the VTracer presets of the same name. With the
installed vtracer 0.6.x there is no native preset API, so these are
application-level bundles over the canonical settings.

Use one with:

```powershell
raster2svg convert photo.jpg --preset photo
raster2svg convert photo.jpg --preset bw --mode polygon   # CLI still overrides
```

## Custom presets

Save a config file as a reusable preset (PRD 16.4):

```powershell
# From an existing config file (the [conversion] section is used)
raster2svg preset save my-logo --from-config raster2svg.toml
```

Custom presets are stored as TOML files in the application data directory
(next to the user-level config file), one file per preset, named
`<preset-name>.toml`:

| OS | Directory |
| --- | --- |
| Windows | `%APPDATA%\raster2svg` |
| Linux | `~/.local/share/raster2svg` |
| macOS | `~/Library/Application Support/raster2svg` |

The directory honors `RASTER2SVG_DATA_DIR`.

Rules for a custom preset:

- Name: lowercase letters, digits, and dashes (e.g. `my-logo`).
- Must not shadow a built-in name (`bw`, `photo`, `poster`).
- May only contain conversion settings (plus the optional `base` key).
- Values are validated against the canonical model before saving, so a saved
  preset can never be silently ignored (PRD 21).

### Inheriting with `base`

A custom preset may declare a `base` key to inherit from another preset
(built-in or custom). The base is resolved recursively; on a conflict the
derived preset's value wins. Cycles and chains deeper than 8 levels are
rejected.

```toml
# my-logo.toml
base = "photo"
clustering = "bw"
filter_speckle = 3
```

### Managing presets

```powershell
# List built-in and custom presets with their resolved values
raster2svg preset list

# Show all resolved values of one preset (base chain applied)
raster2svg preset show my-logo
```

## Notes

- Presets never limit the user: every field they set is overridable.
- A preset selects *which* engine settings are pre-filled; it does not change
  validation or the precedence rules.
