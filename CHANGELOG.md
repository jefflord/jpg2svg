# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Presets: fourteen built-in presets — `bw`, `photo`, `poster`,
  `flat-illustration`, `clip-art`, `clip-art-soft`, `clip-art-strong`, `comic`,
  `line-art`, `line-art-inverted`, `silhouette`, `silhouette-inverted`,
  `logo-cleanup`, `pixel-art`. Each bundles `[conversion]`, `[preprocess]`,
  and (for the inverted pair) `[postprocess]` starting values plus
  `description` / `recommended_for` metadata. `preset list` shows description
  and recommended inputs; `preset show NAME` prints metadata and the fully
  resolved values of every section.
- `preset compare IMAGE`: convert one image with every preset (or a
  `--presets` subset) and write one SVG plus a `report.json` (status, duration,
  output size, path count) per preset, for quick visual tuning.
- New preprocessing options (Pillow, no new dependencies): `--blur` /
  `--no-blur` (gentle Gaussian blur), `--posterize N` (1-8 bits per channel),
  `--autocontrast` / `--no-autocontrast`.
- New post-processing stage (no new dependencies): `--invert` / `--no-invert`
  renders a negative (light-on-dark) SVG after tracing — hex fills are
  inverted, unfilled shapes are forced white, and a dark background rect is
  inserted. Settable as `invert` under a `[postprocess]` config section; the
  `postprocess` / `postprocess_applied` fields are reported in the conversion
  report.
- Negative presets: `line-art-inverted` and `silhouette-inverted`, each the
  base preset plus `invert = true`, so they trace identically and only differ
  in the final post-processing step.
- Custom presets may now be saved in structured form (`[conversion]` +
  `[preprocess]` + optional `base` and metadata) from a config file; the
  legacy flat shape (top-level conversion values) still loads and saves.
- Web UI: selecting a preset shows its description and recommended inputs;
  the preset's `[preprocess]` and `[postprocess]` values merge under any
  explicitly set preprocessing / postprocessing options.
- `scripts/make_corpus.py`: deterministic Pillow-generated test images (one per
  preset family) for reproducible preset tuning.
- Web UI: proper preview zoom & pan — scroll anywhere to zoom at the cursor,
  drag to pan, double-click to zoom in, `+` / `-` / `0` / arrow keys when the
  preview is focused, and zoom buttons anchored at the view center (zoom range
  10%–800% of fit).
- Web UI: a thumbnail of the uploaded image is shown in the controls panel so
  you can see the source raster next to the options.
- `raster2svg web --sample PATH`: expose an existing SVG file at
  `GET /api/sample` (reported as `sample` in `/api/info`), enabling a **Sample**
  button in the UI to load it into the preview for testing without converting.

## [0.4.0] - 2026-08-29

### Added

- `raster2svg web`: a local, browser-based live converter (see
  `raster2svg_web_prd.md`). `raster2svg web` starts a loopback HTTP server
  (default `http://localhost:9921/`) hosting a single-page app to upload an
  image once, tweak options, preview the SVG live, and download it.
  - `--host` / `--port` select the bind target (defaults `127.0.0.1:9921`).
  - `--open` opens the browser on startup.
  - No new runtime dependencies: stdlib `http.server` + a self-contained HTML
    page. Reuses the same engine, presets, and preprocessing as `convert`.
  - In-memory upload sessions (bounded in count and bytes, 30-minute TTL).
- `--pre-max-colors N` (1-256): cap the raster to at most N colors in the
  preprocessor (Pillow, no dithering) before tracing. Distinct from the
  engine-side `--max-colors` (VTracer-native, needs VTracer 1.0). Also settable
  as `pre_max_colors` under `[preprocess]`.

### Changed

- `convert`/`batch` option help now clearly marks engine-dependent advanced
  options (`--simplify`, `--palette`, `--palette-file`, `--max-colors`,
  `--optimize`, `--binary-threshold`, `--adaptive`, `--adaptive-window`,
  `--adaptive-t`, `--watershed-detail`) with `[UNAVAILABLE - needs VTracer 1.0]`
  when the installed engine doesn't support them.
- `raster2svg engine capabilities` now lists the advanced options that are and
  are not available on the installed engine.
- The `UnsupportedFeatureError` hint now points to VTracer 1.0.

## [0.3.0] - 2026-08-29

### Added

- `help` subcommand in both positions, printing the same text as the matching
  `--help`:
  - `raster2svg help [COMMAND [SUBCOMMAND]]` (e.g. `raster2svg help config show`)
  - `raster2svg COMMAND help` (e.g. `raster2svg convert help`,
    `raster2svg config help show`)
- `inspect` command: decode an image and report format, mode, dimensions,
  pixel count, alpha channel, EXIF orientation, on-disk size, and estimated
  decode memory, without converting (PRD 15.4).
  - `raster2svg inspect INPUT` — human-readable report
  - `raster2svg inspect --format json INPUT` — machine-readable report
  - `inspect_image()` / `ImageInspection` exported from the library API
- Global logging options on every command (PRD 18):
  - `--verbose` — debug logging
  - `--quiet` — warnings and errors only
  - `--log-level debug|info|warning|error` — explicit level; overrides `--verbose`/`--quiet`
  - `--log-file PATH` — also write log messages to a file
- `output_sha256` in conversion reports (JSON report and JSONL): the SHA-256
  fingerprint of the written SVG file, matching the bytes on disk — useful for
  integrity checks, CI determinism, and cache keys (PRD 17.1).
- `--verbose`/`--quiet` conflict and invalid levels are clean errors (exit code 2).
- Shorthand `raster2svg INPUT OUTPUT` accepts leading global options
  (e.g. `raster2svg --verbose photo.jpg out.svg`).
- Debug pipeline tracing (input, preprocessing, trace, write) visible with
  `--verbose`; batch per-file failures are logged at WARNING level.
- User-level configuration file (PRD 8): a machine-wide `config.toml` /
  `config.json` in the platform data directory, applied below `--config` and
  CLI options. New five-layer precedence:
  `engine defaults < preset < user config < --config file < CLI options`.
  - Directory: `%APPDATA%\raster2svg\` (Windows), `~/.local/share/raster2svg/`
    (Linux), `~/Library/Application Support/raster2svg/` (macOS);
    overridable with `RASTER2SVG_DATA_DIR`.
  - `config show` / `convert --show-config` now reflect the user file.
- User-facing documentation in `docs/` (PRD 22): `configuration.md`, `cli.md`,
  `presets.md`, `architecture.md`.
- Sample configs in `examples/`: `photo.toml`, `bw.toml`, `poster.toml`, and a
  user-level `user-config.toml`.
- Test coverage (PRD 25): golden (exact), structural, and semantic SVG output
  tests with committed golden files and a regeneration script, plus a
  performance tracking suite (wall time, peak Python-heap memory, output size)
  at 512x512, 1920x1080, and 4000x3000.

## [0.2.0] - 2026-08-29

### Added

- Image preprocessing pipeline (Pillow) run before tracing, applied to both
  `convert` and `batch`:
  - `--auto-orient` / `--no-auto-orient` — apply EXIF orientation (on by default)
  - `--resize WxH` — fit within a box, aspect ratio preserved (up- and down-scaling)
  - `--max-width N` / `--max-height N` — shrink only, aspect ratio preserved
  - `--scale F` — scale both dimensions by factor
  - `--grayscale` / `--color` — convert to grayscale
  - `--denoise` / `--no-denoise` — conservative median speckle removal
  - `--contrast F` / `--brightness F` — tone adjustment (1.0 = unchanged, alpha preserved)
  - `--sharpen` / `--no-sharpen` — conservative unsharp mask
- `[preprocess]` section in TOML/JSON config files; CLI flags override file values.
- `config init` template and `config show` include the preprocess section;
  `convert --show-config` prints the resolved preprocessing settings.
- Conversion reports include the resolved `preprocess` settings and the
  `preprocess_applied` operation list; `--dry-run` reports the operations
  that would be applied without writing output.
- Default runs never re-encode the input image (no-op configs pass bytes through).

## [0.1.0] - 2026-08-29

### Added

- Initial development version.
- JPG/JPEG, PNG, and other raster formats to SVG conversion via the VTracer engine.
- `convert` (single file) and `batch` (directory/glob, serial or parallel) commands.
- Presets (`bw`, `photo`, `poster`) with `preset save`, `preset list`, `preset show`.
- TOML/JSON config files with CLI > file > default precedence.
- Conversion reports (JSON), dry runs, overwrite protection, and atomic writes.
- `engine capabilities` introspection of the installed VTracer version.

[Unreleased]: https://github.com/jefflord/jpg2svg/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/jefflord/jpg2svg/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/jefflord/jpg2svg/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/jefflord/jpg2svg/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jefflord/jpg2svg/releases/tag/v0.1.0
