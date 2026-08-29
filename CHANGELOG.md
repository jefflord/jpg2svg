# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/jefflord/jpg2svg/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/jefflord/jpg2svg/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/jefflord/jpg2svg/releases/tag/v0.1.0
