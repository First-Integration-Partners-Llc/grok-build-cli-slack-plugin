---
name: slack
description: Post and read Slack as the current Grok Build CLI session's own bot. Use when the user asks this session to speak, react, or read in a Slack channel.
---

# Slack

Speak as this session's bot. The name in the channel is the session title. The bot token is `SLACK_BOT_TOKEN`. Never send with a user token, and never call the Slack MCP tools that post as the signed-in person.

The bot can read and post only in channels where it has been invited. If Slack returns `not_in_channel`, ask the user to invite `@<session name>` and stop. Do not fall back to posting as them.

## Send

`chat.postMessage` with the bot token. Pass the channel ID. Pass `thread_ts` when the reply belongs in a thread. The text is standard Markdown in `markdown_text`. Leave `username` unset so Slack shows the bot's own name.

Confirm the channel before the first post in a conversation. A reaction uses `reactions.add` on the same token. File uploads use the bot token's external upload methods and are shared only into channels the bot has joined.
