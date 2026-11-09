# Slack credentials for this Mac. Fill the three values, then load this file
# from a login shell. Do not commit the filled-in values.
#
#   echo 'source /path/to/grok-build-cli-slack-plugin/env/slack.macos.sh' >> ~/.zprofile
#
# New Terminal windows then see the variables. Grok Build started from the Dock
# does not read the shell profile. For that, run the three launchctl lines at
# the bottom once, then quit and reopen Grok Build.

export SLACK_DESKTOP_NAME="grokbuildcli-desktop"
# Token on Basic Information → App-Level Tokens → desktop-listener. Not the Client Secret.
export SLACK_APP_TOKEN="xapp-paste-the-app-level-token"
export SLACK_BOT_TOKEN="xoxb-paste-the-bot-token"

# Uncomment after the exports above have real values. Run once per login user.
# launchctl setenv SLACK_DESKTOP_NAME "$SLACK_DESKTOP_NAME"
# launchctl setenv SLACK_APP_TOKEN "$SLACK_APP_TOKEN"
# launchctl setenv SLACK_BOT_TOKEN "$SLACK_BOT_TOKEN"
