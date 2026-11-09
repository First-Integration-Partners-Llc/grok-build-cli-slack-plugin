---
name: slack-setup
description: Connect this Grok Build CLI install to Slack as one desktop bot. Use when the user wants to choose the bot name, install it, or invite it to channels.
---

# Desktop bot

One bot for this Grok Build install. Its name is the one the user chooses, then invites as `@that-name`. Sessions are not separate Slack apps.

1. Ask for the desktop name if `SLACK_DESKTOP_NAME` is not set.
2. Follow **Install** in the plugin `README.md`. Run the env script for this machine and pass `--app-token` and `--bot-token` (Windows: `-AppToken` and `-BotToken`) on the command line. Do not paste token values into a file in the repository.
3. The listener starts with the next Grok Build session after the plugin is installed with `--trust`. Python 3 must be on `PATH` (`python3` or `python`). No pip packages.

A mention is `@<name> #session-title` plus the prompt. `#session-title` is the session on this machine. A manual `/rename` wins. Two sessions with that title are listed back in the thread.
