param(
    [Parameter(Mandatory = $true)]
    [string] $DesktopName,
    [string] $ManifestPath
)

$ErrorActionPreference = "Stop"

if (-not $ManifestPath) {
    $ManifestPath = Join-Path $PSScriptRoot "..\slack-app-manifest.json"
}

$appName = $DesktopName.Trim()
if ($appName.Length -gt 35) {
    $appName = $appName.Substring(0, 35).TrimEnd()
}
$botName = $DesktopName.Trim()
if ($botName.Length -gt 80) {
    $botName = $botName.Substring(0, 80).TrimEnd()
}

$manifest = Get-Content -Raw -Path $ManifestPath | ConvertFrom-Json
$manifest.display_information.name = $appName
$manifest.features.bot_user.display_name = $botName
$manifest | ConvertTo-Json -Depth 8
