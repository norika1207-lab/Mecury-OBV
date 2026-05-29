param(
  [int]$DurationSeconds = 20,
  [string]$TestSize = "512M",
  [switch]$KeepMercury,
  [string]$TargetDir = ""
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Step($Message) {
  Write-Host "[DiskSpd Baseline] $Message"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$benchDir = Join-Path $repoRoot "var\external-bench"
$toolDir = Join-Path $benchDir "tools\diskspd"
$neutralDir = if ($TargetDir) { $TargetDir } else { Join-Path $env:TEMP "NeuronMercuryBench" }
New-Item -ItemType Directory -Force -Path $benchDir,$toolDir,$neutralDir | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$modeSlug = if ($KeepMercury) { "with-mercury" } else { "no-mercury" }
$zipPath = Join-Path $toolDir "DiskSpd.zip"
$extractDir = Join-Path $toolDir "extracted"
$diskspd = Join-Path $extractDir "amd64\diskspd.exe"

if (-not (Test-Path $diskspd)) {
  Step "Downloading Microsoft DiskSpd"
  Invoke-WebRequest -Uri "https://aka.ms/getdiskspd" -OutFile $zipPath -UseBasicParsing
  if (Test-Path $extractDir) { Remove-Item -Recurse -Force $extractDir }
  Expand-Archive -Path $zipPath -DestinationPath $extractDir -Force
}

if ($KeepMercury) {
  Step "Keeping Mercury resident services running in low-impact mode"
  try {
    & wsl.exe -e bash -lc "cd /home/norika/Neuron-Mercury 2>/dev/null && node src/mercury.js product low-impact >/tmp/mercury-low-impact.log 2>&1 && node src/mercury.js resident start --low-impact >/tmp/mercury-resident-low-impact.log 2>&1 || true"
  } catch {}
} else {
  Step "Stopping Mercury resident services if WSL is available"
  try {
    & wsl.exe -e bash -lc "cd /home/norika/Neuron-Mercury 2>/dev/null && node src/mercury.js product stop >/tmp/mercury-stop.log 2>&1 || true"
  } catch {}
}

$target = Join-Path $neutralDir "diskspd-target.dat"
$jsonPath = Join-Path $benchDir "diskspd-$modeSlug-$stamp.json"
$txtPath = Join-Path $benchDir "diskspd-$modeSlug-$stamp.txt"

$system = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory
$cpu = Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors
$gpu = $null
try {
  $gpu = & nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,power.draw,utilization.gpu --format=csv,noheader,nounits
} catch {}

$runs = @()
function Parse-DiskSpdSectionTotal($Text, $SectionName) {
  $escaped = [regex]::Escape($SectionName)
  $sectionPattern = "(?s)$escaped\s*[\r\n]+.*?total:\s+\d+\s+\|\s+\d+\s+\|\s+(?<mib>[\d\.]+)\s+\|\s+(?<iops>[\d\.]+)\s+\|\s+(?<lat>[\d\.]+)"
  $match = [regex]::Match($Text, $sectionPattern)
  if (-not $match.Success) { return $null }
  return [pscustomobject]@{
    mibps = [double]$match.Groups["mib"].Value
    iops = [double]$match.Groups["iops"].Value
    avg_latency_ms = [double]$match.Groups["lat"].Value
  }
}

function Run-DiskSpd($Name, $DiskSpdArgs) {
  Step "Running $Name"
  $out = Join-Path $benchDir "diskspd-$Name-$stamp.txt"
  $started = Get-Date
  $text = & $diskspd @DiskSpdArgs $target 2>&1
  $elapsed = ((Get-Date) - $started).TotalMilliseconds
  $text | Set-Content $out
  $textBlob = ($text -join "`n")
  $readMetrics = Parse-DiskSpdSectionTotal $textBlob "Read IO"
  $writeMetrics = Parse-DiskSpdSectionTotal $textBlob "Write IO"
  $primaryMetrics = if ($Name -like "*write*") { $writeMetrics } else { $readMetrics }
  $script:runs += [pscustomobject]@{
    name = $Name
    args = $DiskSpdArgs
    elapsed_ms = [math]::Round($elapsed, 3)
    exit_code = $LASTEXITCODE
    output_path = $out
    primary_metrics = $primaryMetrics
    read_metrics = $readMetrics
    write_metrics = $writeMetrics
    output_tail = (($text | Select-Object -Last 36) -join "`n")
  }
}

Run-DiskSpd "seq_read" @("-c$TestSize", "-b1M", "-d$DurationSeconds", "-o4", "-t1", "-Sh", "-L", "-w0")
Run-DiskSpd "seq_write" @("-c$TestSize", "-b1M", "-d$DurationSeconds", "-o4", "-t1", "-Sh", "-L", "-w100")
Run-DiskSpd "rand_read_4k" @("-c$TestSize", "-b4K", "-r", "-d$DurationSeconds", "-o8", "-t2", "-Sh", "-L", "-w0")
Run-DiskSpd "rand_write_4k" @("-c$TestSize", "-b4K", "-r", "-d$DurationSeconds", "-o8", "-t2", "-Sh", "-L", "-w100")

$report = [pscustomobject]@{
  schema = "mercury-diskspd-external-benchmark-v2"
  created_at = (Get-Date).ToUniversalTime().ToString("o")
  mercury_mode = $(if ($KeepMercury) { "resident_running_before_benchmark" } else { "stopped_before_benchmark" })
  duration_seconds = $DurationSeconds
  test_size = $TestSize
  mode_slug = $modeSlug
  system = $system
  cpu = $cpu
  gpu = $gpu
  target = $target
  target_dir = $neutralDir
  runs = $runs
  json_path = $jsonPath
}
$report | ConvertTo-Json -Depth 6 | Set-Content $jsonPath
$report | ConvertTo-Json -Depth 6 | Set-Content $txtPath
Write-Output $jsonPath
