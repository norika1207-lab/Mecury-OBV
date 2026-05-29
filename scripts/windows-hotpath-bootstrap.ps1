param(
  [switch]$RunBench,
  [string]$Model = "qwen2.5:7b",
  [int]$Repeat = 3
)

$ErrorActionPreference = "Stop"

function Step($Message) {
  Write-Host "[Mercury] $Message"
}

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$wslRoot = "/home/norika/Neuron-Mercury"

Step "Checking WSL"
$wslVersion = & wsl.exe --status 2>$null
if ($LASTEXITCODE -ne 0) {
  throw "WSL is required for the Windows hot path. Install WSL first, then rerun this script."
}

Step "Resolving Windows repo path for WSL"
$windowsRoot = $repoRoot.Path
if ($windowsRoot -match '^([A-Za-z]):\\(.*)$') {
  $drive = $Matches[1].ToLowerInvariant()
  $rest = $Matches[2] -replace '\\', '/'
  $wslSource = "/mnt/$drive/$rest"
} else {
  $wslSource = (& wsl.exe wslpath -a "$windowsRoot").Trim()
}
if (-not $wslSource) {
  throw "Unable to resolve repo path inside WSL: $windowsRoot"
}

Step "Installing Mercury hot runtime into WSL ext4: $wslRoot"
$copyScript = @"
set -e
mkdir -p "$wslRoot/src" "$wslRoot/scripts" "$wslRoot/docs" "$wslRoot/var/bench"
cp "$wslSource/src/mercury.js" "$wslRoot/src/mercury.js"
cp "$wslSource/src/neurons.json" "$wslRoot/src/neurons.json"
cp "$wslSource/README.md" "$wslRoot/README.md"
cp "$wslSource/package.json" "$wslRoot/package.json"
if [ -d "$wslSource/scripts" ]; then cp "$wslSource/scripts/"*.sh "$wslRoot/scripts/" 2>/dev/null || true; cp "$wslSource/scripts/"*.py "$wslRoot/scripts/" 2>/dev/null || true; fi
cd "$wslRoot"
node --check src/mercury.js
node src/mercury.js windows-hotpath-plan --json
"@

& wsl.exe -e bash -lc $copyScript
if ($LASTEXITCODE -ne 0) {
  throw "Mercury WSL ext4 hotpath install failed."
}

if ($RunBench) {
  Step "Running RTX/Qwen before-after benchmark"
  & wsl.exe -e bash -lc "cd '$wslRoot' && node src/mercury.js bench-qwen-3060-demo --model='$Model' --repeat=$Repeat --json"
  if ($LASTEXITCODE -ne 0) {
    throw "Mercury RTX/Qwen benchmark failed."
  }
  Step "Running RTX/Qwen cold-start first-impression benchmark"
  & wsl.exe -e bash -lc "cd '$wslRoot' && node src/mercury.js bench-qwen-3060-cold-start --model='$Model' --json"
  if ($LASTEXITCODE -ne 0) {
    throw "Mercury RTX/Qwen cold-start benchmark failed."
  }
}

Step "Ready: Windows launcher can call WSL ext4 Mercury runtime."
