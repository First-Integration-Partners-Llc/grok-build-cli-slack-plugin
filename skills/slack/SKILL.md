---
name: slack
description: >
  Speak in Slack as this desktop's Grok Build bot, and route an @mention
  plus #session-title to that session. Use when a Slack mention should
  reach a local session, or when a From Slack: prompt should be answered
  with scripts/listen.py --post.
---

# Slack

Post as this desktop's bot. Do not post as the signed-in user. Do not use a Slack connection that posts as that user.

`/grok-build-cli-slack-plugin` only loads the reply instructions. It does not fetch Slack.

A mention `@desktop-name #session-title` plus the request is delivered by the listener. The session receives one prompt that starts with `From Slack:` and names `channel` and `thread_ts`. That prompt is the mention. A direct `#session-title` mention does not need join.

`@here` reaches only the sessions added in that channel with `@bot #session-title join`, except the session named on that line.

If the session is closed, or open and its last turn has ended, the listener delivers the prompt now. If the last turn is still started, it posts `That session is busy on this desktop. I will deliver this when it is free.` and delivers once when the turn ends. If two sessions share the title, it lists their directories and waits.

`:inbox_tray:` is the listener's receipt, added when the mention is accepted. The thread reply is the answer.

If the user message does not start with `From Slack:`, delivery has not happened. Say so. Do not scrape Slack as the signed-in user unless the person explicitly asks for a manual read.

When the message does start with `From Slack:`, do the work, then post from the plugin root (the directory that contains `scripts/listen.py`):

```text
python scripts/listen.py --post --channel C0123 --thread-ts "123.456" --text-file reply.txt
```

Quote `thread_ts`. An unquoted timestamp is rounded by PowerShell and the reply misses the thread.

The text file is one reply:

```text
From @<SLACK_DESKTOP_NAME> #<this session title> <answer>
```

Do not wrap the bot name in `<@U...>`. Do not write an HTTP script. Do not call the official Slack MCP. The command reads the bot token and does not print it. `ok` means the reply was posted. Any other line is the Slack error code. `not_in_channel` means the bot needs `/invite`.
