---
name: slack-setup
description: Connect this Grok Build CLI install to Slack as one desktop bot. Use when the user wants to choose the bot name, install it, or invite it to channels.
---

# Desktop bot

One bot for this Grok Build install. Its name is the one the user chooses, then invites as `@that-name`. Sessions are not separate Slack apps.

1. Ask for the desktop name if `SLACK_DESKTOP_NAME` is not set.
2. Follow **Install** in the plugin `README.md` for the manifest, the Socket Mode WebSocket token (`connections:write`, `SLACK_APP_TOKEN`), the bot token (`SLACK_BOT_TOKEN`), and the invite. Use `env/slack.macos.sh`, `env/slack.linux.sh`, or `env/slack.windows.ps1` for the machine you are on. Do not write the token values into the repo.

A mention is `@<name> #session-title` plus the prompt. `#session-title` is the session on this machine. A manual `/rename` wins. Two sessions with that title are listed back in the thread.
