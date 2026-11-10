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

This desktop has one Slack bot. Its name is `SLACK_DESKTOP_NAME`. It posts as itself. A mention `@that-name #session-title` delivers the rest of the text to the local session with that title.

A prompt that starts with `From Slack:` is that delivery. The header names the thread:

```text
From Slack:
channel: C0123
thread_ts: 123.456

<the request>
```

Do the requested work. Then post the answer in that thread with `chat.postMessage`, as plain text:

```text
From @<SLACK_DESKTOP_NAME> #<this session's title> <answer>
```

Do not wrap the bot name in `<@U...>`. That mentions the bot again. Use `SLACK_BOT_TOKEN` from the environment. On Windows, read it from the User environment when the process does not have it. Do not print the token, the app token, or a `wss://` URL.

`:inbox_tray:` on the originating message is the listener's receipt. It is not the answer.

Post `<!here>` only when the task itself is a broadcast:

```text
From @<SLACK_DESKTOP_NAME> #<this session's title> <!here> <message>
```

A prompt that arrived from `@here` is not itself a reason to broadcast. `@here` reaches the named sessions that were added to that channel on this runtime, except the session named on that line. It does not replace between-bot messaging.

If the header has no channel, find the mention in the channels this bot has joined and reply in that thread. `not_in_channel` means the bot needs `/invite`. Do not post as the signed-in user, and do not use a Slack connection that posts as that user.

Install, tokens, and the listener are in the plugin `README.md`.
