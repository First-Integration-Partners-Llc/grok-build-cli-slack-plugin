# grok-build-cli-slack-plugin

One Slack bot per Grok Build CLI install. You choose its name when you connect it, invite that bot into the channels it should hear, and it posts as itself.

A mention names the session:

```text
@grokbuildcli-desktop #fix-login-bug look at the token refresh
```

`grokbuildcli-desktop` is the name you chose for this desktop. `#fix-login-bug` is the session title. The desktop listener submits the rest of the message to that session. It starts with Grok Build on Windows, macOS, and Linux.

## What connects

The plugin follows the install, the same way this CLI stays signed in to your Grok account. It does not create a Slack app per session, and it does not post as your Slack user.

| Piece | Where it lives |
| --- | --- |
| Bot name | Chosen once, on this desktop |
| Membership | Invite `@that-name` into each channel |
| Listener | Starts with Grok Build on Windows, macOS, and Linux. Socket Mode, so no public URL |
| Route | Text after the mention: `#session-title` plus the prompt |

Slack also uses `#name` for a channel link. The listener accepts that form and the plain-text form, and uses the name either way.

Session titles are matched on this machine. A manual `/rename` wins over the generated title. Two sessions with the same title get a reply in the thread listing their directories. The listener does not pick one.

## Delivery

A session that is closed, or open and waiting for the next prompt, is given the Slack text as its prompt.

A session that is in the middle of a reply is left alone. The listener holds the message, says so in the thread, and delivers it when that reply finishes.

## Install

Socket Mode apps cannot be listed in the Slack Marketplace. Create this one in your own workspace. On Enterprise Grid it can be deployed to the org, and it still is not a Marketplace app.

### 1. Install the plugin

From a checkout of this repo:

```bash
grok plugin install ./grok-build-cli-slack-plugin --trust
```

Turn off the other plugin named `slack`. That one posts as the signed-in user.

### 2. Print the manifest

Pick the name people will invite, such as `grokbuildcli-desktop`. Slack keeps 35 characters of the app name and 80 of the bot display name.

macOS or Linux, with `python3` on `PATH`:

```bash
./scripts/desktop-manifest.sh grokbuildcli-desktop
```

Windows:

```powershell
./scripts/desktop-manifest.ps1 -DesktopName "grokbuildcli-desktop"
```

Either script also reads `SLACK_DESKTOP_NAME` when you omit the name. Copy the printed JSON.

### 3. Create the app and turn on the WebSocket

Slack's guide is [Using Socket Mode](https://docs.slack.dev/apis/events-api/using-socket-mode). The manifest already sets `socket_mode_enabled` and `is_hosted` to false, and it subscribes the bot to `app_mention`.

1. Open [api.slack.com/apps](https://api.slack.com/apps?new_app=1) and choose **From a manifest**.
2. Pick the workspace where this desktop should appear. Paste the JSON. Create the app.
3. Open **Socket Mode** in the sidebar. Slack tells you the app uses a WebSocket and does not need a public Request URL. **Enable Socket Mode** must be on. The manifest turns it on. If the page asks you to generate a token before the switch will stay on, do the next step and come back.
4. Open **Basic Information**. The top of that page lists **App ID**, **Client ID**, **Client Secret**, **Signing Secret**, and **Verification Token**. None of those is the WebSocket token. Scroll to **App-Level Tokens**. The row named `desktop-listener` is the token. Open it. The field labeled **Token** starts with `xapp-`. Slack does not label it `APP_TOKEN`. Copy that **Token** into `SLACK_APP_TOKEN`. Its scopes should include `connections:write` (route interactions and event payloads over WebSockets). `authorizations:read` may be listed next to it. That extra scope is fine. If `desktop-listener` is missing, use **Generate Token and Scopes**, name it `desktop-listener`, add `connections:write`, and copy the **Token** before you close the dialog.
5. Open **Event Subscriptions**. With Socket Mode on, Slack does not ask for a Request URL. Leave that field empty. Confirm the bot event `app_mention` is listed, and that the page is turned on. Save if Slack shows **Save Changes**.
6. Open **OAuth & Permissions** and confirm the bot token scopes from the manifest are present. Click **Install to Workspace** and allow it. Copy the **Bot User OAuth Token**. It starts with `xoxb-`. This token is not the app-level token. Installing does not replace `xapp-`.
7. Do not add a user token scope. This bot posts as itself.

Reinstall the app from **OAuth & Permissions** if you add a scope later. The old `xoxb-` value stops matching the new scopes. The `xapp-` token stays valid across that reinstall.

Events arrive only while this desktop holds the WebSocket. Slack does not keep them on an HTTP URL for later. The WebSocket address itself changes. The listener asks for a new one with `SLACK_APP_TOKEN`. You do not paste a `wss://` URL anywhere.

### 4. Save the credentials

Three variables:

| Variable | Value |
| --- | --- |
| `SLACK_DESKTOP_NAME` | The invite name, such as `grokbuildcli-desktop` |
| `SLACK_APP_TOKEN` | The **Token** on the `desktop-listener` app-level token. It starts with `xapp-`. Not the Client Secret. |
| `SLACK_BOT_TOKEN` | The `xoxb-` bot token from **Install App** |

Pass the two tokens on the command line. Do not paste them into a file in this repository. The scripts reject an app token that does not start with `xapp-` and a bot token that does not start with `xoxb-`.

macOS:

```bash
./env/slack.macos.sh \
  --desktop-name grokbuildcli-desktop \
  --app-token 'xapp-...' \
  --bot-token 'xoxb-...'
```

The script writes `~/.config/grok-build-cli-slack.env` with mode `600`, adds one `source` line to `~/.zprofile`, and runs `launchctl setenv` so Grok Build started from the Dock can see the variables. Quit Grok Build and open it again. The command can remain in the shell history on this Mac. It is not a file in this repo.

Linux:

```bash
./env/slack.linux.sh \
  --desktop-name grokbuildcli-desktop \
  --app-token 'xapp-...' \
  --bot-token 'xoxb-...'
```

The script writes the same env file under your home directory and adds one `source` line to `~/.profile`. If `~/.bashrc` does not source `~/.profile`, add that line there too. Start Grok Build from a new login session.

Windows:

```powershell
pwsh -File .\env\slack.windows.ps1 `
  -DesktopName "grokbuildcli-desktop" `
  -AppToken "xapp-..." `
  -BotToken "xoxb-..."
```

That stores the three variables in the Windows user environment. Quit Grok Build and start it again.

### 5. Invite the bot

In each channel it should hear, run:

```text
/invite @grokbuildcli-desktop
```

Use the display name Slack shows if it shortened the one you chose. A mention in a channel the bot has not joined does not arrive.

## Listener

Installing the plugin with `--trust` registers a `SessionStart` hook. The next time Grok Build starts, or reopens a saved session, that hook starts the listener and returns. One listener runs per machine. A second session sees that it is already running.

The hook needs `python3` or `python` on `PATH`. Nothing is installed from pip. On Windows the hook command uses `||`, which PowerShell 7 understands. Grok uses PowerShell 7 when `pwsh` is installed. Windows PowerShell 5.1 does not understand `||`; install PowerShell 7, or start the listener yourself with the script below.

The listener reads `SLACK_APP_TOKEN` and `SLACK_BOT_TOKEN` from the process environment, the Windows user environment, or `~/.config/grok-build-cli-slack.env`. Its log is `~/.config/grok-build-cli-slack/listener.log`.

You can also leave a listener in a terminal. macOS:

```bash
./scripts/listen.macos.sh
```

Linux:

```bash
./scripts/listen.linux.sh
```

Windows:

```powershell
pwsh -File ./scripts/listen.ps1
```

A mention `@your-bot #session-title` followed by the request is delivered to that session. An open session that is waiting for a prompt gets it immediately. A session that is mid-reply gets it when that reply finishes.

These check the mention parser without connecting to Slack:

```bash
./scripts/listen.macos.sh --self-test
./scripts/listen.linux.sh --self-test
```

```powershell
pwsh -File ./scripts/listen.ps1 -SelfTest
```

`python listen.py --self-test` is the same check. It does not call Slack or `grok`.

## Technical reference

Plugin name `grok-slack`, marketplace name `grok-build-cli-slack`, MIT, author First-Integration-Partners-Llc. The name is not `slack`, so it does not replace the official plugin. That official plugin posts as the signed-in user. This one does not. There is no `.mcp.json` and no user token.

Grok Build's own "bring to Slack" app creation is not available to this CLI. Each desktop creates and installs its own Socket Mode app. One app is one bot user. Session titles are mention tags, not extra Slack users.

### Layout

| Path | Role |
| --- | --- |
| `.grok-plugin/plugin.json` | Plugin manifest |
| `.grok-plugin/marketplace.json` | Local marketplace, source `"."` |
| `hooks/hooks.json` | `SessionStart` hook |
| `slack-app-manifest.json` | Slack app manifest. `DESKTOP_NAME` is replaced when you print it |
| `scripts/listen.py` | The listener. Standard library only |
| `scripts/start_listener.py` | Detaches one listener and exits |
| `scripts/start_listener.ps1`, `scripts/start_listener.sh` | Hook entry points. PowerShell looks up `python`, then `python3`, then `py -3`. The shell script looks up `python3`, then `python` |
| `scripts/listen.ps1`, `scripts/listen.macos.sh`, `scripts/listen.linux.sh` | Foreground wrappers around `listen.py` |
| `scripts/desktop-manifest.ps1`, `scripts/desktop-manifest.sh` | Print the manifest. The shell script needs `python3` |
| `env/slack.windows.ps1`, `env/slack.macos.sh`, `env/slack.linux.sh` | Store credentials outside this repo |
| `skills/slack/`, `skills/slack-setup/` | Skills loaded with the plugin |

Hooks run from the installed copy. After you pull, install again:

```bash
grok plugin install ./grok-build-cli-slack-plugin --trust
```

`grok plugin update grok-slack` refreshes a local install that Grok is already reading from this checkout. A listener that is already running keeps the process it started in. Stop that process and the next session start launches the updated one. `--trust` is required. Without it the skills and the hook stay inactive.

`SessionStart` runs when a session starts and when a saved session is reopened. It does not run for a subagent session, and compaction does not run it. The session that was already open when you installed the plugin does not run the hook until that session starts again.

### Start hook

`hooks/hooks.json` sets a 15 second timeout. The default is 5. A hook field named `async` is ignored, so the listener cannot be the hook process. The hook command is:

```text
pwsh -NoProfile -ExecutionPolicy Bypass -File "${GROK_PLUGIN_ROOT}/scripts/start_listener.ps1" 2>/dev/null || powershell -NoProfile -ExecutionPolicy Bypass -File "${GROK_PLUGIN_ROOT}/scripts/start_listener.ps1" 2>/dev/null || sh "${GROK_PLUGIN_ROOT}/scripts/start_listener.sh"
```

Grok expands `${GROK_PLUGIN_ROOT}` to the installed plugin directory. On Windows it rewrites that variable for PowerShell. The `||` form is valid in `sh` and in PowerShell 7. Grok runs hook commands under PowerShell 7 when `pwsh` is on `PATH`, then Windows PowerShell 5.1, then Git Bash. Windows PowerShell 5.1 does not parse `||`. Install PowerShell 7, or run `scripts/listen.ps1` yourself.

`start_listener.py` loads saved credentials, then probes `~/.config/grok-build-cli-slack/listener.lock` and releases it. A probe that cannot take the lock prints `Slack listener already running.` and exits 0. A missing token, or a token with the wrong prefix, prints `Slack listener not started. Set SLACK_APP_TOKEN and SLACK_BOT_TOKEN.` on stderr and exits 0, so a session still starts before Slack setup is finished. When the probe succeeds and both tokens are present, it starts `listen.py` with the same Python and `-u`, stdin closed, and stdout and stderr appended to `listener.log`, then exits. The parent does not hold the lock. On Windows the child is a detached process in a new process group with no console window. On macOS and Linux it is a new session and does not inherit extra file descriptors.

`listen.py` takes that lock before it opens Slack. The lock is `fcntl` on macOS and Linux, and one locked byte on Windows. The file then contains the listener pid. If the lock is already held, that process prints `Slack listener already running.` and exits 0. Two starters can both pass the probe before either child locks. The second child exits, so only one socket stays up.

The starter scripts exit 1 when no Python is on `PATH`. That failure shows up on the session start. The listener itself does not.

### Credentials

Nothing in this repository is a place to put a token. The env scripts take them as arguments and reject an app token that does not start with `xapp-` or a bot token that does not start with `xoxb-`.

Lookup order when the listener starts:

1. The process environment.
2. On Windows, the user environment (`HKCU\Environment`), if the process does not already have the variable.
3. `~/.config/grok-build-cli-slack.env` for any of the three names that are still empty.

The env file is `export KEY='value'` with mode `600`. A single quote inside a value is written as `'\''`. macOS also appends `source` of that file to `~/.zprofile` and calls `launchctl setenv`, which is what a Dock-launched Grok Build sees after you quit and reopen it. Linux appends the same `source` line to `~/.profile`. Windows writes the user environment. A Grok Build process that was already running does not see a user-environment change until it is started again. The listener still reads the registry and the env file itself, so a hook-started process can see them.

`SLACK_APP_TOKEN` is the **Token** field on Basic Information → App-Level Tokens → `desktop-listener`. Scope `connections:write` is an app-level scope. It is not one of the bot OAuth scopes. `authorizations:read` on that same token is fine. Client ID, Client Secret, Signing Secret, and Verification Token are not this value. `SLACK_BOT_TOKEN` is the Bot User OAuth Token from OAuth & Permissions. Reinstalling the app after a scope change replaces `xoxb-` only.

### Socket Mode

`slack-app-manifest.json` sets `socket_mode_enabled` true, `is_hosted` false, `org_deploy_enabled` false, and `token_rotation_enabled` false. The only bot event is `app_mention`. There is no request URL and no user scope. Bot scopes are `app_mentions:read`, `chat:write`, `channels:history`, `channels:read`, `groups:history`, `groups:read`, `im:history`, `im:read`, `mpim:history`, `mpim:read`, `reactions:read`, `reactions:write`, and `users:read`.

The listener posts `https://slack.com/api/apps.connections.open` with `Authorization: Bearer` and the app token. Slack returns a one-time `wss://` URL. That URL is not written to the log or to a file. The client speaks a small masked WebSocket. It answers ping frames. Any message with `envelope_id` is acknowledged with `{"envelope_id":"..."}` before the mention is handled. A `disconnect` message, a closed socket, or an error closes the socket and waits 5 seconds, then opens a new one. Slack does not queue events for the time the socket is down.

Only `app_mention` is routed. The thread is `thread_ts` when Slack sends one, otherwise `ts`. Replies use `chat.postMessage` with the bot token and that `thread_ts`.

### Mention and session match

The bot mention `<@U...>` is removed. The session tag is the first `#name` or the first channel link `<#C...|name>`. Only that span is removed, so a later `#other` stays in the prompt. A mention with no tag is answered with `Add a session tag, for example #server-admin, then the request.` A tag with an empty request is answered with `Add the request after #<tag>.`

Titles come from `~/.grok/sessions/**/summary.json`: `generated_title`, `title_is_manual`, `info.id`, and `info.cwd`. The title string is `generated_title` even when `/rename` set it. A row with no title or no id is skipped. Matching lowercases the text and turns every run of non-alphanumeric characters into a single space, so `#fix-login-bug` matches `Fix login bug`.

One manual `/rename` wins over generated titles with the same key. Two manual titles with that key are ambiguous. With no manual title, one generated match is used, and two are ambiguous. An ambiguous reply does not pick one. It posts `More than one session matches. Rename one so the title is unique.` and then one line per match, `title — cwd`. No match posts `No session on this desktop is named <tag>.` The tag text is used as stored, without an extra `#`.

### Delivery

An open session is one whose id is in `~/.grok/active_sessions.json` and whose `pid` is still alive. That file is one object or an array of `{session_id, pid, cwd}`. On Windows the check opens the process. `os.kill(pid, 0)` is a Ctrl+C event there, and a live `grok.exe` returns "The parameter is incorrect." Access denied still counts as alive. The session is busy only when the last `turn_started` or `turn_ended` line in its `events.jsonl` is `turn_started`. An open session whose last turn has ended is waiting, and the mention is delivered into that window. A busy session is held. The listener writes `~/.config/grok-build-cli-slack/held/<guid>.json` and replies `That session is busy on this desktop. I will deliver this when it is free.`

Each held file is one message:

```json
{"session_id": "", "channel": "", "thread_ts": "", "prompt": ""}
```

The prompt stored there, and the prompt passed to Grok, is the Slack text prefixed with `From Slack:` and a newline.

A waiting session, open or closed, is given the prompt in the background:

```text
grok --cwd <session cwd> -r <session id> -p <prompt> --output-format plain
```

The socket loop does not wait for that process. Delivery runs on a daemon thread, and a session id already in that set is not started again. If the exit code is not 0, or the output contains `has it open` or `not sent`, the held file is written again and the hold sentence is posted. Otherwise the held file is deleted and the thread gets `Delivered to <title>.` Held files are scanned when the socket connects and on every 15 seconds of idle. A session that is still mid-reply, or that already has a delivery thread running, is skipped in that scan, and its held file stays until that delivery finishes. A new mention that arrives while a delivery thread is already running for that session is not written to a held file.

`not_in_channel` means the bot has not been invited. A failed `chat.postMessage` on the socket thread is logged and the socket reconnects. A failure inside a delivery thread is logged as `Delivery error` and does not reconnect the socket. The listener does not post as your user.

## License

MIT. See `LICENSE`.
