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

### Canonical way: use `scripts\web-server.ps1` (always verify, never assume)
```powershell
.\scripts\web-server.ps1 status   -Port 9921
.\scripts\web-server.ps1 start    -Port 9921 [-Sample tests\golden\logo_spline.svg]
.\scripts\web-server.ps1 restart  -Port 9921 [-Sample tests\golden\logo_spline.svg]
.\scripts\web-server.ps1 stop     -Port 9921
```
- `stop` kills every `raster2svg` launcher tree (and any orphaned listener on the port),
  then waits up to 5 s per attempt (3 attempts) until the port is actually released;
  it fails with the surviving PIDs otherwise. It never hangs.
- `start` launches detached (logs: `%TEMP%\r2s-web.log` / `r2s-web.err`) and polls up to
  15 s for `GET /api/info` → HTTP 200 before reporting success.
- Foreground alternative (Ctrl+C to stop): `raster2svg web [--sample path\to\file.svg]`.
- Manual fallback (if the script is unavailable):
  ```powershell
  netstat -ano | findstr :9921 | findstr LISTENING   # listener PID
  Get-Process raster2svg | ForEach-Object { taskkill /F /T /PID $_.Id }   # kill the tree
  ```

### Gotchas (these have cost time)
- **The UI is cached at startup.** `WebServer` reads `static/index.html` once in `__init__`
  and serves that string. After editing the UI you **must restart the server** — a browser
  refresh is NOT enough (CSS/JS are inlined into index.html).
- **Use port 9921.** Don't spin up ad-hoc ports (9922, 9923, …) unless you intentionally
  need a second instance, and clean them up when done.
- **Don't leave stray servers.** Check for existing instances before starting (`status`);
  stop test servers after. Multiple instances → port conflicts + confusion.
- **`--sample` path with spaces.** `web-server.ps1` quotes the path for you; if you launch
  detached by hand, `Start-Process -ArgumentList` will split a space-containing path into
  extra arguments ("Got unexpected extra argument") — use a space-free path.
- **The sandbox bash tool kills foreground commands on timeout.** To keep a server alive
  across tool calls, use `web-server.ps1 start` (detached + verified) instead of running
  `raster2svg web` in the foreground.

## Testing the UI without converting an image
`--sample <path-to-svg>` exposes `GET /api/sample` and enables the **Sample** button, so
you can load a known SVG and exercise the preview/zoom controls. Golden SVGs: `tests/golden/*.svg`.
