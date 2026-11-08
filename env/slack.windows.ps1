# Slack credentials for this Windows user. Fill the three values, then run:
#
#   pwsh -File .\env\slack.windows.ps1
#
# The script stores them in the user environment, which new processes inherit.
# Quit Grok Build and start it again after this script finishes. Do not commit
# the filled-in values.

$DesktopName = "grokbuildcli-desktop"
$AppToken = "xapp-paste-the-app-level-token"
$BotToken = "xoxb-paste-the-bot-token"

foreach ($pair in @(
    @{ Name = "SLACK_DESKTOP_NAME"; Value = $DesktopName },
    @{ Name = "SLACK_APP_TOKEN"; Value = $AppToken },
    @{ Name = "SLACK_BOT_TOKEN"; Value = $BotToken }
)) {
    [System.Environment]::SetEnvironmentVariable($pair.Name, $pair.Value, "User")
    Set-Item -Path "Env:$($pair.Name)" -Value $pair.Value
}

Write-Output "Saved SLACK_DESKTOP_NAME, SLACK_APP_TOKEN, and SLACK_BOT_TOKEN for this Windows user."
