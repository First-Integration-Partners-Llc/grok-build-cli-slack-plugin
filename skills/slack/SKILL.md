---
name: slack
description: Speak in Slack as this desktop's Grok Build bot, and route an @mention plus #session-title to that session. Use when a Slack mention should reach a local session or this desktop should post under its own bot name.
---

# Slack

Post with this desktop's bot token. The name in the channel is the name chosen at connect time. Do not post as the signed-in user.

The desktop listener starts with Grok Build on Windows, macOS, and Linux. The same program is `scripts/listen.py`. macOS runs it through `scripts/listen.macos.sh`, Linux through `scripts/listen.linux.sh`, and Windows through `scripts/listen.ps1`. An incoming mention addressed to this bot is routed only when it carries `#session-title`. The title is matched on this machine. The words after the tag are the prompt.

Submit that prompt to the session. If the session is closed, or open and waiting for the next prompt, deliver it now. If a reply is already in progress, hold the message, say so in the Slack thread, and deliver it when that reply finishes. If two sessions share the title, list their directories in the thread and wait.

The bot can read and post only where it has been invited. `not_in_channel` means ask for `/invite @<desktop name>`.
