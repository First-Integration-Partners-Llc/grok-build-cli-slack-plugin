---
name: slack-setup
description: Connect this Grok Build CLI install to Slack as one desktop bot. Use when the user wants to choose the bot name, install it, or invite it to channels.
---

# Desktop bot

One bot for this Grok Build install. Its name is the one the user chooses, then invites as `@that-name`. Sessions are not separate Slack apps.

1. Ask for the desktop name if it is not already chosen.
2. Run `scripts/desktop-manifest.ps1 -DesktopName "<name>"` and create an internal Slack app from the printed JSON.
3. Turn on Socket Mode, install the app, and store the bot token and the app-level token outside git.
4. Invite `@<name>` to each channel it should hear.

A mention is `@<name> #session-title` plus the prompt. `#session-title` is the session on this machine. A manual `/rename` wins. Two sessions with that title are listed back in the thread.
