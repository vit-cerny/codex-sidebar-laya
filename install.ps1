param(
  [string]$BrowserUseRoot = "$env:USERPROFILE\Documents\browseruse",
  [switch]$SkipPluginInstall
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSCommandPath
$runtimePython = Join-Path $BrowserUseRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $runtimePython)) {
  throw "Jev/Laya runtime not found at $BrowserUseRoot. Install browseruse first, then rerun with -BrowserUseRoot."
}
if (-not (Test-Path -LiteralPath (Join-Path $BrowserUseRoot "models\laya-typed-decisions\model.safetensors"))) {
  throw "Laya model not found under $BrowserUseRoot\models\laya-typed-decisions."
}

$configDir = Join-Path $env:USERPROFILE ".codex-sidebar-laya"
New-Item -ItemType Directory -Force -Path $configDir | Out-Null
@{ browserUseRoot = (Resolve-Path -LiteralPath $BrowserUseRoot).Path } |
  ConvertTo-Json | Set-Content -LiteralPath (Join-Path $configDir "config.json") -Encoding utf8

if (-not $SkipPluginInstall) {
  & codex plugin marketplace add $repoRoot
  if ($LASTEXITCODE -ne 0) { throw "Could not add the local plugin marketplace." }
  & codex plugin add "codex-sidebar-laya@codex-sidebar-laya"
  if ($LASTEXITCODE -ne 0) { throw "Could not install the Codex plugin." }
}

Write-Host "Installed. Start a new Codex task and ask it to use Sidebar Laya Browser."
Write-Host "No API keys were copied or written. Optional Jev fallback reads TYPESAFE_API_KEY only from the existing Jev runtime environment."
