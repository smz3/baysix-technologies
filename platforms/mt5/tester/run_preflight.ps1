# FOB emitter PRE-FLIGHT runner (task 190 scoping). Runs the 1-year slice ONCE,
# times it, reports the capture CSV size, and writes a DONE sentinel so the
# orchestrator can wait on existence (not mtime). JM terminal MUST be closed.
param(
  [string]$Term   = 'C:\Program Files\JustMarkets MetaTrader 5\terminal64.exe',
  [string]$Config = 'C:\Users\User\Desktop\baysix-technologies\mt5\tester\fob_preflight_1yr.ini',
  [string]$Common = "$env:APPDATA\MetaQuotes\Terminal\Common\Files\FOB",
  [string]$Glob   = 'fob_capture_*dukas*2016*',
  [string]$Done   = 'C:\Users\User\Desktop\baysix-technologies\mt5\tester\_preflight.done'
)
$ErrorActionPreference = 'Stop'
if (Test-Path $Done) { Remove-Item $Done -Force }
if (Get-Process terminal64 -ErrorAction SilentlyContinue) {
  Write-Error 'terminal64 already running — close it first.'; exit 2 }

Write-Host '[preflight] launching 1-year emit (2016.06 -> 2017.06, real ticks) ...'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
Start-Process -FilePath $Term -ArgumentList "/config:$Config" -Wait
$sw.Stop()
$mins = [math]::Round($sw.Elapsed.TotalMinutes, 2)

$csv = Get-ChildItem -Path $Common -Filter $Glob -File |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $csv) { Write-Error "no capture matching '$Glob' in $Common"; exit 3 }
$mb = [math]::Round($csv.Length / 1MB, 2)

# extrapolate to the full 8.06yr window (2016.06 -> 2024.07 ~= 8.08x of 1yr)
$scale = 8.08
$fullMin = [math]::Round($mins * $scale, 1)
$fullMb  = [math]::Round($mb   * $scale, 1)

$report = @"
PREFLIGHT DONE
csv      = $($csv.Name)
bytes    = $($csv.Length)
size_mb  = $mb
runtime_min = $mins
--- extrapolated full 8yr (x$scale) ---
est_runtime_min = $fullMin
est_size_mb     = $fullMb
"@
$report | Tee-Object -FilePath $Done
Write-Host "[preflight] DONE -> $Done"
