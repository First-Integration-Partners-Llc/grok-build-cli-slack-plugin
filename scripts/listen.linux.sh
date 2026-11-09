#!/bin/sh
# Foreground listener for Linux. The implementation is scripts/listen.py.
#   ./scripts/listen.linux.sh
#   ./scripts/listen.linux.sh --self-test
set -eu
here=$(CDPATH= cd -- "$(dirname "$0")" && pwd)
if [ "${1:-}" = "--self-test" ]; then
  set -- --self-test
else
  set --
fi
if command -v python3 >/dev/null 2>&1; then
  exec python3 "$here/listen.py" "$@"
fi
if command -v python >/dev/null 2>&1; then
  exec python "$here/listen.py" "$@"
fi
echo "Python 3 is not on PATH." >&2
exit 1
