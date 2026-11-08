# Slack credentials for this Linux machine. Fill the three values, then load
# this file from a login shell. Do not commit the filled-in values.
#
#   echo 'source /path/to/grok-build-cli-slack-plugin/env/slack.linux.sh' >> ~/.profile
#
# A desktop session started by a display manager reads ~/.profile at login.
# A terminal-only bash session also needs the same line in ~/.bashrc if that
# file does not already source ~/.profile. Open a new login session before
# starting Grok Build.

export SLACK_DESKTOP_NAME="grokbuildcli-desktop"
export SLACK_APP_TOKEN="xapp-paste-the-app-level-token"
export SLACK_BOT_TOKEN="xoxb-paste-the-bot-token"
