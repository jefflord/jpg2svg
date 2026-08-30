# Command-line interface

`raster2svg` exposes a set of named commands plus a shorthand form. Every
command accepts `--help` / `-h`, and a `help` subcommand that prints the same
text in either position.

## Quick start

```powershell
# Shorthand (equivalent to `convert`)
raster2svg photo.jpg photo.svg

# Named form
raster2svg convert photo.jpg --preset photo --mode spline --overwrite

# See the resolved settings without converting
raster2svg convert photo.jpg --show-config

# Inspect an image without converting
raster2svg inspect photo.jpg

# Batch a folder
raster2svg batch .\images --output-dir .\svg --recursive

# Engine info
raster2svg version
raster2svg engine capabilities
```

## Global options

Available on every command (before the subcommand), PRD section 18:

| Flag | Effect |
| --- | --- |
| `--verbose` | Debug logging (default level: INFO) |
| `--quiet` | Warnings and errors only |
| `--log-level LEVEL` | `debug`, `info`, `warning`, or `error`; overrides `--verbose`/`--quiet` |
| `--log-file PATH` | Also write log messages to a file |

`--verbose` and `--quiet` are mutually exclusive (exit code **2**).

## Commands

| Command | Purpose |
| --- | --- |
| `convert` | Convert one raster image to SVG. |
| `batch` | Convert a file or directory of images to SVG. |
| `inspect` | Report an image's properties without converting. |
| `config` | `show` / `init` configuration files. |
| `preset` | `list` / `show` / `save` presets. |
| `engine` | `capabilities` — what the installed VTracer supports. |
| `web` | Serve the live web interface for real-time conversion and preview. |
| `version` | Tool and tracing-engine versions. |
| `help` | Print help for a command or subcommand. |

### `convert`

```
raster2svg convert [OPTIONS] [INPUT] [OUTPUT]
```

Input and output are accepted positionally or via `--input` / `--output`
(named flag wins when both are given). The main conversion options are the
`[conversion]` settings from [configuration.md](configuration.md#conversion-settings)
as flags (e.g. `--clustering`, `--mode`, `--layer-difference`, `--simplify`),
the `[preprocess]` settings (e.g. `--resize`, `--grayscale`, `--denoise`), and
the `[output]` settings (`--overwrite`, `--validate-svg`, `--no-mkdir`).

Useful flags:

| Flag | Effect |
| --- | --- |
| `--preset NAME` | Starting preset (`bw`, `photo`, `poster`, or a saved custom preset). |
| `--config PATH` | Config file (`.toml`/`.json`) for conversion + output settings. |
| `--show-config` | Print the resolved configuration and exit (no conversion). |
| `--dry-run` | Validate everything but do not write output. |
| `--report PATH` | Write a JSON conversion report to this path. |
| `--overwrite` / `--no-overwrite` | Replace an existing output file (default: refuse). |

### `batch`

```
raster2svg batch [OPTIONS] INPUT_DIR
```

| Flag | Effect |
| --- | --- |
| `--output-dir PATH` | Directory for `.svg` output (default: the input directory). |
| `--recursive` / `--no-recursive` | Recurse into subdirectories, preserving structure (default: no). |
| `--include GLOB` | Only process matching files (repeatable). |
| `--exclude GLOB` | Skip matching files (repeatable). |
| `--jobs N` \| `auto` | Worker count (default: conservative). |
| `--fail-fast` | Stop the batch at the first failed file. |
| `--jsonl` | Emit one JSON object per result on stdout. |
| `--report PATH` | Write a JSON batch report to this path. |

All `convert` conversion/preprocess/output flags apply to every file in the
batch. Per-file failures are captured, not raised: the batch continues (unless
`--fail-fast` is set) and records each result. The command exits with code
**1** if any file failed or was skipped, and **0** if all succeeded.

### `inspect`

```
raster2svg inspect [OPTIONS] [INPUT]
```

Decodes the image and reports format, mode, dimensions, pixel count, alpha,
EXIF orientation, size, and an estimated memory footprint. `--format json`
emits machine-readable output.

### `config`

| Subcommand | Effect |
| --- | --- |
| `config show` | Print the fully resolved configuration (`--format text` \| `json`). |
| `config init` | Write a commented TOML template (`--output`, `--preset`, `--force`). |

### `preset`

| Subcommand | Effect |
| --- | --- |
| `preset list` | List built-in and custom presets with their resolved values. |
| `preset show NAME` | Show all resolved values of one preset (base chain applied). |
| `preset save NAME --from-config FILE` | Save a custom preset from an existing config file. |

### `engine`

| Subcommand | Effect |
| --- | --- |
| `engine capabilities` | Show the engine name/version and its supported parameters. |

### `web`

```
raster2svg web [OPTIONS]
```

Starts a local HTTP server that hosts a single-page app for real-time
conversion: upload an image once, tweak options, preview the rendered SVG live,
and download it. It reuses the same engine, presets, and preprocessing as
`convert`, so the output is identical. The server is stdlib `http.server` and
adds no new runtime dependencies.

| Flag | Effect |
| --- | --- |
| `--host HOST` | Interface to bind (default `127.0.0.1`, loopback only). Use `0.0.0.0` for other hosts. |
| `--port PORT` | Port to listen on (default `9921`). |
| `--open` | Open the interface in the default browser on startup. |

On success the command prints the URL to open and blocks until `Ctrl+C`; a
bind failure (e.g. the port is already in use) exits with code **2** and an
actionable message. See [`raster2svg_web_prd.md`](../raster2svg_web_prd.md) for
the full specification, including the JSON API (`/api/info`, `/api/upload`,
`/api/convert`) and session limits.

### `version`

Prints the tool version and the installed tracing-engine version.

## Help

`--help` and the `help` subcommand are equivalent:

```powershell
raster2svg help
raster2svg help convert
raster2svg help config show
raster2svg convert help
raster2svg config help show
```

## Exit codes

Exit codes follow PRD section 12.6:

| Code | Meaning |
| --- | --- |
| `0` | Success. |
| `1` | One or more conversions failed (batch). |
| `2` | Invalid CLI option or configuration (including unsupported engine features). |
| `3` | Input/output filesystem error. |
| `4` | Dependency / runtime / tracing-engine error. |

Errors are printed to stderr as `ERROR: <message>` followed by an optional
`Hint:` line, then the process exits with the code above.
