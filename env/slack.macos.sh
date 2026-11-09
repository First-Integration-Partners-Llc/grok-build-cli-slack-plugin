#!/usr/bin/env bash
# Save Slack credentials for this Mac. Pass the tokens on the command line.
# Do not paste them into this file.
#
#   ./env/slack.macos.sh \
#     --desktop-name grokbuildcli-desktop \
#     --app-token 'xapp-...' \
#     --bot-token 'xoxb-...'
#
# Writes ~/.config/grok-build-cli-slack.env (mode 600) and loads it from
# ~/.zprofile. Also runs launchctl setenv so a Dock-launched Grok Build sees
# the variables after you quit and reopen it.
set -euo pipefail

desktop_name=""
app_token=""
bot_token=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --desktop-name) desktop_name="${2:-}"; shift 2 ;;
    --app-token) app_token="${2:-}"; shift 2 ;;
    --bot-token) bot_token="${2:-}"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

if [[ -z "$desktop_name" || -z "$app_token" || -z "$bot_token" ]]; then
  echo "Required: --desktop-name, --app-token, --bot-token" >&2
  exit 1
fi
if [[ "$app_token" != xapp-* ]]; then
  echo "App token must be the desktop-listener Token and start with xapp-." >&2
  exit 1
fi
if [[ "$bot_token" != xoxb-* ]]; then
  echo "Bot token must be the Bot User OAuth Token and start with xoxb-." >&2
  exit 1
fi

quote() {
  printf "%s" "$1" | sed "s/'/'\\\\''/g"
}

config_dir="${HOME}/.config"
env_file="${config_dir}/grok-build-cli-slack.env"
mkdir -p "$config_dir"
umask 077
cat > "$env_file" <<EOF
export SLACK_DESKTOP_NAME='$(quote "$desktop_name")'
export SLACK_APP_TOKEN='$(quote "$app_token")'
export SLACK_BOT_TOKEN='$(quote "$bot_token")'
EOF
chmod 600 "$env_file"

source_line="source ${env_file}"
touch "${HOME}/.zprofile"
if ! grep -Fqx "$source_line" "${HOME}/.zprofile"; then
  printf '\n%s\n' "$source_line" >> "${HOME}/.zprofile"
fi

launchctl setenv SLACK_DESKTOP_NAME "$desktop_name"
launchctl setenv SLACK_APP_TOKEN "$app_token"
launchctl setenv SLACK_BOT_TOKEN "$bot_token"

echo "Saved the three Slack variables to ${env_file} and this Mac login session."
echo "Quit Grok Build and open it again."
