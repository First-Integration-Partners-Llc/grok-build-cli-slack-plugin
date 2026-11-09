#!/bin/sh
# Detach the desktop listener and return. Grok runs this on SessionStart.
set -eu
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$here/start_listener.py"
fi
if command -v python >/dev/null 2>&1; then
  exec python "$here/start_listener.py"
fi
echo "Python 3 is required to start the Slack listener." >&2
exit 1
