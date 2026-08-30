# Product Requirements Document (PRD)

# Raster-to-SVG Command-Line Converter

**Working name:** `raster2svg`\
**Version:** 1.0\
**Target platform:** Windows first; cross-platform architecture
preferred\
**Primary implementation:** Python 3.12+\
**Primary tracing engine:** VTracer Python native extension\
**Status:** Build specification for implementation by a coding agent

------------------------------------------------------------------------

## 1. Executive Summary

Build a professional command-line application that converts raster
images, initially JPEG/JPG and PNG, into SVG vector graphics.

The application shall be designed as a reliable automation and
batch-processing tool rather than a GUI-first application. A future
PySide6 desktop GUI may reuse the same core library and configuration
model, but the command-line interface is the primary product for this
version.

The tool must:

-   Convert JPG/JPEG to SVG.
-   Also support PNG and other formats supported by the underlying image
    decoder where practical.
-   Expose as many VTracer features as are available through the
    installed Python API.
-   Support configuration files.
-   Support command-line arguments.
-   Support presets.
-   Support deterministic precedence between defaults, presets,
    configuration files, environment variables, and command-line
    arguments.
-   Support single-file conversion and batch conversion.
-   Validate configuration before processing.
-   Provide machine-readable output for automation.
-   Produce useful errors and diagnostics.
-   Be architected so a future PySide6 GUI can directly use the same
    conversion/configuration core.

The implementation should favor a clean Python library plus a thin CLI
wrapper.

------------------------------------------------------------------------

# 2. Product Goals

## 2.1 Primary Goals

1.  Create a high-quality JPG-to-SVG conversion tool powered by VTracer.
2.  Expose nearly all practical tracing features offered by the
    installed VTracer Python package.
3.  Make complex conversion settings reproducible through configuration
    files.
4.  Make the tool scriptable from PowerShell, CMD, Python, CI/CD
    systems, and other automation tools.
5.  Support batch processing without requiring a GUI.
6.  Provide a stable configuration schema that can later be consumed by
    a PySide6 application.
7.  Avoid reimplementing raster-to-vector algorithms already provided by
    VTracer.

## 2.2 Secondary Goals

-   Optional image preprocessing.
-   Preset management.
-   SVG output optimization.
-   Detailed logging and conversion reports.
-   Dry-run/config inspection modes.
-   Parallel batch processing where safe.
-   Future plugin architecture for alternate tracing engines.

## 2.3 Non-Goals for Version 1

The following should not block the first production release:

-   Writing a custom raster-to-vector engine.
-   Building an advanced desktop GUI.
-   Cloud processing.
-   User accounts.
-   Collaborative editing.
-   Full SVG editing.
-   Adobe Illustrator compatibility features beyond valid SVG output.

------------------------------------------------------------------------

# 3. Target Users

## 3.1 Command-Line Power User

A user who wants to execute:

``` text
raster2svg input.jpg output.svg
```

and optionally tune tracing settings.

## 3.2 Automation / Batch User

A developer or production pipeline that wants:

``` text
raster2svg convert ./input --output-dir ./svg --config production.toml
```

## 3.3 Designer / Technical Artist

A user who wants named presets such as:

-   photo
-   poster
-   logo
-   line-art
-   pixel-art
-   black-and-white

## 3.4 Future GUI User

The future PySide6 application must be able to instantiate the same
configuration objects and call the same conversion service without
invoking the CLI executable.

------------------------------------------------------------------------

# 4. Technical Strategy

## 4.1 Core Principle

Use VTracer as the tracing engine.

Do not duplicate VTracer's segmentation, clustering, contour extraction,
curve fitting, or SVG path generation logic.

The application should provide:

``` text
Input
  ↓
Validation
  ↓
Optional preprocessing
  ↓
Configuration resolution
  ↓
VTracer
  ↓
Optional SVG post-processing
  ↓
Output + report
```

## 4.2 Proposed Stack

### Required

-   Python 3.12+
-   VTracer Python package
-   `typer` for CLI
-   `pydantic` for configuration models and validation
-   `pydantic-settings` if environment-variable configuration is
    implemented
-   `Pillow` for image inspection and optional preprocessing
-   `rich` for terminal formatting
-   `platformdirs` for application/config directories
-   `pytest` for tests
-   `ruff` for linting/formatting
-   `mypy` for static type checking where practical

### Recommended

-   `tomli-w` or standard TOML writing support for generated config
    files
-   `PyYAML` for optional YAML configuration support
-   `orjson` for fast JSON reports if useful
-   `lxml` only if sophisticated SVG XML post-processing becomes
    necessary
-   `scour` or another maintained SVG optimizer only if its behavior is
    acceptable and independently tested

### Future GUI

-   PySide6
-   Reuse the same `core`, `config`, and `services` modules
-   GUI must not duplicate VTracer settings logic

------------------------------------------------------------------------

# 5. Supported Input and Output

## 5.1 Required Input Formats

Required:

-   `.jpg`
-   `.jpeg`
-   `.png`

The implementation should also accept additional formats if the
installed VTracer/image decoder supports them reliably.

## 5.2 Required Output Format

-   `.svg`

## 5.3 Input Validation

Before conversion:

-   Verify input exists.
-   Verify it is a file.
-   Attempt to decode the image.
-   Detect image dimensions.
-   Reject zero-width or zero-height images.
-   Produce actionable errors for corrupted files.
-   Warn or fail when image dimensions exceed configured limits.

## 5.4 Output Validation

Before writing:

-   Ensure output parent directory exists, or create it when requested.
-   Prevent accidental overwrite unless explicitly allowed.
-   Verify SVG was produced and is non-empty.
-   Optionally parse generated SVG as XML in validation mode.

------------------------------------------------------------------------

# 6. Command-Line Interface

The executable shall be named:

``` text
raster2svg
```

A Python module entry point should also work:

``` text
python -m raster2svg
```

## 6.1 Primary Commands

``` text
raster2svg convert
raster2svg batch
raster2svg config
raster2svg preset
raster2svg inspect
raster2svg version
```

A shorthand single-file invocation should also be supported:

``` text
raster2svg input.jpg output.svg
```

which is equivalent to:

``` text
raster2svg convert input.jpg output.svg
```

------------------------------------------------------------------------

# 7. Core CLI Requirements

## 7.1 Single File Conversion

``` text
raster2svg convert input.jpg output.svg
```

Example:

``` text
raster2svg convert photo.jpg photo.svg
```

## 7.2 Named Input and Output

``` text
raster2svg convert --input photo.jpg --output photo.svg
```

## 7.3 Positional Input/Output

``` text
raster2svg convert photo.jpg photo.svg
```

## 7.4 Automatic Output Naming

If output is omitted:

``` text
raster2svg convert photo.jpg
```

default output:

``` text
photo.svg
```

Alternative output-directory usage:

``` text
raster2svg convert photo.jpg --output-dir ./svg
```

## 7.5 Standard Help

``` text
raster2svg --help
raster2svg convert --help
raster2svg batch --help
```

The help output must document:

-   accepted values
-   defaults
-   valid ranges
-   examples

------------------------------------------------------------------------

# 8. Configuration Precedence

Configuration must be resolved in this order, from lowest to highest
priority:

1.  Application defaults
2.  Built-in preset defaults
3.  User-level config file
4.  Explicit config file supplied with `--config`
5.  Environment variables, if enabled
6.  Explicit command-line options

Example:

``` text
defaults
    ↓
preset
    ↓
config file
    ↓
environment
    ↓
CLI arguments
```

The final resolved configuration must be inspectable.

Example:

``` text
raster2svg config show --preset poster --config settings.toml
```

Output should display the fully resolved configuration.

------------------------------------------------------------------------

# 9. VTracer Feature Support

The application must not artificially limit VTracer features.

The implementation should introspect or explicitly version-map the
installed VTracer API and expose supported options.

The following settings are expected in the current VTracer 1.x Python
API and should be supported where present.

## 9.1 Presets

Supported built-in presets:

-   `bw`
-   `poster`
-   `photo`

CLI:

``` text
raster2svg convert image.jpg output.svg --preset photo
```

Configuration:

``` toml
preset = "photo"
```

Important behavior:

A preset establishes initial values. Explicit configuration and CLI
options override the preset.

------------------------------------------------------------------------

## 9.2 Region Clustering

Configuration field:

``` text
clustering
```

Supported values:

-   `color-cluster`
-   `bw`
-   `watershed`

Examples:

``` text
--clustering color-cluster
--clustering bw
--clustering watershed
```

Semantics:

-   `color-cluster`: standard color-based region formation.
-   `bw`: binary/black-and-white tracing.
-   `watershed`: content-adaptive region formation.

The tool should reject unsupported combinations when required by the
VTracer version.

------------------------------------------------------------------------

## 9.3 Hierarchical / Layering Mode

Configuration field:

``` text
hierarchical
```

Supported values:

-   `stacked`
-   `cutout`

Examples:

``` text
--hierarchical stacked
--hierarchical cutout
```

Expected behavior:

-   `stacked`: layered output.
-   `cutout`: seam-free mosaic behavior where supported by the installed
    VTracer version.

------------------------------------------------------------------------

## 9.4 Curve Fitting Mode

Configuration field:

``` text
mode
```

Supported values:

-   `pixel`
-   `polygon`
-   `spline`

Examples:

``` text
--mode pixel
--mode polygon
--mode spline
```

------------------------------------------------------------------------

## 9.5 Speckle Filtering

Configuration field:

``` text
filter_speckle
```

Example:

``` text
--filter-speckle 4
```

Expected range should be validated according to the installed engine.
The application should use VTracer's documented supported range where
available.

Purpose:

Discard small regions/patches below the configured size threshold.

------------------------------------------------------------------------

## 9.6 Color Precision

Configuration field:

``` text
color_precision
```

Typical supported range:

``` text
1 through 8
```

Example:

``` text
--color-precision 6
```

Purpose:

Control the number of significant bits used per RGB channel.

------------------------------------------------------------------------

## 9.7 Gradient / Layer Difference

Configuration field:

``` text
layer_difference
```

CLI alias:

``` text
--gradient-step
```

Example:

``` text
--gradient-step 16
```

Purpose:

Control color difference between generated gradient/layer regions.

The internal model should use one canonical field name and provide
aliases for compatibility.

Recommended canonical name:

``` text
layer_difference
```

------------------------------------------------------------------------

## 9.8 Corner Threshold

Configuration field:

``` text
corner_threshold
```

Typical range:

``` text
0 through 180 degrees
```

Example:

``` text
--corner-threshold 60
```

Purpose:

Control when a momentary angle is treated as a corner.

------------------------------------------------------------------------

## 9.9 Segment Length / Length Threshold

Configuration field:

``` text
length_threshold
```

CLI aliases:

``` text
--segment-length
--length-threshold
```

Example:

``` text
--segment-length 4
```

Typical range:

``` text
3.5 through 10
```

Purpose:

Control iterative subdivision/smoothing behavior.

------------------------------------------------------------------------

## 9.10 Maximum Iterations

Configuration field:

``` text
max_iterations
```

Example:

``` text
--max-iterations 10
```

This should be exposed if supported by the installed VTracer API.

------------------------------------------------------------------------

## 9.11 Splice Threshold

Configuration field:

``` text
splice_threshold
```

Example:

``` text
--splice-threshold 45
```

Typical range:

``` text
0 through 180 degrees
```

Purpose:

Control angle displacement used when splicing spline segments.

------------------------------------------------------------------------

## 9.12 Curve Simplification

Configuration field:

``` text
simplify
```

Example:

``` text
--simplify 2.0
```

Purpose:

Reduce curve complexity while keeping fitted curves within the
configured pixel tolerance.

This is an important high-level quality/file-size control and should be
prominently supported.

------------------------------------------------------------------------

## 9.13 Path Precision

Configuration field:

``` text
path_precision
```

Example:

``` text
--path-precision 2
```

Purpose:

Control decimal places in generated SVG path data.

------------------------------------------------------------------------

## 9.14 Fixed Palette

Configuration field:

``` text
palette
```

Example:

``` text
--palette "#1b1b1b,#e0c088,#5a7d3c"
```

Configuration file:

``` toml
palette = ["#1b1b1b", "#e0c088", "#5a7d3c"]
```

Also support:

``` text
--palette-file palette.txt
```

The exact palette-file format must be documented and tested.

Recommended format:

``` text
#1b1b1b
#e0c088
#5a7d3c
```

Requirements:

-   Validate color syntax.
-   Reject malformed colors.
-   Remove duplicate colors unless duplicate preservation is required by
    the engine.

------------------------------------------------------------------------

## 9.15 Maximum Colors

Configuration field:

``` text
max_colors
```

Example:

``` text
--max-colors 8
```

Purpose:

Request automatic palette quantization to the specified number of
colors.

------------------------------------------------------------------------

## 9.16 Optimization Level

Configuration field:

``` text
optimize
```

Expected levels:

-   `0`: off
-   `1`: standard quantization/cleanup
-   `2`: more aggressive output optimization including shorthand forms
    where supported

Example:

``` text
--optimize 2
```

The tool must not silently change optimization behavior.

------------------------------------------------------------------------

## 9.17 Binary Threshold

Configuration field:

``` text
binary_threshold
```

CLI:

``` text
--threshold 128
```

Example:

``` text
--threshold 128
```

Purpose:

Fixed black/white threshold.

------------------------------------------------------------------------

## 9.18 Adaptive Binary Thresholding

Configuration fields:

``` text
adaptive
adaptive_window
adaptive_t
```

Examples:

``` text
--adaptive
--adaptive-window 51
--adaptive-t 15
```

Expected behavior:

Use adaptive thresholding for unevenly lit scans when supported by
VTracer.

Validation:

-   Adaptive settings should either automatically imply `clustering=bw`
    or produce a clear validation error.
-   The chosen behavior must be documented and deterministic.

Recommended behavior:

``` text
--adaptive
```

automatically sets:

``` text
clustering = "bw"
```

unless an explicitly conflicting CLI argument is provided, in which case
fail with an error.

------------------------------------------------------------------------

## 9.19 Watershed Detail

Configuration field:

``` text
watershed_detail
```

Example:

``` text
--watershed-detail 128
```

Expected range:

``` text
0 through 255
```

Recommended validation:

Require or strongly recommend:

``` text
clustering = "watershed"
```

------------------------------------------------------------------------

# 10. Configuration Files

## 10.1 Supported Formats

Required:

-   TOML
-   JSON

Optional:

-   YAML

TOML is the recommended primary format.

## 10.2 Example TOML

``` toml
[conversion]
preset = "photo"
clustering = "color-cluster"
hierarchical = "stacked"
mode = "spline"

filter_speckle = 4
color_precision = 6
layer_difference = 16

corner_threshold = 60
length_threshold = 4.0
max_iterations = 10
splice_threshold = 45

simplify = 1.5
path_precision = 2

max_colors = 16
optimize = 2

[preprocess]
enabled = false
auto_orient = true
resize_max_width = 0
resize_max_height = 0
denoise = false
grayscale = false
pre_max_colors = 16

[output]
overwrite = false
validate_svg = true
report = true
```

## 10.3 Example JSON

``` json
{
  "conversion": {
    "preset": "poster",
    "hierarchical": "cutout",
    "mode": "polygon",
    "filter_speckle": 8,
    "color_precision": 5,
    "max_colors": 8,
    "simplify": 1.5
  },
  "output": {
    "overwrite": false,
    "validate_svg": true
  }
}
```

## 10.4 CLI Usage

``` text
raster2svg convert image.jpg output.svg --config settings.toml
```

## 10.5 Generate Default Config

``` text
raster2svg config init
```

Examples:

``` text
raster2svg config init --output raster2svg.toml
raster2svg config init --preset photo --output photo.toml
```

------------------------------------------------------------------------

# 11. CLI Option Mapping

Every supported config setting should be available through a
command-line argument unless there is a strong usability reason not to
expose it.

Recommended examples:

``` text
raster2svg convert image.jpg output.svg \
  --preset photo \
  --clustering color-cluster \
  --hierarchical stacked \
  --mode spline \
  --filter-speckle 4 \
  --color-precision 6 \
  --gradient-step 16 \
  --corner-threshold 60 \
  --segment-length 4 \
  --max-iterations 10 \
  --splice-threshold 45 \
  --simplify 1.5 \
  --path-precision 2 \
  --max-colors 12 \
  --optimize 2
```

------------------------------------------------------------------------

# 12. Batch Processing

## 12.1 Directory Input

Example:

``` text
raster2svg batch ./images --output-dir ./svg
```

Default behavior:

-   Process supported files in the specified directory.
-   Preserve filename stem.
-   Output `.svg`.

Example:

``` text
images/
  a.jpg
  b.jpg
  c.png

svg/
  a.svg
  b.svg
  c.svg
```

## 12.2 Recursive Processing

``` text
raster2svg batch ./images --output-dir ./svg --recursive
```

When recursive mode is used, preserve relative directory structure by
default:

``` text
images/
  products/a.jpg
  icons/b.png

svg/
  products/a.svg
  icons/b.svg
```

## 12.3 Include Patterns

Examples:

``` text
--include "*.jpg"
--include "*.jpeg"
--include "*.png"
```

## 12.4 Exclude Patterns

Example:

``` text
--exclude "*_thumbnail.*"
```

## 12.5 Parallel Processing

``` text
--jobs 4
```

Requirements:

-   Default to a conservative value.
-   Support `--jobs auto`.
-   Avoid excessive memory usage.
-   Each failed file must not terminate the entire batch unless
    `--fail-fast` is specified.

## 12.6 Batch Exit Codes

Recommended behavior:

-   `0`: all files succeeded
-   `1`: one or more conversions failed
-   `2`: invalid CLI/configuration
-   `3`: input/output filesystem error
-   `4`: dependency/runtime error

A batch report must identify successful and failed files.

------------------------------------------------------------------------

# 13. Image Preprocessing

Preprocessing is optional and should remain separate from VTracer
configuration.

## 13.1 Required/Recommended Preprocessing Features

### Auto-orientation

Respect EXIF orientation.

Default:

``` text
enabled
```

### Resize

Options:

``` text
--resize 1920x1080
--max-width 1920
--max-height 1080
--scale 0.5
```

### Grayscale

``` text
--grayscale
```

### Denoise

Initial implementation may expose conservative Pillow/OpenCV-based
denoising.

### Contrast

``` text
--contrast 1.2
```

### Brightness

``` text
--brightness 1.1
```

### Sharpen

``` text
--sharpen
```

### Pre-max colors

Cap the raster to at most N distinct colors in the preprocessor before tracing
(no dithering). Preprocessor-side, so available on any VTracer version;
distinct from the engine-native `max_colors` (VTracer 1.0).

``` text
--pre-max-colors 16
```

## 13.2 Preprocessing Philosophy

Preprocessing must be:

-   explicit
-   reproducible
-   represented in the resolved config
-   reported in conversion metadata

The tool must never silently modify the input image.

------------------------------------------------------------------------

# 14. Output Behavior

## 14.1 Overwrite Protection

Default:

Do not overwrite existing files.

Example:

``` text
raster2svg convert image.jpg image.svg
```

If `image.svg` exists:

``` text
ERROR: Output file already exists.
Use --overwrite to replace it.
```

## 14.2 Overwrite Option

``` text
--overwrite
```

## 14.3 Create Directories

``` text
--mkdir
```

Recommended behavior:

Automatically create output directories for explicit output paths unless
`--no-mkdir` is specified.

## 14.4 Atomic Writes

Recommended:

1.  Write SVG to a temporary file in the target directory.
2.  Validate if requested.
3.  Atomically rename/replace the target.

This prevents partially written output files.

------------------------------------------------------------------------

# 15. Dry Run and Inspection

## 15.1 Dry Run

``` text
raster2svg convert image.jpg output.svg --dry-run
```

Must:

-   resolve configuration
-   validate input
-   validate output path
-   display intended operation
-   not create SVG

## 15.2 Show Resolved Configuration

``` text
raster2svg convert image.jpg output.svg --show-config
```

Example:

``` text
Resolved configuration:
  preset: photo
  clustering: color-cluster
  hierarchical: stacked
  mode: spline
  filter_speckle: 4
  color_precision: 6
  ...
```

## 15.3 JSON Config Output

``` text
--show-config --format json
```

## 15.4 Input Inspection

``` text
raster2svg inspect image.jpg
```

Suggested output:

``` text
Path: image.jpg
Format: JPEG
Width: 6000
Height: 4000
Pixels: 24,000,000
Has alpha: false
EXIF orientation: 1
Estimated memory: ...
```

------------------------------------------------------------------------

# 16. Preset System

## 16.1 Built-In Presets

Required:

-   `bw`
-   `photo`
-   `poster`

Application-level convenience presets may also be provided:

-   `logo`
-   `line-art`
-   `pixel-art`

Custom convenience presets must be clearly distinguished from native
VTracer presets.

## 16.2 List Presets

``` text
raster2svg preset list
```

## 16.3 Show Preset

``` text
raster2svg preset show photo
```

## 16.4 Custom Presets

Allow user-defined presets stored as config files:

``` text
raster2svg preset save my-logo --from-config logo.toml
```

Later:

``` text
raster2svg convert logo.jpg logo.svg --preset my-logo
```

Custom preset storage should use a platform-appropriate application
directory.

------------------------------------------------------------------------

# 17. Machine-Readable Output

## 17.1 JSON Report

Example:

``` text
raster2svg convert image.jpg output.svg --report report.json
```

Suggested schema:

``` json
{
  "tool_version": "1.0.0",
  "status": "success",
  "input": {
    "path": "image.jpg",
    "format": "JPEG",
    "width": 6000,
    "height": 4000
  },
  "output": {
    "path": "output.svg",
    "bytes": 123456,
    "sha256": "..."
  },
  "duration_ms": 842,
  "config": {
    "preset": "photo",
    "mode": "spline"
  }
}
```

## 17.2 JSON Lines for Batch Processing

Example:

``` text
--jsonl
```

Each completed file should emit one JSON object.

This is useful for pipelines and automation.

------------------------------------------------------------------------

# 18. Logging

## 18.1 Levels

Support:

-   ERROR
-   WARNING
-   INFO
-   DEBUG

CLI:

``` text
--verbose
--quiet
--log-level debug
```

## 18.2 Log Files

Optional:

``` text
--log-file conversion.log
```

## 18.3 Progress

For interactive terminals:

-   Use progress indicators for batch processing.
-   Do not emit progress bars when `--json` or `--jsonl` is active.
-   Detect non-interactive environments.

------------------------------------------------------------------------

# 19. Error Handling

Errors must be actionable.

Bad:

``` text
RuntimeError
```

Good:

``` text
ERROR: Invalid color precision: 12
Expected a value between 1 and 8.
```

Examples requiring explicit handling:

-   missing input
-   unsupported/corrupt image
-   invalid config syntax
-   invalid config field
-   unsupported VTracer option
-   invalid palette color
-   output already exists
-   permission denied
-   VTracer runtime failure
-   memory failure
-   interrupted conversion

------------------------------------------------------------------------

# 20. Configuration Validation

Use Pydantic models as the canonical configuration schema.

Suggested structure:

``` text
AppConfig
├── conversion: ConversionConfig
├── preprocess: PreprocessConfig
├── output: OutputConfig
├── batch: BatchConfig
└── runtime: RuntimeConfig
```

## 20.1 ConversionConfig

Suggested fields:

``` text
preset
clustering
hierarchical
mode
filter_speckle
color_precision
layer_difference
corner_threshold
length_threshold
max_iterations
splice_threshold
simplify
path_precision
palette
palette_file
max_colors
optimize
binary_threshold
adaptive
adaptive_window
adaptive_t
watershed_detail
```

The implementation must use optional fields for settings where `None`
means "do not override the underlying VTracer default."

------------------------------------------------------------------------

# 21. Version Compatibility Strategy

VTracer evolves.

The application must not assume that every installed VTracer version
supports every feature.

Implement:

``` text
EngineCapabilities
```

Example:

``` python
@dataclass
class EngineCapabilities:
    version: str
    supports_watershed: bool
    supports_palette: bool
    supports_max_colors: bool
    supports_simplify: bool
    supports_adaptive_threshold: bool
```

At startup or on first conversion:

1.  Determine installed VTracer version.
2.  Detect supported API/configuration fields where practical.
3.  Reject unsupported requested settings with clear errors.
4.  Include engine version in reports.

Do not silently ignore requested features.

------------------------------------------------------------------------

# 22. Architecture

Recommended project structure:

``` text
raster2svg/
├── pyproject.toml
├── README.md
├── LICENSE
├── docs/
│   ├── configuration.md
│   ├── cli.md
│   ├── presets.md
│   └── architecture.md
├── src/
│   └── raster2svg/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli/
│       │   ├── app.py
│       │   ├── convert.py
│       │   ├── batch.py
│       │   ├── config.py
│       │   ├── preset.py
│       │   └── inspect.py
│       ├── config/
│       │   ├── models.py
│       │   ├── loader.py
│       │   ├── resolver.py
│       │   ├── defaults.py
│       │   └── validation.py
│       ├── core/
│       │   ├── models.py
│       │   ├── conversion.py
│       │   ├── capabilities.py
│       │   └── errors.py
│       ├── engines/
│       │   ├── base.py
│       │   └── vtracer_engine.py
│       ├── preprocess/
│       │   ├── image.py
│       │   └── operations.py
│       ├── output/
│       │   ├── svg.py
│       │   ├── reports.py
│       │   └── atomic_write.py
│       ├── services/
│       │   ├── converter.py
│       │   └── batch_converter.py
│       └── utils/
│           ├── paths.py
│           ├── logging.py
│           └── hashing.py
└── tests/
    ├── unit/
    ├── integration/
    ├── fixtures/
    └── golden/
```

------------------------------------------------------------------------

# 23. Core API

The CLI should be a thin wrapper around a reusable Python API.

Example conceptual API:

``` python
from raster2svg import Converter, ConversionConfig

config = ConversionConfig(
    preset="photo",
    mode="spline",
    simplify=1.5,
    max_colors=12,
)

result = Converter().convert(
    input_path="photo.jpg",
    output_path="photo.svg",
    config=config,
)
```

Batch:

``` python
results = Converter().convert_many(
    input_paths=paths,
    output_dir="svg",
    config=config,
    jobs=4,
)
```

The future PySide6 application should call this API directly.

------------------------------------------------------------------------

# 24. PySide6 Future Compatibility

The CLI project must be designed so a GUI can be added without changing
the conversion engine.

Future GUI architecture:

``` text
PySide6 UI
    ↓
View Models / Controllers
    ↓
raster2svg.core + services
    ↓
VTracer Engine
```

The GUI should use:

-   the same Pydantic config models
-   the same presets
-   the same validation
-   the same conversion reports
-   the same preprocessing services

No tracing business logic should live inside Qt widgets.

------------------------------------------------------------------------

# 25. Testing Requirements

## 25.1 Unit Tests

Test:

-   config loading
-   config precedence
-   validation
-   CLI parsing
-   aliases
-   preset overrides
-   path handling
-   palette parsing
-   report generation
-   error mapping

## 25.2 Integration Tests

Test actual conversions using small fixture images:

-   JPEG photo
-   PNG transparency
-   black-and-white line art
-   flat-color logo
-   pixel-art image
-   image with noise

## 25.3 Golden Tests

For deterministic configurations:

-   Generate SVG.
-   Normalize harmless metadata.
-   Compare output or structural SVG characteristics.

Because exact SVG serialization may vary by VTracer version, tests
should distinguish:

-   exact golden tests
-   structural tests
-   semantic tests

## 25.4 Performance Tests

Track:

-   conversion duration
-   peak memory where practical
-   SVG output size

Test representative images:

-   512x512
-   1920x1080
-   4000x3000

------------------------------------------------------------------------

# 26. Packaging and Distribution

## 26.1 Development Installation

Use:

``` text
pip install -e .[dev]
```

## 26.2 Build System

Use:

-   `pyproject.toml`
-   modern Python packaging
-   pinned dependency ranges

## 26.3 Windows Distribution

Initial options:

-   Python wheel for developer users
-   standalone executable using Nuitka or PyInstaller

Preferred evaluation:

1.  Develop and test with normal Python packaging.
2.  Validate standalone Windows packaging near release.
3.  Choose Nuitka or PyInstaller based on VTracer native-extension
    compatibility, startup time, antivirus false positives, and binary
    size.

## 26.4 CI

Recommended:

-   GitHub Actions
-   Windows test matrix
-   Python version matrix
-   Ruff
-   Pytest
-   Packaging smoke test

**Decision (v0.2):** No CI / GitHub Actions pipeline will be set up at this
time. Development is single-machine (local Windows) and the checks above
(Ruff, Mypy, Pytest, plus a manual packaging smoke test) are run locally as the
verification gate before each commit/release. A remote CI pipeline can be added
later if the project moves to a shared or multi-platform development model; the
local gate commands remain the source of truth in the meantime.

------------------------------------------------------------------------

# 27. Performance Requirements

Version 1 targets:

-   UI is not applicable; CLI startup should remain reasonably fast.
-   Avoid loading full image data multiple times unless preprocessing
    requires it.
-   Do not duplicate large images unnecessarily.
-   Batch mode must have bounded concurrency.
-   Large images should not cause uncontrolled memory growth.

The tool should report elapsed conversion time in verbose/report modes.

------------------------------------------------------------------------

# 28. Security and Safety

The tool processes local files.

Requirements:

-   Never execute embedded image metadata.
-   Never use shell interpolation for input paths.
-   Use `pathlib`/safe subprocess APIs where needed.
-   Treat configuration files as data, not executable code.
-   Validate output paths.
-   Do not automatically upload images or telemetry.

------------------------------------------------------------------------

# 29. Telemetry

Default:

``` text
No telemetry.
```

If telemetry is ever added, it must be opt-in.

------------------------------------------------------------------------

# 30. Example Workflows

## 30.1 Simplest Conversion

``` text
raster2svg photo.jpg photo.svg
```

## 30.2 High-Quality Photo

``` text
raster2svg convert photo.jpg photo.svg \
  --preset photo \
  --mode spline \
  --simplify 1.5 \
  --max-colors 24 \
  --optimize 2
```

## 30.3 Flat Logo

``` text
raster2svg convert logo.jpg logo.svg \
  --mode polygon \
  --hierarchical cutout \
  --max-colors 8 \
  --filter-speckle 2 \
  --simplify 1.0
```

## 30.4 Black-and-White Scan

``` text
raster2svg convert scan.jpg scan.svg \
  --clustering bw \
  --adaptive \
  --adaptive-t 15 \
  --mode spline
```

## 30.5 Watershed

``` text
raster2svg convert image.jpg image.svg \
  --clustering watershed \
  --watershed-detail 160 \
  --hierarchical cutout \
  --simplify 2
```

## 30.6 Config-Driven

``` text
raster2svg convert image.jpg image.svg --config production.toml
```

## 30.7 CLI Override of Config

``` text
raster2svg convert image.jpg image.svg \
  --config production.toml \
  --max-colors 8 \
  --overwrite
```

## 30.8 Batch

``` text
raster2svg batch ./images \
  --output-dir ./svg \
  --recursive \
  --config production.toml \
  --jobs 4 \
  --report batch-report.json
```

------------------------------------------------------------------------

# 31. Acceptance Criteria

The implementation is acceptable for Version 1 when all of the following
are true.

## Core

-   [ ] Converts JPG to SVG successfully.
-   [ ] Converts PNG to SVG successfully.
-   [ ] Supports positional input/output arguments.
-   [ ] Supports named input/output arguments.
-   [ ] Supports config files.
-   [ ] Supports deterministic config precedence.
-   [ ] Supports built-in VTracer presets.
-   [ ] Supports batch conversion.
-   [ ] Supports overwrite protection.
-   [ ] Supports dry-run.
-   [ ] Supports resolved-config inspection.
-   [ ] Supports JSON reports.

## VTracer

-   [ ] Supports all available practical VTracer settings exposed by the
    installed Python package.
-   [ ] Detects unsupported requested features.
-   [ ] Does not silently ignore requested options.
-   [ ] Exposes major clustering, hierarchy, curve-fitting, palette,
    simplification, thresholding, and optimization features where
    supported.

## Quality

-   [ ] Unit test suite passes.
-   [ ] Integration tests pass on Windows.
-   [ ] Corrupt images fail cleanly.
-   [ ] Invalid configs fail with useful messages.
-   [ ] Batch mode continues after individual file failures unless
    fail-fast is requested.
-   [ ] Generated SVGs are non-empty and valid when validation is
    enabled.

## Architecture

-   [ ] CLI is thin.
-   [ ] Conversion logic is reusable as a Python library.
-   [ ] Configuration models are independent of CLI code.
-   [ ] Future PySide6 GUI can reuse the core conversion API.

------------------------------------------------------------------------

# 32. Recommended Implementation Order

## Milestone 1: Foundation

1.  Create project structure.
2.  Configure `pyproject.toml`.
3.  Add VTracer dependency.
4.  Add Typer CLI.
5.  Add basic `convert`.
6.  Convert JPG to SVG with defaults.
7.  Add tests.

## Milestone 2: Configuration

1.  Add Pydantic models.
2.  Add TOML loading.
3.  Add JSON loading.
4.  Implement precedence resolution.
5.  Add `config show`.
6.  Add `config init`.

## Milestone 3: VTracer Feature Coverage

1.  Map installed VTracer API.
2.  Implement all supported conversion fields.
3.  Add aliases matching common VTracer terminology.
4.  Add presets.
5.  Add palette support.
6.  Add adaptive threshold support.
7.  Add watershed support.
8.  Add capability/version detection.

## Milestone 4: Production CLI

1.  Batch processing.
2.  Parallel jobs.
3.  Progress output.
4.  JSON reports.
5.  Logging.
6.  Atomic output writes.
7.  SVG validation.

## Milestone 5: Preprocessing

1.  Auto-orientation.
2.  Resize.
3.  Grayscale.
4.  Denoise.
5.  Contrast/brightness/sharpen.
6.  Pre-max colors (palette cap before tracing).

## Milestone 6: Packaging

1.  Windows packaging experiment.
2.  Test native VTracer dependency.
3.  Build executable.
4.  CI packaging smoke tests.
5.  Release documentation.

------------------------------------------------------------------------

# 33. Coding-Agent Instructions

The coding agent should follow these implementation rules:

1.  Do not implement raster tracing algorithms from scratch.
2.  Use the VTracer Python API as the primary tracing engine.
3.  Verify the actual installed VTracer API rather than blindly assuming
    parameter names.
4.  Keep engine-specific code inside `engines/vtracer_engine.py`.
5.  Use strongly typed Pydantic configuration models.
6.  Preserve `None` for "engine default" where appropriate.
7.  Never silently discard unsupported configuration values.
8.  Add tests before or alongside each major feature.
9.  Keep CLI parsing separate from conversion business logic.
10. Use `pathlib` for filesystem operations.
11. Support Windows paths correctly.
12. Avoid shelling out to the VTracer CLI when the Python API can
    provide the required capability.
13. If a VTracer Python API feature is missing, either:
    -   implement a clearly isolated fallback, or
    -   fail with a precise unsupported-feature error.
14. Do not add a GUI in Version 1 unless requested; design for future
    PySide6 reuse.
15. Keep the project installable with a single modern Python packaging
    workflow.
16. Document every config option and its precedence.
17. Include sample configuration files.
18. Include fixture images that are small enough for source control.
19. Add a capability test command if useful, for example:
    `raster2svg engine capabilities`.
20. Prefer correctness and reproducibility over hiding complexity.

------------------------------------------------------------------------

# 34. Definition of Done

Version 1 is complete when a Windows user can install or run the tool
and reliably execute:

``` text
raster2svg input.jpg output.svg
```

and advanced users can reproduce a complete conversion through a
configuration file such as:

``` text
raster2svg convert input.jpg output.svg --config settings.toml
```

while overriding individual settings:

``` text
raster2svg convert input.jpg output.svg \
  --config settings.toml \
  --mode spline \
  --simplify 1.5 \
  --max-colors 12
```

The same resolved configuration and conversion engine must be reusable
by a future PySide6 desktop application without rewriting the tracing
pipeline.

------------------------------------------------------------------------

# 35. Reference Notes for the Implementer

This PRD intentionally targets the modern VTracer Python interface and
asks the implementation to verify the installed package version at
build/runtime.

Expected VTracer capabilities include, depending on the installed
version:

-   Config objects and reusable conversion configuration.
-   Built-in presets.
-   Color, black-and-white, and watershed clustering.
-   Stacked and cutout hierarchy.
-   Pixel, polygon, and spline fitting.
-   Speckle filtering.
-   Color precision and layer difference.
-   Corner, segment, iteration, and splice controls.
-   Curve simplification.
-   Path precision.
-   Fixed palettes and automatic color quantization.
-   Output optimization.
-   Fixed and adaptive binary thresholding.
-   Watershed detail.

The implementer should treat the actual installed VTracer package API as
authoritative and add a compatibility layer so the CLI remains stable
even if engine parameter names differ between supported VTracer
releases.
