---
name: slack-setup
description: Give the current Grok Build CLI session its own Slack bot, named after the session. Use when the user wants this session to join Slack, be invited to channels, or post as itself.
---

# Session bot

This session posts as its own Slack member. The member's name is the session title (`/rename`, or the generated title). Someone invites that member into a channel. Messages in that channel show the session name.

Do not connect Slack's hosted MCP with a user token. That path posts as the person who signed in.

## Create the member

1. Read the session title. A manual `/rename` wins. Otherwise use `generated_title` in the session's `summary.json`.
2. Run `scripts/session-manifest.ps1 -SessionName "<title>"`. It fills `SESSION_NAME` in `slack-app-manifest.json` and trims the app name to 35 characters.
3. Create an internal Slack app from that JSON at https://api.slack.com/apps?new_app=1 (From a manifest), in the workspace that should see this session.
4. Install the app to the workspace and keep the bot token (`xoxb-`) out of git. Put it in the environment for this session as `SLACK_BOT_TOKEN`.
5. Invite the bot: `/invite @<session name>` in each channel it should read or post in. Until that invite, Slack rejects the post with `not_in_channel`.

A workspace that approves apps will show the same approval wait Grok Bot shows for a new Bot. One session, one app. A second session gets its own app and its own invite.

Grok Bot creates that app from its own servers when you choose Bring to your team's Slack. That call is not available to this CLI. The manifest is the same outcome: a bot named for the session, installed, then invited.
