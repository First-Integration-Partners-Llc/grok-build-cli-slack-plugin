# Handoff

Next session for this plugin. Start it with the working directory set to this repo:

```powershell
grok --cwd D:\Git\fipllc\grok-build-cli-slack-plugin
```

A running Grok session cannot change its working directory. `/cd` applies only to a new agent. The session that built this plugin is `server-admin` (`01a1bd1b-87b7-7cc1-8b0f-8470527c678e`) and stays at `D:\Git\fipllc`.

## Product

One Slack bot per Grok Build desktop. The person chooses the name at connect time, invites that bot, and the bot posts as itself. It does not post as the signed-in Slack user. The official Slack MCP plugin (`https://mcp.slack.com/mcp`) posts as the user. Leave that plugin off for this work.

A mention is `@desktop-name #session-title` plus the request. `#name` may be plain text or a Slack channel link `<#C…|name>`. Only the first tag is the session. A later `#other` stays in the prompt. A manual `/rename` wins over `generated_title`. Two sessions with the same title get a thread reply that lists `title — cwd`. The listener does not guess.

The prompt given to Grok starts with `From Slack:`, then `channel:` and `thread_ts:`, then the Slack text. The session posts `From @<bot> #<session> <answer>` in that thread. `:inbox_tray:` on the originating message is the routing receipt.

One listener per Grok CLI runtime. A renamed session is not in a channel until `@<bot> #<session> join` is posted there. `@here` delivers to those sessions on this runtime, except the session named on that line. Subscriptions are `~/.config/grok-build-cli-slack/subscriptions.json`. Bare `@here` needs the Slack app events `message.channels` and `message.groups`.

## Current code

Plugin `grok-slack` is `0.4.3`, MIT, author First-Integration-Partners-Llc. The listener behavior is `b414bc1`. This file is the commit after that. Marketplace name is `grok-build-cli-slack`. Origin is https://github.com/First-Integration-Partners-Llc/grok-build-cli-slack-plugin.git.

`scripts/listen.py` is the listener on Windows, macOS, and Linux. Python standard library only. No pip.

| Path | Role |
| --- | --- |
| `hooks/hooks.json` | `SessionStart` starts one detached listener and returns |
| `scripts/start_listener.ps1`, `scripts/start_listener.sh` | Hook entry points |
| `scripts/listen.ps1`, `scripts/listen.macos.sh`, `scripts/listen.linux.sh` | Foreground wrappers |
| `env/slack.windows.ps1`, `env/slack.macos.sh`, `env/slack.linux.sh` | Save tokens outside the repo, from CLI arguments |
| `slack-app-manifest.json` | Socket Mode manifest. `DESKTOP_NAME` is replaced when printed |

The hook command is PowerShell 7, then Windows PowerShell, then `sh`. It uses `||`. Windows PowerShell 5.1 cannot parse that. Those machines need PowerShell 7, or they run `scripts/listen.ps1` themselves.

`start_listener.py` probes `~/.config/grok-build-cli-slack/listener.lock` and releases it. The child `listen.py` holds the lock before it opens Slack. A second start prints `Slack listener already running.` and exits 0. Missing or wrong-prefix tokens exit 0 with a stderr line so SessionStart still succeeds. Missing Python exits 1.

## Delivery

Closed session, or open session whose last `turn_started` / `turn_ended` in `events.jsonl` is `turn_ended`: deliver now.

```text
grok --cwd <session cwd> -r <session id> -p <prompt> --output-format plain
```

Open session whose last marker is `turn_started`: the reply is still running. Save `~/.config/grok-build-cli-slack/held/<guid>.json` and post `That session is busy on this desktop. I will deliver this when it is free.`

Held files are scanned when the socket connects and every 15 seconds after that. Slack ping frames must not postpone the scan. A socket timeout never arrives while pings keep coming, so the scan is also on its own timer.

On Windows, `os.kill(pid, 0)` is Ctrl+C and returns WinError 87 for a live `grok.exe`. That is not a dead process. `pid_alive` uses `OpenProcess`. Access denied still counts as alive. `active_sessions.json` is one object or an array of `{session_id, pid, cwd}`.

If `grok` exits non-zero, or its output contains `has it open` or `not sent`, write the held file again and post the hold sentence. Otherwise delete the held file. The originating message already has `:inbox_tray:`.

`not_in_channel` means the bot is not in the channel. A failed `chat.postMessage` on the socket thread reconnects the socket. A failure inside a delivery thread is logged as `Delivery error` and does not reconnect. Do not post as the user to get around either case.

## This desktop

Verified on Windows only. macOS and Linux have the scripts. They were not run on those operating systems. `listen.linux.sh --self-test` was run under Git Bash on Windows.

- Desktop name: `grokcli-menashedesk`
- Slack app id: `A0CG27YRCQ4`
- `SLACK_APP_TOKEN` is the `xapp-` token at Basic Information → App-Level Tokens → `desktop-listener` (`connections:write`). It is not the Client ID, Client Secret, Signing Secret, or Verification Token.
- `SLACK_BOT_TOKEN` is the `xoxb-` Bot User OAuth Token.
- Tokens are in Windows User environment variables. Do not print them. Do not put them in the repo.
- Test channel: `#security-announcements` (`C0CFL3M093Q`). The bot is in that channel.
- Listener log: `~/.config/grok-build-cli-slack/listener.log`
- The listener process was started from this repo's `scripts/listen.py`, not from the installed plugin copy. It holds `listener.lock`. A SessionStart hook from the installed copy should see the lock and exit.
- The installed copy `grok-build-cli-slack-plugin-12c0302e` is older than `0.4.3`. After a pull, install again with `grok plugin install ./grok-build-cli-slack-plugin --trust`, then stop the repo listener so the next session starts the installed one. `grok plugin update grok-slack` does not refresh a second install that is shadowing this checkout. Uninstall by plugin name `grok-slack`, not by directory id.
- Do not read `listener.lock` while the listener is running. Another process holds a byte of it.

## What was verified

- `python scripts/listen.py --self-test` passes. It does not call Slack or `grok`. It covers the parser, title resolver, env quoting, the Windows pid check, a local masked WebSocket, ping frames not blocking the idle scan, and the lock.
- Socket Mode connected on this machine.
- A real mention of `#server-admin` was delivered into that open session after the session finished its reply. The text was `read the security announcement from Infrastructure and Security about Node.js`. The answer is in that session. It is not a pending task.
- Before the 15-second timer, a held mention sat for about 20 minutes because Slack pings kept the socket from looking idle. `b414bc1` fixes that.

## Do not

- Do not post as the signed-in Slack user.
- Do not store tokens or the temporary `wss://` URL in the repo or the log.
- Do not treat an open window as unable to take a prompt. Hold only while `events.jsonl` says the turn is still started.
- Do not use `os.kill(pid, 0)` on Windows to test whether `grok.exe` is alive.
- Do not commit `__pycache__`, `.env` files, or token values.
- Do not live-test `grok -r -p` against a session that is mid-reply. That interrupts the turn.
- Shell scripts in this repo are LF.

## Publish

Commit plugin changes and push them to `main` for review. Recent commits:

- `b414bc1` Scan held mentions every 15 seconds while Slack pings.
- `d89d6ce` Deliver into an open session that is waiting.
- `dc89b3d` Windows pid check. `os.kill(pid, 0)` was treating a live `grok.exe` as dead.
- `35ccbdf` Technical reference in the README.
- `0d03638` Listener starts with Grok on Windows, macOS, and Linux.
