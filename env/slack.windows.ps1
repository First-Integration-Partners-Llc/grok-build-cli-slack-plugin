# Save Slack credentials into this Windows user's environment.
# Pass the tokens on the command line. Do not paste them into this file.
#
#   pwsh -File .\env\slack.windows.ps1 `
#     -DesktopName "grokbuildcli-desktop" `
#     -AppToken "xapp-..." `
#     -BotToken "xoxb-..."
#
# Quit Grok Build and start it again after this script finishes.

param(
    [Parameter(Mandatory = $true)]
    [string] $DesktopName,
    [Parameter(Mandatory = $true)]
    [string] $AppToken,
    [Parameter(Mandatory = $true)]
    [string] $BotToken
)

$ErrorActionPreference = "Stop"

if ($AppToken -notlike "xapp-*") {
    throw "AppToken must be the desktop-listener Token and start with xapp-."
}
if ($BotToken -notlike "xoxb-*") {
    throw "BotToken must be the Bot User OAuth Token and start with xoxb-."
}

foreach ($pair in @(
    @{ Name = "SLACK_DESKTOP_NAME"; Value = $DesktopName.Trim() },
    @{ Name = "SLACK_APP_TOKEN"; Value = $AppToken.Trim() },
    @{ Name = "SLACK_BOT_TOKEN"; Value = $BotToken.Trim() }
)) {
    [System.Environment]::SetEnvironmentVariable($pair.Name, $pair.Value, "User")
    Set-Item -Path "Env:$($pair.Name)" -Value $pair.Value
}

Write-Output "Saved SLACK_DESKTOP_NAME, SLACK_APP_TOKEN, and SLACK_BOT_TOKEN for this Windows user."
