# Listen for Slack mentions and hand them to a Grok Build session on this machine.
# Requires SLACK_APP_TOKEN (xapp-) and SLACK_BOT_TOKEN (xoxb-) in the process
# or user environment. See README.md.
#
#   pwsh -File ./scripts/listen.ps1
#   pwsh -File ./scripts/listen.ps1 -SelfTest

param(
    [switch] $SelfTest
)

$ErrorActionPreference = "Stop"

function Get-SlackEnv {
    param([Parameter(Mandatory = $true)][string] $Name)
    $value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($value)) {
        $value = [Environment]::GetEnvironmentVariable($Name, "User")
    }
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $null
    }
    return $value.Trim()
}

function ConvertTo-TitleKey {
    param([string] $Text)
    if ([string]::IsNullOrWhiteSpace($Text)) {
        return ""
    }
    return ([regex]::Replace($Text.ToLowerInvariant(), "[^a-z0-9]+", " ")).Trim()
}

function Get-MentionRequest {
    param([string] $Text)
    $source = if ($null -eq $Text) { "" } else { $Text }
    $source = [regex]::Replace($source, "<@[A-Z0-9]+>", " ")

    $chosen = $null
    foreach ($match in [regex]::Matches($source, "<#[A-Z0-9]+\|([^>]+)>|#([^\s#<>]+)")) {
        if (-not $chosen -or $match.Index -lt $chosen.Index) {
            $chosen = $match
        }
    }
    if (-not $chosen) {
        return $null
    }
    $tag = if ($chosen.Groups[1].Success -and $chosen.Groups[1].Value) { $chosen.Groups[1].Value } else { $chosen.Groups[2].Value }
    $rest = $source.Remove($chosen.Index, $chosen.Length)
    $rest = ([regex]::Replace($rest, "\s+", " ")).Trim()
    return @{ Tag = $tag; Prompt = $rest }
}

function Get-GrokSessions {
    $root = Join-Path $env:USERPROFILE ".grok\sessions"
    if (-not (Test-Path $root)) {
        return @()
    }
    $found = @()
    Get-ChildItem -Path $root -Recurse -Filter summary.json -File -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $summary = Get-Content -Raw -Path $_.FullName | ConvertFrom-Json
        } catch {
            return
        }
        $title = [string] $summary.generated_title
        $id = [string] $summary.info.id
        $cwd = [string] $summary.info.cwd
        if ([string]::IsNullOrWhiteSpace($title) -or [string]::IsNullOrWhiteSpace($id)) {
            return
        }
        $found += @{
            Id = $id
            Title = $title
            Key = (ConvertTo-TitleKey $title)
            Manual = [bool] $summary.title_is_manual
            Cwd = $cwd
        }
    }
    return $found
}

function Resolve-GrokSession {
    param(
        [string] $Tag,
        [array] $Sessions
    )
    $key = ConvertTo-TitleKey $Tag
    $matches = @($Sessions | Where-Object { $_.Key -eq $key })
    if ($matches.Count -eq 0) {
        return @{ Status = "none" }
    }
    $manual = @($matches | Where-Object { $_.Manual })
    if ($manual.Count -eq 1) {
        return @{ Status = "one"; Session = $manual[0] }
    }
    if ($manual.Count -gt 1) {
        return @{ Status = "many"; Sessions = $manual }
    }
    if ($matches.Count -eq 1) {
        return @{ Status = "one"; Session = $matches[0] }
    }
    return @{ Status = "many"; Sessions = $matches }
}

function Get-ActiveSessionIds {
    $path = Join-Path $env:USERPROFILE ".grok\active_sessions.json"
    if (-not (Test-Path $path)) {
        return @()
    }
    try {
        $rows = @(Get-Content -Raw -Path $path | ConvertFrom-Json)
    } catch {
        return @()
    }
    $live = @()
    foreach ($row in $rows) {
        if (-not $row.session_id) {
            continue
        }
        if (Get-Process -Id $row.pid -ErrorAction SilentlyContinue) {
            $live += [string] $row.session_id
        }
    }
    return $live
}

function Get-HeldDirectory {
    $dir = Join-Path $env:USERPROFILE ".config\grok-build-cli-slack\held"
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return $dir
}

function Save-HeldMessage {
    param(
        [string] $SessionId,
        [string] $Channel,
        [string] $ThreadTs,
        [string] $Prompt
    )
    $path = Join-Path (Get-HeldDirectory) ("{0}.json" -f [guid]::NewGuid())
    @{
        session_id = $SessionId
        channel = $Channel
        thread_ts = $ThreadTs
        prompt = $Prompt
    } | ConvertTo-Json | Set-Content -Path $path -Encoding utf8
}

function Send-SlackMessage {
    param(
        [string] $BotToken,
        [string] $Channel,
        [string] $ThreadTs,
        [string] $Text
    )
    $body = @{
        channel = $Channel
        text = $Text
        thread_ts = $ThreadTs
    } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "https://slack.com/api/chat.postMessage" -Headers @{ Authorization = "Bearer $BotToken" } -ContentType "application/json; charset=utf-8" -Body $body | Out-Null
}

function Start-SessionDelivery {
    param(
        [string] $BotToken,
        [hashtable] $Session,
        [string] $Channel,
        [string] $ThreadTs,
        [string] $Prompt,
        [string] $HeldPath
    )
    $grok = Get-Command grok -ErrorAction SilentlyContinue
    if (-not $grok) {
        throw "grok is not on PATH."
    }
    if ([string]::IsNullOrWhiteSpace($HeldPath)) {
        $HeldPath = Join-Path (Get-HeldDirectory) ("{0}.json" -f [guid]::NewGuid())
    }
    Start-Job -Name "slack-$($Session.Id)" -ScriptBlock {
        param($Grok, $Cwd, $Id, $Title, $Prompt, $Bot, $Channel, $Thread, $HeldPath)
        $output = & $Grok --cwd $Cwd -r $Id -p $Prompt --output-format plain 2>&1 | Out-String
        $code = $LASTEXITCODE
        $blocked = ($code -ne 0) -or ($output -match "has it open|not sent")
        $text = if ($blocked) {
            @{
                session_id = $Id
                channel = $Channel
                thread_ts = $Thread
                prompt = $Prompt
            } | ConvertTo-Json | Set-Content -Path $HeldPath -Encoding utf8
            "That session is open on this desktop. I will deliver this when it is free."
        } else {
            if (Test-Path $HeldPath) {
                Remove-Item -Force $HeldPath
            }
            "Delivered to $Title."
        }
        $body = @{ channel = $Channel; text = $text; thread_ts = $Thread } | ConvertTo-Json
        Invoke-RestMethod -Method Post -Uri "https://slack.com/api/chat.postMessage" -Headers @{ Authorization = "Bearer $Bot" } -ContentType "application/json; charset=utf-8" -Body $body | Out-Null
    } -ArgumentList $grok.Source, $Session.Cwd, $Session.Id, $Session.Title, $Prompt, $BotToken, $Channel, $ThreadTs, $heldPath | Out-Null
}

function Receive-SocketText {
    param($Socket, $OnIdle)
    $buffer = New-Object byte[] 16384
    $stream = New-Object System.IO.MemoryStream
    $pending = $null
    while ($true) {
        if (-not $pending) {
            $segment = [ArraySegment[byte]]::new($buffer)
            $pending = $Socket.ReceiveAsync($segment, [System.Threading.CancellationToken]::None)
        }
        if (-not $pending.Wait(15000)) {
            if ($OnIdle) {
                & $OnIdle
            }
            continue
        }
        $result = $pending.GetAwaiter().GetResult()
        $pending = $null
        if ($result.MessageType -eq [System.Net.WebSockets.WebSocketMessageType]::Close) {
            return $null
        }
        $stream.Write($buffer, 0, $result.Count)
        if ($result.EndOfMessage) {
            $text = [Text.Encoding]::UTF8.GetString($stream.ToArray())
            $stream.SetLength(0)
            return $text
        }
    }
}

function Send-SocketText {
    param($Socket, [string] $Text)
    $bytes = [Text.Encoding]::UTF8.GetBytes($Text)
    $segment = [ArraySegment[byte]]::new($bytes)
    $Socket.SendAsync($segment, [System.Net.WebSockets.WebSocketMessageType]::Text, $true, [System.Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
}

function Connect-SlackSocket {
    param([string] $AppToken)
    $opened = Invoke-RestMethod -Method Post -Uri "https://slack.com/api/apps.connections.open" -Headers @{ Authorization = "Bearer $AppToken" }
    if (-not $opened.ok) {
        throw "apps.connections.open failed: $($opened.error)"
    }
    $socket = [System.Net.WebSockets.ClientWebSocket]::new()
    $socket.ConnectAsync([Uri] $opened.url, [System.Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
    return $socket
}

function Deliver-HeldMessages {
    param([string] $BotToken)
    $dir = Get-HeldDirectory
    $active = Get-ActiveSessionIds
    $sessions = Get-GrokSessions
    Get-ChildItem -Path $dir -Filter "*.json" -File -ErrorAction SilentlyContinue | ForEach-Object {
        try {
            $held = Get-Content -Raw -Path $_.FullName | ConvertFrom-Json
        } catch {
            return
        }
        if ($active -contains [string] $held.session_id) {
            return
        }
        $session = $sessions | Where-Object { $_.Id -eq [string] $held.session_id } | Select-Object -First 1
        if (-not $session) {
            return
        }
        $running = @(Get-Job -Name "slack-$($session.Id)" -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Running" })
        if ($running.Count -gt 0) {
            return
        }
        Write-Output "Delivering held mention to $($session.Title)."
        Start-SessionDelivery -BotToken $BotToken -Session $session -Channel $held.channel -ThreadTs $held.thread_ts -Prompt $held.prompt -HeldPath $_.FullName
    }
}

if ($SelfTest) {
    $parsed = Get-MentionRequest "<@U123> #server-admin look at the token"
    if ($parsed.Tag -ne "server-admin" -or $parsed.Prompt -ne "look at the token") {
        throw "plain tag parse failed: $($parsed | ConvertTo-Json -Compress)"
    }
    $linked = Get-MentionRequest "<@U123> <#C123|Fix login bug> check the log"
    if ($linked.Tag -ne "Fix login bug" -or $linked.Prompt -ne "check the log") {
        throw "channel-link tag parse failed: $($linked | ConvertTo-Json -Compress)"
    }
    $kept = Get-MentionRequest "<@U123> #server-admin see #other"
    if ($kept.Prompt -ne "see #other") {
        throw "only the session tag should be removed"
    }
    if (Get-MentionRequest "<@U123> hello there") {
        throw "a mention without a session tag should not route"
    }
    $one = Resolve-GrokSession -Tag "fix-login-bug" -Sessions @(
        @{ Id = "a"; Title = "Fix login bug"; Key = (ConvertTo-TitleKey "Fix login bug"); Manual = $true; Cwd = "D:\one" },
        @{ Id = "b"; Title = "Fix login bug"; Key = (ConvertTo-TitleKey "fix-login-bug"); Manual = $false; Cwd = "D:\two" }
    )
    if ($one.Status -ne "one" -or $one.Session.Id -ne "a") {
        throw "manual title should win"
    }
    $many = Resolve-GrokSession -Tag "fix login bug" -Sessions @(
        @{ Id = "a"; Key = "fix login bug"; Manual = $true; Title = "Fix login bug"; Cwd = "D:\one" },
        @{ Id = "b"; Key = "fix login bug"; Manual = $true; Title = "Fix login bug"; Cwd = "D:\two" }
    )
    if ($many.Status -ne "many") {
        throw "two manual titles should stay ambiguous"
    }
    Write-Output "self-test ok"
    exit 0
}

$appToken = Get-SlackEnv "SLACK_APP_TOKEN"
$botToken = Get-SlackEnv "SLACK_BOT_TOKEN"
if ($appToken -notlike "xapp-*") {
    throw "SLACK_APP_TOKEN is missing. It is the desktop-listener Token and starts with xapp-."
}
if ($botToken -notlike "xoxb-*") {
    throw "SLACK_BOT_TOKEN is missing. It is the Bot User OAuth Token and starts with xoxb-."
}

Write-Output "Slack listener starting. Mentions route as @bot #session-title."
$flushHeld = { Deliver-HeldMessages -BotToken $botToken }.GetNewClosure()

while ($true) {
    $socket = $null
    try {
        $socket = Connect-SlackSocket -AppToken $appToken
        Write-Output "WebSocket connected."
        while ($socket.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
            $raw = Receive-SocketText -Socket $socket -OnIdle $flushHeld
            if ($null -eq $raw) {
                break
            }
            $message = $raw | ConvertFrom-Json
            if ($message.envelope_id) {
                Send-SocketText -Socket $socket -Text (@{ envelope_id = [string] $message.envelope_id } | ConvertTo-Json -Compress)
            }
            if ($message.type -eq "disconnect") {
                Write-Output "Slack asked the socket to reconnect."
                break
            }
            $event = $message.payload.event
            if (-not $event -and $message.payload.payload) {
                $event = $message.payload.payload.event
            }
            if ($event.type -ne "app_mention") {
                continue
            }
            $thread = if ($event.thread_ts) { $event.thread_ts } else { $event.ts }
            $request = Get-MentionRequest $event.text
            if (-not $request) {
                Send-SlackMessage -BotToken $botToken -Channel $event.channel -ThreadTs $thread -Text "Add a session tag, for example #server-admin, then the request."
                continue
            }
            if ([string]::IsNullOrWhiteSpace($request.Prompt)) {
                Send-SlackMessage -BotToken $botToken -Channel $event.channel -ThreadTs $thread -Text "Add the request after #$($request.Tag)."
                continue
            }
            $resolved = Resolve-GrokSession -Tag $request.Tag -Sessions (Get-GrokSessions)
            if ($resolved.Status -eq "none") {
                Send-SlackMessage -BotToken $botToken -Channel $event.channel -ThreadTs $thread -Text "No session on this desktop is named $($request.Tag)."
                continue
            }
            if ($resolved.Status -eq "many") {
                $lines = @($resolved.Sessions | ForEach-Object { "$($_.Title) — $($_.Cwd)" })
                Send-SlackMessage -BotToken $botToken -Channel $event.channel -ThreadTs $thread -Text ("More than one session matches. Rename one so the title is unique.`n" + ($lines -join "`n"))
                continue
            }
            $session = $resolved.Session
            $prompt = "From Slack:`n$($request.Prompt)"
            if ((Get-ActiveSessionIds) -contains $session.Id) {
                Save-HeldMessage -SessionId $session.Id -Channel $event.channel -ThreadTs $thread -Prompt $prompt
                Send-SlackMessage -BotToken $botToken -Channel $event.channel -ThreadTs $thread -Text "That session is open on this desktop. I will deliver this when it is free."
                continue
            }
            Write-Output "Delivering to $($session.Title)."
            Start-SessionDelivery -BotToken $botToken -Session $session -Channel $event.channel -ThreadTs $thread -Prompt $prompt
        }
    } catch {
        Write-Output "Listener error: $($_.Exception.Message)"
    } finally {
        if ($socket) {
            if ($socket.State -eq [System.Net.WebSockets.WebSocketState]::Open) {
                $socket.CloseAsync([System.Net.WebSockets.WebSocketCloseStatus]::NormalClosure, "reconnect", [System.Threading.CancellationToken]::None).GetAwaiter().GetResult() | Out-Null
            }
            $socket.Dispose()
        }
    }
    Start-Sleep -Seconds 5
}
