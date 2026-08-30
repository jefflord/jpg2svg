<#
.SYNOPSIS
  Stop / start / restart / status the local raster2svg web server.

.DESCRIPTION
  The server is a process tree (raster2svg.exe launcher -> python -> python
  listener), so it must be killed as a tree. This script always verifies the
  actual result (port released / HTTP 200) with bounded waits:
    stop    kill every launcher tree + orphaned listener, wait up to 5 s per
            attempt, up to 3 attempts; fails with the surviving PIDs
    start   launch detached (logs in %TEMP%\r2s-web.log / .err), poll up to
            15 s (3 x 5 s) for the HTTP endpoint before reporting success
    restart stop then start
    status  print launcher PIDs, port listener, and HTTP status

.EXAMPLE
  .\scripts\web-server.ps1 status  -Port 9921
  .\scripts\web-server.ps1 start   -Port 9921 -Sample tests\golden\logo_spline.svg
  .\scripts\web-server.ps1 restart -Port 9921
  .\scripts\web-server.ps1 stop    -Port 9921
#>
param(
  [Parameter(Position = 0)]
  [ValidateSet("start", "stop", "restart", "status")]
  [string]$Action = "status",

  [string]$Port = "9921",

  [string]$BindHost = "127.0.0.1",

  [string]$Sample = ""
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Exe = Join-Path $RepoRoot ".venv\Scripts\raster2svg.exe"
$LogFile = Join-Path $env:TEMP "r2s-web.log"
$ErrLog = Join-Path $env:TEMP "r2s-web.err"

function Test-PortListening([string]$Port) {
  return [bool](Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Get-ListenerPids([string]$Port) {
  @(Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique)
}

function Stop-WebServer([string]$Port) {
  for ($attempt = 1; $attempt -le 3; $attempt++) {
    Get-Process -Name raster2svg -ErrorAction SilentlyContinue |
      ForEach-Object { & taskkill /F /T /PID $_.Id 2>&1 | Out-Null }
    foreach ($pid in (Get-ListenerPids $Port)) {
      Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
    }
    $deadline = (Get-Date).AddSeconds(5)
    while ((Test-PortListening $Port) -and ((Get-Date) -lt $deadline)) {
      Start-Sleep -Milliseconds 500
    }
    if (-not (Test-PortListening $Port)) {
      Write-Host "stopped: port ${Port} is free"
      return
    }
    Write-Host "attempt ${attempt}/3: port ${Port} still listening, retrying..."
  }
  $pids = (Get-ListenerPids $Port) -join ", "
  throw "Could not release port ${Port} after 3 attempts. Still listening: PID(s) ${pids}"
}

function Start-WebServer([string]$Port, [string]$BindHost, [string]$Sample) {
  if (Test-PortListening $Port) {
    throw "Port ${Port} is already in use. Run action 'stop' or 'restart' first."
  }
  if (-not (Test-Path $Exe)) {
    throw "Entry point not found: ${Exe}. Install first: .venv\Scripts\pip install -e '.[dev]'"
  }
  $args = @("web", "--host", $BindHost, "--port", $Port)
  if ($Sample) {
    $resolved = (Resolve-Path -LiteralPath $Sample).Path
    $args += @("--sample", "`"$resolved`"")
  }
  $proc = Start-Process -FilePath $Exe -ArgumentList $args `
    -RedirectStandardOutput $LogFile -RedirectStandardError $ErrLog `
    -WindowStyle Hidden -PassThru
  for ($attempt = 1; $attempt -le 3; $attempt++) {
    $deadline = (Get-Date).AddSeconds(5)
    while ((Get-Date) -lt $deadline) {
      try {
        $r = Invoke-WebRequest "http://127.0.0.1:$Port/api/info" -UseBasicParsing -TimeoutSec 1
        if ($r.StatusCode -eq 200) {
          Write-Host "started: launcher PID $($proc.Id), serving http://127.0.0.1:$Port/ (log: $LogFile)"
          return
        }
      } catch { }
      Start-Sleep -Milliseconds 500
    }
    Write-Host "attempt ${attempt}/3: server not responding yet..."
  }
  throw "Server did not come up on port ${Port} within 15 s. Check ${ErrLog}"
}

function Show-Status([string]$Port) {
  $procs = @(Get-Process -Name raster2svg -ErrorAction SilentlyContinue)
  $listening = Test-PortListening $Port
  $pids = (Get-ListenerPids $Port) -join ", "
  $http = $null
  try {
    $http = (Invoke-WebRequest "http://127.0.0.1:$Port/" -UseBasicParsing -TimeoutSec 2).StatusCode
  } catch { }
  Write-Host ("launcher PIDs     : " + $(if ($procs) { $procs.Id -join ", " } else { "none" }))
  Write-Host ("port ${Port}      : " + $(if ($listening) { "LISTENING (PID $pids)" } else { "free" }))
  Write-Host ("http status       : " + $(if ($http) { $http } else { "n/a" }))
  if (-not $listening) { exit 1 }
}

switch ($Action) {
  "stop"    { Stop-WebServer $Port }
  "start"   { Start-WebServer $Port $BindHost $Sample }
  "restart" { Stop-WebServer $Port; Start-WebServer $Port $BindHost $Sample }
  "status"  { Show-Status $Port }
}
