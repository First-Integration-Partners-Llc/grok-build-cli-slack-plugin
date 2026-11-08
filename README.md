# grok-build-cli-slack-plugin

A Grok Build CLI plugin that connects to Slack the way the Grok Bot Slack plugin does. It uses Slack's hosted MCP server at `https://mcp.slack.com/mcp`. After you approve it, search, read, and post run as your Slack user, in the conversations that user can post in.

The Slack plugin shipped for Claude and Cursor hardcodes Slack's partner app. Grok Build is not one of those clients, so that plugin stays on "auth required." This plugin uses an app you register, with Grok Build's loopback redirect and PKCE, so no client secret goes in git.

## Install

From a checkout of this repo:

```bash
grok plugin marketplace add ./grok-build-cli-slack-plugin
grok plugin install grok-slack --trust
```

Or install the directory straight away:

```bash
grok plugin install ./grok-build-cli-slack-plugin --trust
```

Turn the plugin on if `grok plugin list` shows it disabled. In `~/.grok/config.toml`:

```toml
[plugins]
enabled = ["grok-slack"]
```

Disable the other plugin named `slack`. Both cannot own Slack for this CLI.

## Create the Slack app

Slack only allows MCP from an internal app or a Slack Marketplace app.

1. Open [api.slack.com/apps](https://api.slack.com/apps?new_app=1) and choose **From a manifest**.
2. Paste `slack-app-manifest.json`. Create the app in the workspace you want.
3. Leave **PKCE** on. The manifest requests user scopes only.
4. Copy the **Client ID**.

Set this in the environment Grok Build is launched from:

```bash
SLACK_MCP_CLIENT_ID=1234567890.1234567890
```

Restart Grok Build. Run `/mcps`, select `grok-slack`, and press `i`. Approve the app in the browser. Grok Build listens on `http://127.0.0.1:3118/callback` and stores the token in `~/.grok/mcp_credentials.json`.

If your workspace requires admin approval, approve **Grok Build CLI** before signing in.

An internal app works in the workspace where you created it. To ship one client ID for every Grok Build user, publish this same manifest in the Slack Marketplace, then replace `${SLACK_MCP_CLIENT_ID}` in `.mcp.json` with that published client ID.

## What you can ask

Search public channels, read a channel or thread, draft or send a message, react, upload a file, and work with canvases and lists. Private channels and DMs are included only when you ask for them. A sent message appears as you.

## Layout

| Path | Role |
| --- | --- |
| `.mcp.json` | Points Grok Build at Slack's MCP server and the OAuth callback port |
| `slack-app-manifest.json` | Slack app to create: redirect URLs, PKCE, user scopes |
| `skills/slack-setup/` | Walks through connecting the app |
| `skills/slack/` | How to call the Slack tools once connected |

## License

MIT. See `LICENSE`.
