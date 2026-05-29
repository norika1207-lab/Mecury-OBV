param(
  [int]$DiskSeconds = 8,
  [string]$DiskSize = "256M",
  [string]$Model = "qwen2.5:7b",
  [switch]$SkipQwen
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Step($Message) {
  Write-Host "[Mercury Product Proof] $Message"
}

function Convert-LastJson($RawOutput) {
  $text = ($RawOutput | Out-String).Trim()
  $match = [regex]::Match($text, "(?s)\{.*\}\s*$")
  if (-not $match.Success) {
    throw "Command did not return a JSON object tail."
  }
  return $match.Value | ConvertFrom-Json
}

function Invoke-WslJson($Command) {
  $script = "$Command > /tmp/mercury-product-proof-json.json && base64 -w0 /tmp/mercury-product-proof-json.json"
  $encoded = (& wsl.exe -e bash -lc $script | Out-String).Trim()
  if (-not $encoded) {
    throw "WSL JSON command returned no base64 output."
  }
  $json = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($encoded))
  return $json | ConvertFrom-Json
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$benchDir = Join-Path $repoRoot "var\external-bench"
New-Item -ItemType Directory -Force -Path $benchDir | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")

Step "Suspending developer night runner; product proof measures installed low-impact runtime only"
try {
  & wsl.exe -e bash -lc "tmux kill-session -t mercury-night 2>/dev/null || true"
} catch {}

Step "Running no-Mercury DiskSpd baseline"
$noPath = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "windows-diskspd-baseline.ps1") -DurationSeconds $DiskSeconds -TestSize $DiskSize
$noPath = ($noPath | Select-Object -Last 1).Trim()

Step "Running with-Mercury low-impact DiskSpd"
$withPath = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "windows-diskspd-baseline.ps1") -DurationSeconds $DiskSeconds -TestSize $DiskSize -KeepMercury
$withPath = ($withPath | Select-Object -Last 1).Trim()

Step "Comparing foreground no-regression"
$compareJson = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "windows-diskspd-compare.ps1") -NoMercuryJson $noPath -WithMercuryJson $withPath
$compare = Convert-LastJson $compareJson

$qwen = $null
if (-not $SkipQwen) {
  Step "Running Qwen RTX 3060 cold-start proof in WSL"
  $qwen = Invoke-WslJson "cd /home/norika/Neuron-Mercury && node src/mercury.js bench-qwen-3060-cold-start --model='$Model' --json"
}

Step "Reading product status"
$status = Invoke-WslJson "cd /home/norika/Neuron-Mercury && node src/mercury.js product low-impact --json >/tmp/mercury-low-impact.log && node src/mercury.js product status --skip-heavy --json"

$proof = [pscustomobject]@{
  schema = "mercury-windows-product-proof-run-v1"
  created_at = (Get-Date).ToUniversalTime().ToString("o")
  pass = ($compare.pass -and $status.ok -and ($SkipQwen -or $qwen.pass))
  diskspd = $compare
  qwen = $qwen
  product_status = $status
  summary = [pscustomobject]@{
    diskspd_pass = $compare.pass
    diskspd_min_throughput_ratio = (($compare.rows | Measure-Object -Property throughput_ratio -Minimum).Minimum)
    diskspd_max_latency_ratio = (($compare.rows | Measure-Object -Property latency_ratio -Maximum).Maximum)
    qwen_first_request_speedup = $(if ($qwen) { $qwen.result.first_request_speedup } else { $null })
    qwen_cache_ms = $(if ($qwen) { $qwen.result.mercury_cache_ms } else { $null })
    product_ready = $status.readiness.ready
  }
}

$out = Join-Path $benchDir "windows-product-proof-$stamp.json"
$latest = Join-Path $benchDir "windows-product-proof-latest.json"
$proof | ConvertTo-Json -Depth 12 | Set-Content $out
if ($proof.pass -and -not $SkipQwen) {
  $proof | ConvertTo-Json -Depth 12 | Set-Content $latest
  try {
    $latestWslPath = (& wsl.exe -e wslpath -a $latest).Trim()
    $diskLatest = Join-Path $benchDir "diskspd-before-after-latest.json"
    $diskLatestWslPath = (& wsl.exe -e wslpath -a $diskLatest).Trim()
    & wsl.exe -e bash -lc "mkdir -p /home/norika/Neuron-Mercury/var/external-bench && cp '$latestWslPath' /home/norika/Neuron-Mercury/var/external-bench/windows-product-proof-latest.json && cp '$latestWslPath' /home/norika/Neuron-Mercury/var/external-bench/windows-product-proof-$stamp.json"
    & wsl.exe -e bash -lc "if [ -f '$diskLatestWslPath' ]; then cp '$diskLatestWslPath' /home/norika/Neuron-Mercury/var/external-bench/diskspd-before-after-latest.json; fi"
  } catch {}
} elseif ($SkipQwen) {
  Write-Warning "Qwen skipped; preserving previous full latest proof artifacts."
} else {
  Write-Warning "Proof failed; preserving previous latest proof artifacts."
}
$proof | ConvertTo-Json -Depth 12
if ($proof.pass) {
  exit 0
}
exit 1
