# Detach one desktop listener and return. SessionStart must not stay running.
# A second start exits immediately when the lock is already held.

import os
import subprocess
import sys
from pathlib import Path

import listen


def main():
    listen.load_saved_env()
    if listen.listener_running():
        print("Slack listener already running.")
        return 0
    app_token = os.environ.get("SLACK_APP_TOKEN", "").strip()
    bot_token = os.environ.get("SLACK_BOT_TOKEN", "").strip()
    if not app_token.startswith("xapp-") or not bot_token.startswith("xoxb-"):
        print("Slack listener not started. Set SLACK_APP_TOKEN and SLACK_BOT_TOKEN.", file=sys.stderr)
        return 0
    log_path = listen.state_dir() / "listener.log"
    log = open(log_path, "a", encoding="utf-8")
    script = str(Path(__file__).with_name("listen.py"))
    command = [sys.executable, "-u", script]
    kwargs = {
        "args": command,
        "stdin": subprocess.DEVNULL,
        "stdout": log,
        "stderr": subprocess.STDOUT,
    }
    if os.name == "nt":
        kwargs["creationflags"] = 0x00000008 | 0x00000200 | 0x08000000
    else:
        kwargs["start_new_session"] = True
        kwargs["close_fds"] = True
    subprocess.Popen(**kwargs)
    print("Slack listener started.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
