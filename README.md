# grok-build-cli-slack-plugin

Each Grok Build CLI session joins Slack as its own bot. The bot's name is the session title. Someone invites it into a channel, and it posts there as itself.

This is the Grok Bot path where a Bot has its own Slack app, named after the Bot, and you `/invite` it. It is not the other Slack connection, the one that posts as your user. That one is what Claude uses, and this plugin does not do that.

## How a session shows up

Slack gives one app one bot user. A name you can invite is a bot user, so each session is its own Slack app.

1. Take the session title (`/rename`, or the generated title).
2. Build a manifest with that name:

```powershell
./scripts/session-manifest.ps1 -SessionName "Fix login bug"
```

The app name is trimmed to 35 characters. The bot display name is trimmed to 80.

3. Create an internal app from that JSON: [api.slack.com/apps](https://api.slack.com/apps?new_app=1), **From a manifest**.
4. Install it and keep the bot token out of git:

```powershell
$env:SLACK_BOT_TOKEN = "xoxb-..."
```

5. In the channel, invite it: `/invite @Fix login bug`.

Until the invite, Slack answers `not_in_channel`. The session does not post under your name to get around that.

Grok Bot creates the app from its own servers when you choose **Bring to your team's Slack**. That API is not offered to this CLI. A workspace that reviews new apps shows the same approval wait Grok Bot shows. One session, one app, one invite list.

## Install the plugin

```bash
grok plugin install ./grok-build-cli-slack-plugin --trust
```

Turn off the other plugin named `slack`. Its server posts as the signed-in user.

## Layout

| Path | Role |
| --- | --- |
| `slack-app-manifest.json` | Bot-user manifest. `SESSION_NAME` is replaced with the session title |
| `scripts/session-manifest.ps1` | Prints the manifest for one session |
| `skills/slack-setup/` | Creates this session's bot |
| `skills/slack/` | Posts with the bot token only |

## License

MIT. See `LICENSE`.
