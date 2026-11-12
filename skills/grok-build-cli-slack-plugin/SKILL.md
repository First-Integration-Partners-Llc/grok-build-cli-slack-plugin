---
name: grok-build-cli-slack-plugin
description: >
  When a Grok session receives a prompt that starts with "From Slack:",
  answer that mention in the same Slack thread as this desktop's bot.
  Use when the user says "From Slack:", asks to acknowledge or reply in
  the Slack channel, or asks where a mention of this session should be
  answered. Slash command: /grok-build-cli-slack-plugin.
---

# Reply in the Slack thread

`/grok-build-cli-slack-plugin` only loads these instructions. It does not fetch Slack, replay a missed mention, or post.

The work starts when the user message begins with `From Slack:` and names `channel` and `thread_ts`. That message is the mention.

```text
From Slack:
channel: C0123
thread_ts: 123.456

<the request>
```

Do the requested work. Do not look the channel up through a Slack connection that posts as the signed-in user.

Post one reply with this plugin's post command, from the plugin root (the directory that contains `scripts/listen.py`). Write the reply to a text file so the shell does not mangle a multi-line answer. Do not write an HTTP script. Do not call the official Slack MCP. The command reads `SLACK_BOT_TOKEN` the same way the listener does, and it does not print the token.

```text
python scripts/listen.py --post --channel C0123 --thread-ts "123.456" --text-file reply.txt
```

Quote `thread_ts`. An unquoted timestamp is rounded by PowerShell and the reply misses the thread. Exit 0 prints `ok` or the Slack error code.

The reply text is exactly:

```text
From @<SLACK_DESKTOP_NAME> #<this session title> <answer>
```

`SLACK_DESKTOP_NAME` is the desktop bot's name. Read it from the environment. On Windows, if the process does not have it, read the User environment. Do not print `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, or a `wss://` URL.

Do not wrap the bot name in `<@U...>`. That mentions the bot again and routes the answer back into this plugin.

`:inbox_tray:` on the originating message is the listener's receipt. It is added when the listener accepts the mention for delivery or hold. It is not the answer. The thread reply is the answer.

If the prompt did not start with `From Slack:`, say that delivery has not happened. Do not scrape Slack as the signed-in user to compensate, unless the person explicitly asks for a manual read.

`@here` is only for sessions added with `@bot #session-title join`. A direct `#session-title` mention does not need join. Post `<!here>` only when the task itself is a broadcast:

```text
From @<SLACK_DESKTOP_NAME> #<this session title> <!here> <message>
```

A prompt that arrived from `@here` is not itself a reason to broadcast. `not_in_channel` means the bot needs `/invite`.
