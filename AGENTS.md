# AGENTS.md

Guidance for AI agents (and humans) working in this repo.

## Project
`raster2svg` — raster→SVG converter CLI + live web UI, powered by VTracer.
- Python ≥ 3.12, hatchling, entry point `raster2svg` (see `pyproject.toml`).
- Source: `src/raster2svg/` · Tests: `tests/` · Web UI: `src/raster2svg/web/` (all UI is inlined in `web/static/index.html`).

## Setup & common commands
```powershell
python -m venv .venv
.\.venv\Scripts\pip install -e ".[dev]"
```
| Task | Command |
| --- | --- |
| Run tests | `pytest` |
| Lint | `ruff check .` (auto-fix: `ruff check . --fix`) |
| Type-check | `mypy` |
| CLI help | `raster2svg --help` |
| Web UI | `raster2svg web`  →  http://localhost:9921/ |

## Web UI — start / verify / stop (READ THIS before testing the UI)

The server is a **foreground console app** and a **process tree**, not one process:
```
raster2svg.exe   (launcher)          <- Get-Process raster2svg returns THIS one
└─ python.exe   (venv python)
   └─ python.exe (real server)       <- this is what LISTENs on the port
```

### Start (canonical port is 9921)
```powershell
raster2svg web                                             # Ctrl+C to stop
raster2svg web --sample path\to\file.svg                   # also enables the "Sample" button
```

### Is it running? (ALWAYS verify — never assume)
```powershell
netstat -ano | findstr :9921 | findstr LISTENING          # shows the listener PID
Get-Process raster2svg -ErrorAction SilentlyContinue      # non-null => an instance is up
Invoke-WebRequest http://127.0.0.1:9921/ -UseBasicParsing # HTTP 200 => serving
```

### Stop it — kill the WHOLE tree, not just the listener
The listener is the *grandchild*; killing only its PID orphans the parents. Kill the
top-level launcher with `/T` so the entire tree terminates:
```powershell
# kill every running instance + its children:
Get-Process raster2svg -ErrorAction SilentlyContinue | ForEach-Object { taskkill /F /T /PID $_.Id }
# or a single instance by its launcher PID:
taskkill /F /T /PID <raster2svg.exe-PID>
```

### Gotchas (these have cost time)
- **The UI is cached at startup.** `WebServer` reads `static/index.html` once in `__init__`
  and serves that string. After editing the UI you **must restart the server** — a browser
  refresh is NOT enough (CSS/JS are inlined into index.html).
- **Use port 9921.** Don't spin up ad-hoc ports (9922, 9923, …) unless you intentionally
  need a second instance, and clean them up when done.
- **Don't leave stray servers.** Check for existing instances before starting; kill test
  servers after. Multiple instances → port conflicts + confusion.
- **Detached launch + `--sample` path with spaces breaks.** `Start-Process -ArgumentList`
  splits a space-containing path into extra arguments ("Got unexpected extra argument").
  Use a space-free path (copy the file to `%TEMP%` first) or launch in the foreground.
- **The sandbox bash tool kills foreground commands on timeout.** To keep a server alive
  across tool calls, launch detached, then verify it's listening before proceeding:
  ```powershell
  $s = Start-Process -FilePath ".venv\Scripts\raster2svg.exe" `
         -ArgumentList @("web","--port","9921") `
         -RedirectStandardOutput "$env:TEMP\r2s.log" `
         -RedirectStandardError  "$env:TEMP\r2s.err" `
         -PassThru -WindowStyle Hidden
  # VERIFY:  netstat -ano | findstr :9921 | findstr LISTENING
  ```

## Testing the UI without converting an image
`--sample <path-to-svg>` exposes `GET /api/sample` and enables the **Sample** button, so
you can load a known SVG and exercise the preview/zoom controls. Golden SVGs: `tests/golden/*.svg`.
