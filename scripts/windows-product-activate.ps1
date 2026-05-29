param(
  [string]$WslRepo = "/home/norika/Neuron-Mercury",
  [string]$BindHost = "127.0.0.1",
  [int]$Port = 17345
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

function Step($Message) {
  Write-Host "[Mercury Product Activate] $Message"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$productDir = Join-Path $repoRoot "var\product"
New-Item -ItemType Directory -Force -Path $productDir | Out-Null
$stamp = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")

function Write-FailedProof($Reason) {
  $failed = [pscustomobject]@{
    schema = "mercury-windows-product-activate-v1"
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    pass = $false
    elapsed_ms = 0
    reason = $Reason
    activation = $null
    summary = [pscustomobject]@{
      readiness_ready = $false
      readiness_checks = "0/0"
      qwen_first_request_speedup = 0
      qwen_cache_ms = 0
      diskspd_min_throughput_ratio = 0
      diskspd_max_latency_ratio = 0
      slow_worker_deferred = $false
    }
  }
  $out = Join-Path $productDir "windows-product-activate-$stamp.json"
  $latest = Join-Path $productDir "windows-product-activate-latest.json"
  $failed | ConvertTo-Json -Depth 10 | Set-Content $out
  $failed | ConvertTo-Json -Depth 10 | Set-Content $latest
  $failed | ConvertTo-Json -Depth 10
  exit 1
}

if (-not (Get-Command wsl.exe -ErrorAction SilentlyContinue)) {
  Write-FailedProof "wsl.exe not found"
}

& wsl.exe -e bash -lc "test -d '$WslRepo' && command -v node >/dev/null && test -f '$WslRepo/src/mercury.js'"
if ($LASTEXITCODE -ne 0) {
  Write-FailedProof "WSL Mercury repo or Node runtime not ready: $WslRepo"
}

Step "Activating WSL Mercury in low-impact product mode"
$started = Get-Date
$command = "cd '$WslRepo' && node src/mercury.js product activate --host=$BindHost --port=$Port --json"
$raw = & wsl.exe -e bash -lc $command
try {
  $activation = ($raw | Select-Object -Last 1) | ConvertFrom-Json
} catch {
  Write-FailedProof "product activate did not return parseable JSON"
}
$elapsedMs = [int]((Get-Date) - $started).TotalMilliseconds

$proof = [pscustomobject]@{
  schema = "mercury-windows-product-activate-v1"
  created_at = (Get-Date).ToUniversalTime().ToString("o")
  pass = [bool]($activation.ok -and $activation.readiness.ready -and $activation.proof.pass)
  elapsed_ms = $elapsedMs
  activation = $activation
  summary = [pscustomobject]@{
    readiness_ready = [bool]$activation.readiness.ready
    readiness_checks = "$(($activation.readiness.checks | Where-Object { $_.pass }).Count)/$($activation.readiness.checks.Count)"
    qwen_first_request_speedup = $activation.proof.metrics.qwen_first_request_speedup
    qwen_cache_ms = $activation.proof.metrics.qwen_cache_ms
    diskspd_min_throughput_ratio = $activation.proof.metrics.diskspd_min_throughput_ratio
    diskspd_max_latency_ratio = $activation.proof.metrics.diskspd_max_latency_ratio
    slow_worker_deferred = -not [bool](($activation.readiness.services | Where-Object { $_.name -eq "slow-worker" }).running)
  }
}

$out = Join-Path $productDir "windows-product-activate-$stamp.json"
$latest = Join-Path $productDir "windows-product-activate-latest.json"
$proof | ConvertTo-Json -Depth 14 | Set-Content $out
$proof | ConvertTo-Json -Depth 14 | Set-Content $latest

try {
  $latestWslPath = (& wsl.exe -e wslpath -a $latest).Trim()
  & wsl.exe -e bash -lc "mkdir -p '$WslRepo/var/product' && cp '$latestWslPath' '$WslRepo/var/product/windows-product-activate-latest.json'"
} catch {}

$proof | ConvertTo-Json -Depth 14
if ($proof.pass) {
  exit 0
}
exit 1
