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

## Create the bot

`slack-app-manifest.json` is the bot for this desktop. Replace `DESKTOP_NAME` with the name you want to invite, then create an internal app from that JSON at [api.slack.com/apps](https://api.slack.com/apps?new_app=1). Install it, invite it, and keep the bot token and the Socket Mode app token out of git.

```powershell
./scripts/desktop-manifest.ps1 -DesktopName "grokbuildcli-desktop"
```

The app name is trimmed to 35 characters. The bot display name is trimmed to 80.

## Install the plugin

```bash
grok plugin install ./grok-build-cli-slack-plugin --trust
```

Turn off the other plugin named `slack`. That one posts as the signed-in user.

## License

MIT. See `LICENSE`.
