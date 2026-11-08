---
name: slack
description: Read, search, and post in Slack through the grok-slack MCP server. Use when the user asks to find, read, draft, schedule, or send Slack messages, reactions, files, canvases, or lists from Grok Build CLI.
---

# Slack

Use the `grok-slack` server. Discover tools with `search_tool` before calling them. The tool names are Slack's (`slack_send_message`, `slack_search_public`, `slack_read_channel`, and the rest of that set).

The connection acts as the Slack user who authorized it. A post shows that person's name, and it lands only in conversations that person can post in.

## Which tool

- Search public messages and files with `slack_search_public`.
- Search private channels, DMs, or group DMs only when the user asked to include those. Use `slack_search_public_and_private` for that.
- Read one channel with `slack_read_channel`. Read one thread with `slack_read_thread`.
- Find a channel or person before posting. `slack_search_channels` and `slack_search_users` return the IDs the send tools require.
- Send with `slack_send_message` when the user asked to send. Draft with `slack_send_message_draft` when they asked to prepare a message. Schedule with `slack_schedule_message` when they named a future time.
- React with `slack_add_reaction` instead of sending a message whose only content is an acknowledgement.
- Upload in two calls: `slack_get_file_upload_url`, then POST the bytes, then `slack_complete_file_upload`. Confirm the destination channel before the complete call.

## Message text

Write standard Markdown. `**bold**`, `_italic_`, `` `code` ``, `~~strike~~`, lists, links, and fenced code blocks. Do not use Slack mrkdwn (`*bold*`, `~strike~`). Keep the first line to the point. Reply in a thread by passing the parent message `ts` as `thread_ts`. Set `reply_broadcast` only when the user wants the reply in the channel too.

`slack_create_canvas` uses Canvas markdown, which is a different dialect. Follow that tool's own schema for canvas content.
