param(
  [string]$BenchDir = "",
  [string]$NoMercuryJson = "",
  [string]$WithMercuryJson = "",
  [switch]$AllowFailedLatest
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
if (-not $BenchDir) {
  $BenchDir = Join-Path $repoRoot "var\external-bench"
}

function Latest-Json($Pattern) {
  Get-ChildItem -Path $BenchDir -Filter $Pattern |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
}

if (-not $NoMercuryJson) {
  $item = Latest-Json "diskspd-no-mercury-*.json"
  if ($item) { $NoMercuryJson = $item.FullName }
}
if (-not $WithMercuryJson) {
  $item = Latest-Json "diskspd-with-mercury-*.json"
  if ($item) { $WithMercuryJson = $item.FullName }
}
if (-not $NoMercuryJson -or -not (Test-Path $NoMercuryJson)) {
  throw "Missing no-Mercury DiskSpd JSON."
}
if (-not $WithMercuryJson -or -not (Test-Path $WithMercuryJson)) {
  throw "Missing with-Mercury DiskSpd JSON."
}

$no = Get-Content $NoMercuryJson -Raw | ConvertFrom-Json
$with = Get-Content $WithMercuryJson -Raw | ConvertFrom-Json

function Metrics-By-Name($Report) {
  $map = @{}
  foreach ($run in $Report.runs) {
    $metrics = $run.primary_metrics
    if (-not $metrics) {
      $totals = [regex]::Matches($run.output_tail, "total:\s+(?<bytes>\d+)\s+\|\s+(?<ios>\d+)\s+\|\s+(?<mib>[\d\.]+)\s+\|\s+(?<iops>[\d\.]+)\s+\|\s+(?<lat>[\d\.]+)")
      if ($totals.Count -gt 0) {
        $chosen = if ($run.name -like "*write*") { $totals[$totals.Count - 1] } else { $totals[0] }
        $metrics = [pscustomobject]@{
          mibps = [double]$chosen.Groups["mib"].Value
          iops = [double]$chosen.Groups["iops"].Value
          avg_latency_ms = [double]$chosen.Groups["lat"].Value
        }
      }
    }
    $map[$run.name] = $metrics
  }
  return $map
}

$noMap = Metrics-By-Name $no
$withMap = Metrics-By-Name $with
$lanes = @("seq_read", "seq_write", "rand_read_4k", "rand_write_4k")
$rows = @()
foreach ($lane in $lanes) {
  $a = $noMap[$lane]
  $b = $withMap[$lane]
  if (-not $a -or -not $b) { continue }
  $mibRatio = if ($a.mibps -gt 0) { [math]::Round($b.mibps / $a.mibps, 4) } else { 0 }
  $iopsRatio = if ($a.iops -gt 0) { [math]::Round($b.iops / $a.iops, 4) } else { 0 }
  $latRatio = if ($a.avg_latency_ms -gt 0) { [math]::Round($b.avg_latency_ms / $a.avg_latency_ms, 4) } else { 0 }
  $rows += [pscustomobject]@{
    lane = $lane
    no_mercury_mibps = $a.mibps
    with_mercury_mibps = $b.mibps
    throughput_ratio = $mibRatio
    no_mercury_iops = $a.iops
    with_mercury_iops = $b.iops
    iops_ratio = $iopsRatio
    no_mercury_latency_ms = $a.avg_latency_ms
    with_mercury_latency_ms = $b.avg_latency_ms
    latency_ratio = $latRatio
    pass = ($mibRatio -ge 0.90 -and $latRatio -le 1.25)
  }
}

$pass = ($rows.Count -gt 0 -and @($rows | Where-Object { -not $_.pass }).Count -eq 0)
$report = [pscustomobject]@{
  schema = "mercury-diskspd-before-after-v1"
  created_at = (Get-Date).ToUniversalTime().ToString("o")
  pass = $pass
  policy = "DiskSpd is not a Mercury acceleration lane; it is a foreground-no-regression gate."
  no_mercury_json = $NoMercuryJson
  with_mercury_json = $WithMercuryJson
  rows = $rows
}

$out = Join-Path $BenchDir ("diskspd-before-after-" + (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ") + ".json")
$latest = Join-Path $BenchDir "diskspd-before-after-latest.json"
$report | ConvertTo-Json -Depth 8 | Set-Content $out
if ($pass -or $AllowFailedLatest) {
  $report | ConvertTo-Json -Depth 8 | Set-Content $latest
} else {
  Write-Warning "DiskSpd compare failed; preserving previous diskspd-before-after-latest.json."
}
$report | ConvertTo-Json -Depth 8
