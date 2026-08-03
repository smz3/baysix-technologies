# GRW-001 — TRUE-JM-COST pair runner (tight 5-pip vs wide 10-pip, XAUUSD.s, real ticks).
#
# Runs both configs SEQUENTIALLY in this window with live output, copies the resulting
# run-summary + trade-ledger CSVs into mt5/tester/artifacts/, and writes a DONE sentinel
# whose EXISTENCE (not mtime) the orchestrator waits on.
#
# The JM terminal MUST be closed — the headless /config: tester silently no-ops if a
# terminal64.exe instance is already up.
#
# NOTE: the terminal is logged into JustMarkets-Live2, whose XAUUSD.s tick cache is thin
# (~5 months). MT5 will download the 2021.04+ history from the JM server on the first run.
# Expect the first pass to spend real time downloading before any bar is processed.
param(
  [string]$Term      = 'C:\Program Files\JustMarkets MetaTrader 5\terminal64.exe',
  [string]$TesterDir = 'C:\Users\User\Desktop\baysix-technologies\mt5\tester',
  [string]$Common    = "$env:APPDATA\MetaQuotes\Terminal\Common\Files",
  [string]$Done      = 'C:\Users\User\Desktop\baysix-technologies\mt5\tester\_grw_jm_cost.done'
)
$ErrorActionPreference = 'Stop'
if (Test-Path $Done) { Remove-Item $Done -Force }
if (Get-Process terminal64 -ErrorAction SilentlyContinue) {
  Write-Error 'terminal64 already running — close it first.'; exit 2 }

$ArtDir = Join-Path $TesterDir 'artifacts'
if (-not (Test-Path $ArtDir)) { New-Item -ItemType Directory -Path $ArtDir | Out-Null }

$runs = @(
  @{ Tag = 'jm_tight'; Ini = 'grw_jm_tight.ini'; Note = '5-pip stop, risk 2.5%' },
  @{ Tag = 'jm_wide';  Ini = 'grw_jm_wide.ini';  Note = '10-pip stop, risk 5.0%' }
)

$lines = @()
foreach ($r in $runs) {
  $cfg = Join-Path $TesterDir $r.Ini
  Write-Host ''
  Write-Host "[grw-jm] === $($r.Tag) — $($r.Note) ===" -ForegroundColor Cyan
  Write-Host "[grw-jm] config: $cfg"
  Write-Host '[grw-jm] launching (real ticks, XAUUSD.s, 2021.04 -> 2026.07) ...'
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  Start-Process -FilePath $Term -ArgumentList "/config:$cfg" -Wait
  $sw.Stop()
  $mins = [math]::Round($sw.Elapsed.TotalMinutes, 2)
  Write-Host "[grw-jm] $($r.Tag) finished in $mins min" -ForegroundColor Green

  # collect every CSV this batch produced (run summary + trade ledger + params)
  $found = Get-ChildItem -Path $Common -Filter "*$($r.Tag)*" -File -ErrorAction SilentlyContinue
  if (-not $found) {
    Write-Host "[grw-jm] WARNING: no output matching *$($r.Tag)* in $Common" -ForegroundColor Yellow
    $lines += "$($r.Tag): NO OUTPUT (runtime ${mins}m)"
  } else {
    foreach ($f in $found) {
      Copy-Item $f.FullName -Destination $ArtDir -Force
      Write-Host "[grw-jm]   -> artifacts/$($f.Name) ($($f.Length) bytes)"
    }
    $lines += "$($r.Tag): $($found.Count) file(s), runtime ${mins}m"
  }
}

$report = @"
GRW JM-COST PAIR DONE
symbol      = XAUUSD.s (Just Markets real ticks — TRUE venue spread)
window      = 2021.04.01 -> 2026.07.01
deposit     = 20 USD | leverage 1:3000 | Model=4 real ticks
$($lines -join "`n")
"@
Set-Content -Path $Done -Value $report -Encoding UTF8
Write-Host ''
Write-Host $report -ForegroundColor Green
Write-Host "[grw-jm] sentinel: $Done"
