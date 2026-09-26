param()

$ErrorActionPreference = "Stop"
$scriptRoot = Split-Path -Parent $PSCommandPath
$pluginRoot = Split-Path -Parent $scriptRoot
$configPath = Join-Path $env:USERPROFILE ".codex-sidebar-laya\config.json"

$browserUseRoot = $env:SIDEBAR_LAYA_BROWSERUSE_ROOT
if (-not $browserUseRoot -and (Test-Path -LiteralPath $configPath)) {
  try { $browserUseRoot = (Get-Content -Raw -LiteralPath $configPath | ConvertFrom-Json).browserUseRoot } catch {}
}
if (-not $browserUseRoot) { $browserUseRoot = Join-Path $env:USERPROFILE "Documents\browseruse" }

$python = Join-Path $browserUseRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
  [Console]::Error.WriteLine("sidebar-laya: Jev/Laya runtime not found at $browserUseRoot. Run install.ps1 with -BrowserUseRoot.")
  exit 1
}

& $python (Join-Path $scriptRoot "mcp_server.py")
exit $LASTEXITCODE
