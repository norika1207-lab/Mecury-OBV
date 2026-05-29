param(
  [switch]$Compute
)

$ErrorActionPreference = "Stop"

function Step($Message) {
  Write-Host "[Geekbench Baseline] $Message"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$benchDir = Join-Path $repoRoot "var\external-bench"
New-Item -ItemType Directory -Force -Path $benchDir | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$jsonPath = Join-Path $benchDir "geekbench-no-mercury-$stamp.json"
$txtPath = Join-Path $benchDir "geekbench-no-mercury-$stamp.txt"

Step "Stopping Mercury resident services if WSL is available"
try {
  & wsl.exe -e bash -lc "cd /home/norika/Neuron-Mercury 2>/dev/null && node src/mercury.js product stop >/tmp/mercury-stop.log 2>&1 || true"
} catch {}

$candidates = @(
  "C:\Program Files\Geekbench 6\geekbench6.exe",
  "C:\Program Files\Geekbench 6\geekbench_x86_64.exe",
  "C:\Program Files (x86)\Geekbench 6\geekbench6.exe",
  "C:\Program Files (x86)\Geekbench 6\geekbench_x86_64.exe"
)
$exe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $exe) {
  $found = Get-ChildItem -Path "C:\Program Files","C:\Program Files (x86)",$env:LOCALAPPDATA -Filter "geekbench*.exe" -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($found) { $exe = $found.FullName }
}
if (-not $exe) {
  throw "Geekbench executable not found. Install with: winget install --id PrimateLabs.Geekbench.6"
}

$system = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory
$cpu = Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
$gpu = $null
try {
  $gpu = & nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,power.draw,utilization.gpu --format=csv,noheader,nounits
} catch {}

$args = @()
if ($Compute) { $args += "--compute" }
Step "Running Geekbench: $exe $($args -join ' ')"
$started = Get-Date
$output = & $exe @args 2>&1
$elapsed = ((Get-Date) - $started).TotalMilliseconds
$output | Set-Content $txtPath

$report = [pscustomobject]@{
  schema = "mercury-geekbench-no-mercury-baseline-v1"
  created_at = (Get-Date).ToUniversalTime().ToString("o")
  mercury_mode = "stopped_before_benchmark"
  executable = $exe
  args = $args
  elapsed_ms = [math]::Round($elapsed, 3)
  exit_code = $LASTEXITCODE
  system = $system
  cpu = $cpu
  gpu = $gpu
  output_path = $txtPath
  output = ($output -join "`n")
}
$report | ConvertTo-Json -Depth 6 | Set-Content $jsonPath
Write-Output $jsonPath
