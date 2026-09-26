param([switch]$KeepLogs)

$ErrorActionPreference = "Continue"
& codex plugin remove "codex-sidebar-laya"
if ($LASTEXITCODE -ne 0) { Write-Warning "Codex could not remove the plugin automatically. Remove it from the Codex Plugins page." }

if (-not $KeepLogs) {
  $configDir = Join-Path $env:USERPROFILE ".codex-sidebar-laya"
  if (Test-Path -LiteralPath $configDir) { Remove-Item -LiteralPath $configDir -Recurse -Force }
}
Write-Host "Uninstalled. The source checkout was left untouched."
