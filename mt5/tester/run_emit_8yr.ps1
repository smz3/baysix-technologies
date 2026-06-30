# FOB emitter FULL-HISTORY runner (task 190). Runs the 8yr emit ONCE, times it,
# reports the capture CSV size, and writes a DONE sentinel so the orchestrator can
# wait on existence (not mtime). JM terminal MUST be closed. ~90min / ~390MB est.
param(
  [string]$Term   = 'C:\Program Files\JustMarkets MetaTrader 5\terminal64.exe',
  [string]$Config = 'C:\Users\User\Desktop\baysix-technologies\mt5\tester\fob_emit_8yr.ini',
  [string]$Common = "$env:APPDATA\MetaQuotes\Terminal\Common\Files\FOB",
  [string]$Glob   = 'fob_capture_*dukas*2016*',
  [string]$Done   = 'C:\Users\User\Desktop\baysix-technologies\mt5\tester\_emit_8yr.done'
)
$ErrorActionPreference = 'Stop'
if (Test-Path $Done) { Remove-Item $Done -Force }
if (Get-Process terminal64 -ErrorAction SilentlyContinue) {
  Write-Error 'terminal64 already running — close it first.'; exit 2 }

Write-Host '[emit-8yr] launching FULL-HISTORY emit (2016.06 -> 2024.07, real ticks Model=4) ...'
$sw = [System.Diagnostics.Stopwatch]::StartNew()
Start-Process -FilePath $Term -ArgumentList "/config:$Config" -Wait
$sw.Stop()
$mins = [math]::Round($sw.Elapsed.TotalMinutes, 2)

$csv = Get-ChildItem -Path $Common -Filter $Glob -File |
       Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $csv) { Write-Error "no capture matching '$Glob' in $Common"; exit 3 }
$mb = [math]::Round($csv.Length / 1MB, 2)

$report = @"
EMIT-8YR DONE
csv         = $($csv.Name)
bytes       = $($csv.Length)
size_mb     = $mb
runtime_min = $mins
window      = 2016.06.01 -> 2024.07.01 (Model=4 real ticks)
version     = fob_baysix v1.25.0
next        = ingest_fob -> run_id 18, then task 192 storyline screen
"@
$report | Tee-Object -FilePath $Done
Write-Host "[emit-8yr] DONE -> $Done"
