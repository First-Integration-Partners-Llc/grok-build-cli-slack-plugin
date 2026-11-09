# Listen for Slack mentions and hand them to a Grok Build session on this machine.
# Stdlib only. Windows, macOS, and Linux launchers call this file.
#
#   python listen.py
#   python listen.py --self-test

import base64
import hashlib
import json
import os
import re
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import threading
import time
import uuid
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
IDLE = object()
CLOSED = object()
MENTION = re.compile(r"<#[A-Z0-9]+\|([^>]+)>|#([^\s#<>]+)")
USER_MENTION = re.compile(r"<@[A-Z0-9]+>")
BLOCKED_DELIVERY = re.compile(r"has it open|not sent", re.IGNORECASE)
HOLD_REPLY = "That session is busy on this desktop. I will deliver this when it is free."
_LOCK_HANDLE = None
_BUSY = set()
_BUSY_LOCK = threading.Lock()
_HELD_WAITING = set()


def state_dir():
    path = Path.home() / ".config" / "grok-build-cli-slack"
    path.mkdir(parents=True, exist_ok=True)
    return path


def shell_single_quoted(value):
    if not value.startswith("'"):
        return value
    out = []
    index = 1
    while index < len(value):
        if value.startswith("'\\''", index):
            out.append("'")
            index += 4
            continue
        if value[index] == "'":
            break
        out.append(value[index])
        index += 1
    return "".join(out)


def read_saved_env(path):
    found = {}
    try:
        lines = Path(path).read_text(encoding="utf-8").splitlines()
    except OSError:
        return found
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        found[key.strip()] = shell_single_quoted(value.strip())
    return found


def windows_user_env(name):
    if os.name != "nt":
        return ""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value, _ = winreg.QueryValueEx(key, name)
    except OSError:
        return ""
    return str(value).strip()


def load_saved_env():
    for name in ("SLACK_APP_TOKEN", "SLACK_BOT_TOKEN", "SLACK_DESKTOP_NAME"):
        if os.environ.get(name, "").strip():
            continue
        from_user = windows_user_env(name)
        if from_user:
            os.environ[name] = from_user
    saved = read_saved_env(Path.home() / ".config" / "grok-build-cli-slack.env")
    for key, value in saved.items():
        if key and value and not os.environ.get(key, "").strip():
            os.environ[key] = value


def env_value(name):
    load_saved_env()
    return os.environ.get(name, "").strip()


def title_key(text):
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def mention_request(text):
    source = USER_MENTION.sub(" ", text or "")
    chosen = None
    for match in MENTION.finditer(source):
        if chosen is None or match.start() < chosen.start():
            chosen = match
    if chosen is None:
        return None
    tag = chosen.group(1) or chosen.group(2)
    rest = source[:chosen.start()] + source[chosen.end():]
    rest = re.sub(r"\s+", " ", rest).strip()
    return {"tag": tag, "prompt": rest}


def grok_sessions():
    root = Path.home() / ".grok" / "sessions"
    found = []
    if not root.is_dir():
        return found
    for path in root.rglob("summary.json"):
        try:
            summary = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeError):
            continue
        info = summary.get("info") or {}
        title = str(summary.get("generated_title") or "")
        session_id = str(info.get("id") or "")
        if not title.strip() or not session_id:
            continue
        found.append({
            "id": session_id,
            "title": title,
            "key": title_key(title),
            "manual": bool(summary.get("title_is_manual")),
            "cwd": str(info.get("cwd") or ""),
            "dir": str(path.parent),
        })
    return found


def resolve_session(tag, sessions):
    key = title_key(tag)
    matches = [row for row in sessions if row["key"] == key]
    if not matches:
        return {"status": "none"}
    manual = [row for row in matches if row["manual"]]
    if len(manual) == 1:
        return {"status": "one", "session": manual[0]}
    if len(manual) > 1:
        return {"status": "many", "sessions": manual}
    if len(matches) == 1:
        return {"status": "one", "session": matches[0]}
    return {"status": "many", "sessions": matches}


def pid_alive(pid):
    try:
        pid = int(pid)
    except (TypeError, ValueError):
        return False
    if pid <= 0:
        return False
    # os.kill(pid, 0) on Windows is CTRL_C_EVENT. A live grok.exe in another
    # console returns WinError 87, which is not "process does not exist".
    if os.name == "nt":
        return _windows_pid_alive(pid)
    try:
        os.kill(pid, 0)
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _windows_pid_alive(pid):
    import ctypes
    from ctypes import wintypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel32.GetExitCodeProcess.restype = wintypes.BOOL
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    ERROR_ACCESS_DENIED = 5
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ctypes.get_last_error() == ERROR_ACCESS_DENIED
    try:
        code = wintypes.DWORD()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return ctypes.get_last_error() == ERROR_ACCESS_DENIED
        return code.value == STILL_ACTIVE
    finally:
        kernel32.CloseHandle(handle)


def session_turn_busy(directory):
    # events.jsonl records turn_started when a reply begins and turn_ended when
    # the window is waiting for the next prompt. An open idle session has ended.
    path = Path(directory) / "events.jsonl"
    try:
        handle = path.open("rb")
    except OSError:
        return False
    try:
        handle.seek(0, os.SEEK_END)
        pos = handle.tell()
        buf = b""
        while pos > 0:
            take = min(65536, pos)
            pos -= take
            handle.seek(pos)
            buf = handle.read(take) + buf
            lines = buf.splitlines()
            if pos > 0:
                buf = lines[0] if lines else b""
                lines = lines[1:]
            for raw in reversed(lines):
                if b"turn_started" not in raw and b"turn_ended" not in raw:
                    continue
                try:
                    event = json.loads(raw)
                except (json.JSONDecodeError, UnicodeError):
                    continue
                kind = event.get("type")
                if kind == "turn_started":
                    return True
                if kind == "turn_ended":
                    return False
        return False
    finally:
        handle.close()


def active_session_ids():
    path = Path.home() / ".grok" / "active_sessions.json"
    try:
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        return set()
    if isinstance(rows, dict):
        rows = [rows]
    live = set()
    for row in rows or []:
        if not isinstance(row, dict) or not row.get("session_id"):
            continue
        if pid_alive(row.get("pid")):
            live.add(str(row["session_id"]))
    return live


def held_dir():
    path = state_dir() / "held"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_held(session_id, channel, thread_ts, prompt, path=None):
    target = Path(path) if path else held_dir() / f"{uuid.uuid4()}.json"
    target.write_text(json.dumps({
        "session_id": session_id,
        "channel": channel,
        "thread_ts": thread_ts,
        "prompt": prompt,
    }), encoding="utf-8")
    return target


def post_slack(bot_token, channel, thread_ts, text):
    payload = json.dumps({
        "channel": channel,
        "text": text,
        "thread_ts": thread_ts,
    }).encode("utf-8")
    request = urllib.request.Request(
        "https://slack.com/api/chat.postMessage",
        data=payload,
        headers={
            "Authorization": "Bearer " + bot_token,
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not body.get("ok"):
        raise RuntimeError(body.get("error") or "chat.postMessage failed")


def delivery_busy(session_id):
    with _BUSY_LOCK:
        return session_id in _BUSY


def start_delivery(bot_token, session, channel, thread_ts, prompt, held_path=None):
    grok = shutil.which("grok")
    if not grok:
        raise RuntimeError("grok is not on PATH.")
    target = Path(held_path) if held_path else held_dir() / f"{uuid.uuid4()}.json"
    with _BUSY_LOCK:
        if session["id"] in _BUSY:
            return
        _BUSY.add(session["id"])

    def run():
        try:
            completed = subprocess.run(
                [grok, "--cwd", session["cwd"], "-r", session["id"], "-p", prompt, "--output-format", "plain"],
                capture_output=True,
                text=True,
            )
            output = (completed.stdout or "") + (completed.stderr or "")
            blocked = completed.returncode != 0 or BLOCKED_DELIVERY.search(output)
            if blocked:
                save_held(session["id"], channel, thread_ts, prompt, target)
                text = HOLD_REPLY
            else:
                if target.exists():
                    target.unlink()
                text = "Delivered to {0}.".format(session["title"])
            post_slack(bot_token, channel, thread_ts, text)
        except Exception as exc:
            print("Delivery error: {0}".format(exc), flush=True)
        finally:
            with _BUSY_LOCK:
                _BUSY.discard(session["id"])

    threading.Thread(target=run, daemon=True).start()


def deliver_held(bot_token):
    active = active_session_ids()
    sessions = {row["id"]: row for row in grok_sessions()}
    for path in held_dir().glob("*.json"):
        try:
            held = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError, UnicodeError):
            continue
        session_id = str(held.get("session_id") or "")
        if not session_id or delivery_busy(session_id):
            continue
        session = sessions.get(session_id)
        if not session:
            continue
        if session_id in active and session_turn_busy(session.get("dir") or ""):
            key = str(path)
            with _BUSY_LOCK:
                first = key not in _HELD_WAITING
                _HELD_WAITING.add(key)
            if first:
                print("Holding mention for {0} until the reply finishes.".format(session["title"]), flush=True)
            continue
        with _BUSY_LOCK:
            _HELD_WAITING.discard(str(path))
        print("Delivering held mention to {0}.".format(session["title"]), flush=True)
        start_delivery(
            bot_token,
            session,
            held.get("channel") or "",
            held.get("thread_ts") or "",
            held.get("prompt") or "",
            path,
        )


def open_socket_url(app_token):
    request = urllib.request.Request(
        "https://slack.com/api/apps.connections.open",
        data=b"",
        headers={"Authorization": "Bearer " + app_token},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    if not body.get("ok") or not body.get("url"):
        raise RuntimeError(body.get("error") or "apps.connections.open failed")
    return body["url"]


class SlackSocket:
    def __init__(self, raw, buffered=b""):
        self.raw = raw
        self.buf = buffered

    def close(self):
        try:
            self.raw.close()
        except OSError:
            pass

    def _read_exact(self, size):
        while len(self.buf) < size:
            try:
                chunk = self.raw.recv(65536)
            except socket.timeout:
                if self.buf:
                    raise ConnectionError("timed out mid-frame")
                raise
            if not chunk:
                raise ConnectionError("socket closed")
            self.buf += chunk
        out = self.buf[:size]
        self.buf = self.buf[size:]
        return out

    def _frame(self):
        try:
            header = self._read_exact(2)
        except socket.timeout:
            return None
        first, second = header[0], header[1]
        fin = bool(first & 0x80)
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        if length > 8_000_000:
            raise ConnectionError("websocket frame is too large")
        mask = self._read_exact(4) if second & 0x80 else None
        payload = self._read_exact(length) if length else b""
        if mask:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return fin, opcode, payload

    def send(self, opcode, payload):
        mask = os.urandom(4)
        header = bytearray([0x80 | opcode])
        length = len(payload)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header += struct.pack("!H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack("!Q", length)
        masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        self.raw.sendall(bytes(header) + mask + masked)

    def send_text(self, text):
        self.send(0x1, text.encode("utf-8"))

    def recv_text(self, control_deadline=15):
        # Slack sends ping frames often enough that a socket timeout never
        # arrives. Control frames must not postpone the held-message scan.
        started = time.monotonic()
        parts = []
        while True:
            frame = self._frame()
            if frame is None:
                return IDLE
            fin, opcode, payload = frame
            if opcode == 0x8:
                return CLOSED
            if opcode in (0x9, 0xA):
                if opcode == 0x9:
                    self.send(0xA, payload)
                if time.monotonic() - started >= control_deadline:
                    return IDLE
                continue
            if opcode in (0x0, 0x1, 0x2):
                parts.append(payload)
                if fin:
                    return b"".join(parts).decode("utf-8", "replace")


def connect_websocket(url):
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        raise RuntimeError("Slack did not return a WebSocket host.")
    port = parsed.port or (443 if parsed.scheme == "wss" else 80)
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    raw = socket.create_connection((host, port), timeout=30)
    try:
        if parsed.scheme == "wss":
            context = ssl.create_default_context()
            raw = context.wrap_socket(raw, server_hostname=host)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        host_header = host if port in (80, 443) else "{0}:{1}".format(host, port)
        request = (
            "GET {path} HTTP/1.1\r\n"
            "Host: {host}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        ).format(path=path, host=host_header, key=key)
        raw.sendall(request.encode("ascii"))
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = raw.recv(4096)
            if not chunk:
                raise RuntimeError("socket closed during handshake")
            data += chunk
            if len(data) > 65536:
                raise RuntimeError("websocket handshake is too large")
        header, rest = data.split(b"\r\n\r\n", 1)
        status = header.split(b"\r\n", 1)[0]
        if b" 101 " not in status:
            raise RuntimeError(status.decode("ascii", "replace"))
        accept = ""
        for line in header.decode("ascii", "replace").split("\r\n")[1:]:
            if line.lower().startswith("sec-websocket-accept:"):
                accept = line.split(":", 1)[1].strip()
        expected = base64.b64encode(hashlib.sha1((key + WS_GUID).encode("ascii")).digest()).decode("ascii")
        if accept != expected:
            raise RuntimeError("websocket accept did not match")
        raw.settimeout(15)
        return SlackSocket(raw, rest)
    except Exception:
        raw.close()
        raise


def event_from(message):
    payload = message.get("payload") or {}
    event = payload.get("event")
    if not event and isinstance(payload.get("payload"), dict):
        event = payload["payload"].get("event")
    return event or {}


def handle_mention(bot_token, event):
    thread = event.get("thread_ts") or event.get("ts") or ""
    channel = event.get("channel") or ""
    request = mention_request(event.get("text") or "")
    if not request:
        post_slack(bot_token, channel, thread, "Add a session tag, for example #server-admin, then the request.")
        return
    if not request["prompt"]:
        post_slack(bot_token, channel, thread, "Add the request after #{0}.".format(request["tag"]))
        return
    resolved = resolve_session(request["tag"], grok_sessions())
    if resolved["status"] == "none":
        post_slack(bot_token, channel, thread, "No session on this desktop is named {0}.".format(request["tag"]))
        return
    if resolved["status"] == "many":
        lines = ["{0} — {1}".format(row["title"], row["cwd"]) for row in resolved["sessions"]]
        post_slack(
            bot_token,
            channel,
            thread,
            "More than one session matches. Rename one so the title is unique.\n" + "\n".join(lines),
        )
        return
    session = resolved["session"]
    prompt = "From Slack:\n{0}".format(request["prompt"])
    if session["id"] in active_session_ids() and session_turn_busy(session.get("dir") or ""):
        save_held(session["id"], channel, thread, prompt)
        post_slack(bot_token, channel, thread, HOLD_REPLY)
        return
    print("Delivering to {0}.".format(session["title"]), flush=True)
    start_delivery(bot_token, session, channel, thread, prompt)


def _lock_file(directory):
    path = Path(directory) / "listener.lock"
    Path(directory).mkdir(parents=True, exist_ok=True)
    handle = open(path, "a+", encoding="utf-8")
    try:
        if os.name == "nt":
            import msvcrt
            if handle.seek(0, os.SEEK_END) < 1:
                handle.write("0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return None
    return handle


def _unlock_file(handle):
    try:
        if os.name == "nt":
            import msvcrt
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    finally:
        handle.close()


def listener_running(directory=None):
    handle = _lock_file(directory or state_dir())
    if handle is None:
        return True
    _unlock_file(handle)
    return False


def take_listener_lock():
    global _LOCK_HANDLE
    handle = _lock_file(state_dir())
    if handle is None:
        return False
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    _LOCK_HANDLE = handle
    return True


def _held_scan_loop(bot_token):
    while True:
        time.sleep(15)
        try:
            deliver_held(bot_token)
        except Exception as exc:
            print("Held delivery error: {0}".format(exc), flush=True)


def run_listener(app_token, bot_token):
    print("Slack listener starting. Mentions route as @bot #session-title.", flush=True)
    threading.Thread(target=_held_scan_loop, args=(bot_token,), daemon=True).start()
    while True:
        slack = None
        try:
            slack = connect_websocket(open_socket_url(app_token))
            print("WebSocket connected.", flush=True)
            deliver_held(bot_token)
            while True:
                incoming = slack.recv_text()
                if incoming is IDLE:
                    deliver_held(bot_token)
                    continue
                if incoming is CLOSED:
                    break
                message = json.loads(incoming)
                envelope = message.get("envelope_id")
                if envelope:
                    slack.send_text(json.dumps({"envelope_id": envelope}))
                if message.get("type") == "disconnect":
                    print("Slack asked the socket to reconnect.", flush=True)
                    break
                event = event_from(message)
                if event.get("type") != "app_mention":
                    continue
                handle_mention(bot_token, event)
        except Exception as exc:
            print("Listener error: {0}".format(exc), flush=True)
        finally:
            if slack is not None:
                slack.close()
        time.sleep(5)


def _self_test_turn_busy():
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "events.jsonl"
        path.write_text('{"type":"turn_started"}\n{"type":"turn_ended"}\n', encoding="utf-8")
        if session_turn_busy(directory):
            raise SystemExit("ended turn should be idle")
        path.write_text(
            '{"type":"turn_ended"}\n{"type":"turn_started"}\n{"type":"phase_changed"}\n',
            encoding="utf-8",
        )
        if not session_turn_busy(directory):
            raise SystemExit("started turn should be busy")
        if session_turn_busy(str(Path(directory) / "missing")):
            raise SystemExit("missing events should be idle")


def self_test():
    parsed = mention_request("<@U123> #server-admin look at the token")
    if not parsed or parsed["tag"] != "server-admin" or parsed["prompt"] != "look at the token":
        raise SystemExit("plain tag parse failed")
    linked = mention_request("<@U123> <#C123|Fix login bug> check the log")
    if not linked or linked["tag"] != "Fix login bug" or linked["prompt"] != "check the log":
        raise SystemExit("channel-link tag parse failed")
    kept = mention_request("<@U123> #server-admin see #other")
    if not kept or kept["prompt"] != "see #other":
        raise SystemExit("only the session tag should be removed")
    if mention_request("<@U123> hello there"):
        raise SystemExit("a mention without a session tag should not route")
    one = resolve_session("fix-login-bug", [
        {"id": "a", "title": "Fix login bug", "key": title_key("Fix login bug"), "manual": True, "cwd": "D:\\one"},
        {"id": "b", "title": "Fix login bug", "key": title_key("fix-login-bug"), "manual": False, "cwd": "D:\\two"},
    ])
    if one["status"] != "one" or one["session"]["id"] != "a":
        raise SystemExit("manual title should win")
    many = resolve_session("fix login bug", [
        {"id": "a", "key": "fix login bug", "manual": True, "title": "Fix login bug", "cwd": "D:\\one"},
        {"id": "b", "key": "fix login bug", "manual": True, "title": "Fix login bug", "cwd": "D:\\two"},
    ])
    if many["status"] != "many":
        raise SystemExit("two manual titles should stay ambiguous")
    quoted = shell_single_quoted("'xapp-a'\\''b'")
    if quoted != "xapp-a'b":
        raise SystemExit("env quote parse failed")
    if not pid_alive(os.getpid()):
        raise SystemExit("this process should count as alive")
    _self_test_turn_busy()
    if os.name == "nt":
        original_kill = os.kill

        def reject_kill(*_args, **_kwargs):
            raise SystemExit("os.kill must not be used to test a Windows pid")

        os.kill = reject_kill
        try:
            if not pid_alive(os.getpid()):
                raise SystemExit("this process should count as alive without os.kill")
            if pid_alive(2**31 - 1):
                raise SystemExit("a missing pid should count as dead")
        finally:
            os.kill = original_kill
    _self_test_websocket()
    _self_test_ping_idle()
    _self_test_lock()
    print("self-test ok")
    return 0


def _self_test_websocket():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    seen = {}

    def serve():
        conn, _ = server.accept()
        data = b""
        while b"\r\n\r\n" not in data:
            data += conn.recv(4096)
        key = ""
        for line in data.decode("ascii", "replace").split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode("ascii")).digest()).decode("ascii")
        conn.sendall((
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: {0}\r\n"
            "\r\n"
        ).format(accept).encode("ascii"))
        payload = b"hello"
        conn.sendall(bytes([0x81, len(payload)]) + payload)
        header = b""
        while len(header) < 2:
            header += conn.recv(2 - len(header))
        length = header[1] & 0x7F
        mask = b""
        while len(mask) < 4:
            mask += conn.recv(4 - len(mask))
        body = b""
        while len(body) < length:
            body += conn.recv(length - len(body))
        seen["text"] = bytes(byte ^ mask[index % 4] for index, byte in enumerate(body)).decode("utf-8")
        conn.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    client = connect_websocket("ws://127.0.0.1:{0}/link".format(port))
    try:
        if client.recv_text() != "hello":
            raise SystemExit("websocket text frame failed")
        client.send_text('{"envelope_id":"abc"}')
    finally:
        client.close()
        server.close()
    thread.join(timeout=3)
    if seen.get("text") != '{"envelope_id":"abc"}':
        raise SystemExit("websocket client frame was not masked")


def _self_test_ping_idle():
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    def serve():
        conn, _ = server.accept()
        conn.settimeout(3)
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = conn.recv(4096)
            if not chunk:
                return
            data += chunk
        key = ""
        for line in data.decode("ascii", "replace").split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
        accept = base64.b64encode(hashlib.sha1((key + WS_GUID).encode("ascii")).digest()).decode("ascii")
        conn.sendall((
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Accept: {0}\r\n"
            "\r\n"
        ).format(accept).encode("ascii"))
        try:
            while True:
                conn.sendall(bytes([0x89, 1, ord("z")]))
                time.sleep(0.05)
        except OSError:
            pass
        finally:
            conn.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    client = connect_websocket("ws://127.0.0.1:{0}/ping".format(port))
    try:
        started = time.monotonic()
        got = client.recv_text(control_deadline=0.4)
        if got is not IDLE:
            raise SystemExit("pings should not block a held-message scan")
        if time.monotonic() - started > 3:
            raise SystemExit("ping idle wait was too long")
    finally:
        client.close()
        server.close()
    thread.join(timeout=2)


def _self_test_lock():
    import tempfile
    with tempfile.TemporaryDirectory() as directory:
        first = _lock_file(directory)
        if first is None:
            raise SystemExit("lock should be free")
        if _lock_file(directory) is not None:
            raise SystemExit("second lock should fail")
        _unlock_file(first)
        if listener_running(directory):
            raise SystemExit("lock should be free after release")


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if not take_listener_lock():
        print("Slack listener already running.", flush=True)
        return 0
    app_token = env_value("SLACK_APP_TOKEN")
    bot_token = env_value("SLACK_BOT_TOKEN")
    if not app_token.startswith("xapp-") or not bot_token.startswith("xoxb-"):
        print("Slack listener not started. Set SLACK_APP_TOKEN and SLACK_BOT_TOKEN.", file=sys.stderr, flush=True)
        return 0
    run_listener(app_token, bot_token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
