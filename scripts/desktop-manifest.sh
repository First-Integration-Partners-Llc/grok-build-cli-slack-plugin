#!/usr/bin/env bash
# Print slack-app-manifest.json with this desktop's name filled in.
# Name: first argument, or SLACK_DESKTOP_NAME.
set -euo pipefail

name="${1:-${SLACK_DESKTOP_NAME:-}}"
if [[ -z "$name" ]]; then
  echo "Pass the desktop name, or set SLACK_DESKTOP_NAME." >&2
  exit 1
fi

root="$(cd "$(dirname "$0")/.." && pwd)"
manifest="${MANIFEST_PATH:-$root/slack-app-manifest.json}"

python3 - "$name" "$manifest" <<'PY'
import json
import sys

name, path = sys.argv[1], sys.argv[2]
app = name.strip()
bot = app
if len(app) > 35:
    app = app[:35].rstrip()
if len(bot) > 80:
    bot = bot[:80].rstrip()

with open(path, encoding="utf-8") as handle:
    manifest = json.load(handle)

manifest["display_information"]["name"] = app
manifest["features"]["bot_user"]["display_name"] = bot
json.dump(manifest, sys.stdout, indent=2)
sys.stdout.write("\n")
PY
