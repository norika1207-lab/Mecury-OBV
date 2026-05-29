param(
  [switch]$SkipD3D
)

$ErrorActionPreference = "Continue"

function Step($Message) {
  Write-Host "[Mercury Baseline] $Message"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$benchDir = Join-Path $repoRoot "var\external-bench"
New-Item -ItemType Directory -Force -Path $benchDir | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$textPath = Join-Path $benchDir "winsat-no-mercury-$stamp.txt"
$jsonPath = Join-Path $benchDir "winsat-no-mercury-$stamp.json"

Step "Stopping Mercury resident services if WSL is available"
try {
  & wsl.exe -e bash -lc "cd /home/norika/Neuron-Mercury 2>/dev/null && node src/mercury.js product stop >/tmp/mercury-stop.log 2>&1 || true"
} catch {}

$system = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory
$cpu = Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
$gpu = $null
try {
  $gpu = & nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,power.draw,utilization.gpu --format=csv,noheader,nounits
} catch {}

"# no Mercury baseline $stamp" | Set-Content $textPath
"# system" | Add-Content $textPath
($system | ConvertTo-Json -Compress) | Add-Content $textPath
($cpu | ConvertTo-Json -Compress) | Add-Content $textPath
$gpu | Add-Content $textPath

$runs = @()
function Run-WinSat($Name, $WinSatArgs) {
  Step "Running winsat $Name"
  "# winsat $Name" | Add-Content $textPath
  $started = Get-Date
  $output = & winsat @WinSatArgs 2>&1
  $elapsed = ((Get-Date) - $started).TotalMilliseconds
  $output | Add-Content $textPath
  $script:runs += [pscustomobject]@{
    name = $Name
    args = $WinSatArgs
    elapsed_ms = [math]::Round($elapsed, 3)
    exit_code = $LASTEXITCODE
    output_tail = (($output | Select-Object -Last 24) -join "`n")
  }
}

Run-WinSat "cpuformal" @("cpuformal", "-xml", (Join-Path $benchDir "winsat-cpuformal-$stamp.xml"))
Run-WinSat "memformal" @("memformal", "-xml", (Join-Path $benchDir "winsat-memformal-$stamp.xml"))
Run-WinSat "diskformal" @("diskformal", "-xml", (Join-Path $benchDir "winsat-diskformal-$stamp.xml"))
if (-not $SkipD3D) {
  Run-WinSat "graphicsformal" @("graphicsformal", "-xml", (Join-Path $benchDir "winsat-graphicsformal-$stamp.xml"))
  Run-WinSat "d3d_dx10" @("d3d", "-dx10", "-xml", (Join-Path $benchDir "winsat-d3d-dx10-$stamp.xml"))
}

$report = [pscustomobject]@{
  schema = "mercury-windows-no-mercury-baseline-v1"
  created_at = (Get-Date).ToUniversalTime().ToString("o")
  mercury_mode = "stopped_before_benchmark"
  system = $system
  cpu = $cpu
  gpu = $gpu
  runs = $runs
  text_path = $textPath
  json_path = $jsonPath
}
$report | ConvertTo-Json -Depth 6 | Set-Content $jsonPath
Step "Baseline saved"
Write-Output $jsonPath
