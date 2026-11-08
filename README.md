# grok-build-cli-slack-plugin

One Slack bot per Grok Build CLI install. You choose its name when you connect it, invite that bot into the channels it should hear, and it posts as itself.

A mention names the session:

```text
@grokbuildcli-desktop #fix-login-bug look at the token refresh
```

`grokbuildcli-desktop` is the name you chose for this desktop. `#fix-login-bug` is the session title. The desktop listener submits the rest of the message to that session.

## What connects

The plugin follows the install, the same way this CLI stays signed in to your Grok account. It does not create a Slack app per session, and it does not post as your Slack user.

| Piece | Where it lives |
| --- | --- |
| Bot name | Chosen once, on this desktop |
| Membership | Invite `@that-name` into each channel |
| Listener | Socket Mode on this machine, so no public URL |
| Route | Text after the mention: `#session-title` plus the prompt |

Slack also uses `#name` for a channel link. The listener accepts that form and the plain-text form, and uses the name either way.

Session titles are matched on this machine. A manual `/rename` wins over the generated title. Two sessions with the same title get a reply in the thread listing their directories. The listener does not pick one.

## Delivery

A session that is not open is resumed and given the Slack text as its prompt.

A session that is already open in a Grok window cannot be opened a second time, and Grok does not accept the text into that window. The listener holds the message, says so in the thread, and delivers it when the session is free.

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
4. Generate the app-level token. The Socket Mode page offers this when you enable it. The same control is **Basic Information → App-level tokens → Generate Token and Scopes**. Name it `desktop-listener`. Add the scope `connections:write`. That scope is what lets the app call [`apps.connections.open`](https://docs.slack.dev/reference/methods/apps.connections.open) and open a WebSocket. Generate, then copy the value that starts with `xapp-`. Slack shows a new token's secret at creation. Store it before you close the dialog.
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
| `SLACK_APP_TOKEN` | The `xapp-` app-level token with `connections:write` |
| `SLACK_BOT_TOKEN` | The `xoxb-` bot token from **Install App** |

Put the real values into the file for this machine. Do not commit that edit.

macOS. Edit `env/slack.macos.sh`, then load it for login shells:

```bash
echo "source $(pwd)/env/slack.macos.sh" >> ~/.zprofile
source ./env/slack.macos.sh
```

A Grok Build process started from the Dock does not read `~/.zprofile`. The comments in `env/slack.macos.sh` have the `launchctl setenv` lines for that case. Run them once, then quit and reopen Grok Build.

Linux. Edit `env/slack.linux.sh`, then load it for login shells:

```bash
echo "source $(pwd)/env/slack.linux.sh" >> ~/.profile
source ./env/slack.linux.sh
```

If `~/.bashrc` does not source `~/.profile`, add the same `source` line there too. Start Grok Build from a new login session.

Windows. Edit the three values at the top of `env/slack.windows.ps1`, then:

```powershell
pwsh -File .\env\slack.windows.ps1
```

That writes them into the Windows user environment and into the current PowerShell process. Quit Grok Build and start it again so it inherits the user environment.

### 5. Invite the bot

In each channel it should hear, run:

```text
/invite @grokbuildcli-desktop
```

Use the display name Slack shows if it shortened the one you chose. A mention in a channel the bot has not joined does not arrive.

## License

MIT. See `LICENSE`.
