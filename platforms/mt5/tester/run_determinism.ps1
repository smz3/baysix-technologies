# FOB emitter DETERMINISM GATE runner (task 198).
# Runs the SAME tester .ini TWICE on real ticks and asserts the two
# fob_capture_*.csv are byte-identical (md5). Replaces the manual
# copy-aside / re-run / md5 dance. JM terminal MUST be closed first
# ([[brc_headless_tester_fires]] — headless tester fires only with no
# terminal64 already running).
#
# Usage:
#   powershell -NoProfile -File mt5\tester\run_determinism.ps1
#   powershell -NoProfile -File mt5\tester\run_determinism.ps1 -Config <abs .ini> -Glob 'fob_capture_*dukas*v1.24*'

param(
  [string]$Term   = 'C:\Program Files\JustMarkets MetaTrader 5\terminal64.exe',
  [string]$Config = 'C:\Users\User\Desktop\baysix-technologies\mt5\tester\fob_ticks_determinism.ini',
  [string]$Common = "$env:APPDATA\MetaQuotes\Terminal\Common\Files\FOB",
  [string]$Glob   = 'fob_capture_*dukas*'   # newest match after each run is the capture
)

$ErrorActionPreference = 'Stop'

if (Get-Process terminal64 -ErrorAction SilentlyContinue) {
  Write-Error 'terminal64 is already running — headless tester will not fire. Close it and retry.'; exit 2
}
if (-not (Test-Path $Term))   { Write-Error "terminal not found: $Term"; exit 2 }
if (-not (Test-Path $Config)) { Write-Error "config not found: $Config"; exit 2 }

function Invoke-TesterRun([int]$n) {
  Write-Host "[det] launching run $n ..."
  Start-Process -FilePath $Term -ArgumentList "/config:$Config" -Wait
  $csv = Get-ChildItem -Path $Common -Filter $Glob -File |
         Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if (-not $csv) { Write-Error "run ${n}: no capture matching '$Glob' in $Common"; exit 3 }
  Write-Host ("[det] run {0} -> {1} ({2:N0} bytes)" -f $n, $csv.Name, $csv.Length)
  return $csv.FullName
}

# Run 1 -> snapshot aside (next run reuses the same filename, so copy now)
$out1 = Invoke-TesterRun 1
$save = Join-Path $Common '_det_run1.csv'
Copy-Item $out1 $save -Force
Remove-Item $out1 -Force            # clear so run 2 is unambiguous

# Run 2
$out2 = Invoke-TesterRun 2

$h1 = (Get-FileHash $save -Algorithm MD5).Hash
$h2 = (Get-FileHash $out2 -Algorithm MD5).Hash
Write-Host ''
Write-Host "run1 md5 = $h1"
Write-Host "run2 md5 = $h2"
if ($h1 -eq $h2) {
  Write-Host '[det] PASS — byte-identical across two runs (deterministic).' -ForegroundColor Green
  exit 0
} else {
  Write-Host '[det] FAIL — captures differ. NON-DETERMINISTIC emitter.' -ForegroundColor Red
  exit 1
}
