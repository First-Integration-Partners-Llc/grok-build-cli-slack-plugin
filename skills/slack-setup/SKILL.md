---
name: slack-setup
description: Connect the grok-slack plugin to a Slack workspace. Use when the user wants to install, authorize, or fix the Grok Build CLI Slack connection, or when the grok-slack server reports that auth is required.
---

# Connect grok-slack

The server is `grok-slack` in `.mcp.json`. It talks to `https://mcp.slack.com/mcp` and posts as the Slack user who approves it. Scopes and redirect URLs live only in `slack-app-manifest.json`. The OAuth callback port is `3118` in `.mcp.json`. Those two files must stay in agreement.

## Steps

1. Turn off the other Slack plugin whose server is named `slack`. That one uses Slack's partner app and stays unauthenticated in Grok Build.
2. Ask a workspace admin, if the workspace requires app approval, before creating the app.
3. Open [Create an app from a manifest](https://api.slack.com/apps?new_app=1) and paste `slack-app-manifest.json`. Create it in the workspace people will use. Leave PKCE on. Do not add bot scopes. A desktop redirect cannot request them, and this plugin posts as the user.
4. Copy the app's Client ID. Set `SLACK_MCP_CLIENT_ID` in the environment Grok Build starts from. Do not write the client secret into the repo. Grok Build completes OAuth with PKCE and stores tokens in `~/.grok/mcp_credentials.json`.
5. If token exchange reports that `client_secret` is required, set `SLACK_MCP_CLIENT_SECRET` in that same environment and add `"clientSecretEnvVar": "SLACK_MCP_CLIENT_SECRET"` next to `clientId` in `.mcp.json`.
6. Restart Grok Build so it sees the variable. Open `/mcps`, select `grok-slack`, and press `i` to sign in. The browser returns to `http://127.0.0.1:3118/callback`.
7. If the server still fails auth, confirm the manifest redirect URLs were not edited and that the app is an internal app or a Slack Marketplace app. Slack refuses MCP calls from unlisted apps.

An internal app works in the workspace where it was created. One shared client ID for every Grok Build user needs that same manifest published in the Slack Marketplace. After publication, the published client ID can be hardcoded in `.mcp.json` in place of `${SLACK_MCP_CLIENT_ID}`.
