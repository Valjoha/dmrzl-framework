#!/usr/bin/env -S uv run --script --quiet
# AUDIENCE: public
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Atomic session counter — returns next session number and logs start time.

Uses mkdir as a POSIX-portable atomic lock (~50ms window).

S216: counter advance + UUID→N mapping write happen under same lock — closes
the attribution race (S212 carry-forward #1). When invoked with `--uuid X` or
when stdin contains a JSON hook payload with `session_id`, the UUID is
appended to `.session-uuid-map` atomically with the counter increment.

Note: no stale-lock cleanup. A "stale" lock means a real bug (crashed process
holding it). Surface it, don't auto-clear.
See spec 2026-05-02-handoff-per-session-split-spec.md §5.2.

Usage:
  next-session.py                       # increment + log start + create stub + append-index-row
  next-session.py --uuid X              # same, plus write UUID→N in .session-uuid-map
  next-session.py --peek                # show current number without incrementing
  next-session.py --end N               # log end time for session N
  next-session.py --resume N --start-time ISO8601
                                        # create stub for existing N (used by /dmrzl-service-promote)

Service mode: if the service-session marker is present for this process tree
(or env var DMRZL_SERVICE=1), the counter still increments but the stub,
INDEX row, and .current-session writes are skipped. The number is consumed
as a gap.
"""

from __future__ import annotations

import json
import os
import select
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = SCRIPT_DIR.parents[1]
COUNTER_FILE = WORKSPACE / ".claude" / "session-counter.txt"
LOCK_DIR = WORKSPACE / ".claude" / "session-counter.lock"
SESSION_LOG = WORKSPACE / ".claude" / "session-log.jsonl"
HANDOFFS_DIR = WORKSPACE / "vault" / "dmrzl" / "session" / "handoffs"
FEEDBACK_DIR = WORKSPACE / ".claude" / "feedback-loops"
HOOKS_DIR = WORKSPACE / ".platform" / "runtime" / "hooks"

MAX_LOCK_RETRIES = 30
LOCK_RETRY_SLEEP = 0.1

# Lazy import of _service_mode helper; degrade gracefully if unavailable.
try:
    sys.path.insert(0, str(HOOKS_DIR))
    from _service_mode import cleanup_stale, is_service_session  # type: ignore
except Exception:  # noqa: BLE001
    def is_service_session() -> bool:  # type: ignore
        return False

    def cleanup_stale() -> bool:  # type: ignore
        return False


def _try_read_stdin_uuid() -> str | None:
    """Best-effort: extract `session_id` from stdin JSON payload (hook context).

    Returns None for skill/CLI invocations (TTY) or empty/malformed stdin.
    """
    try:
        if sys.stdin.isatty():
            return None
        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        if not ready:
            return None
        data = sys.stdin.read()
        if not data.strip():
            return None
        payload = json.loads(data)
        sid = payload.get("session_id") if isinstance(payload, dict) else None
        return sid if isinstance(sid, str) and sid else None
    except Exception:
        return None


def _append_uuid_map(uuid: str, n: int, platform: str) -> None:
    """Append `<uuid>\\t<N>\\t<platform>` to .session-uuid-map (best-effort).

    Called from inside the counter lock so the (UUID, N) pair is atomic with
    the counter advance. Idempotent: skips write if exact line already exists.
    """
    if not uuid:
        return
    map_file = FEEDBACK_DIR / ".session-uuid-map"
    line = f"{uuid}\t{n}\t{platform}\n"
    try:
        if map_file.exists():
            existing = map_file.read_text(encoding="utf-8")
            if line in existing:
                return
        with map_file.open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass


def _acquire_lock() -> None:
    """Spin-lock using mkdir atomicity. Raises SystemExit on timeout."""
    for _ in range(MAX_LOCK_RETRIES):
        try:
            LOCK_DIR.mkdir(exist_ok=False)
            return
        except FileExistsError:
            time.sleep(LOCK_RETRY_SLEEP)
    print("ERROR: could not acquire session counter lock after 3s", file=sys.stderr)
    sys.exit(1)


def _release_lock() -> None:
    import contextlib
    with contextlib.suppress(OSError):
        LOCK_DIR.rmdir()


def _read_counter() -> int:
    if COUNTER_FILE.is_file():
        try:
            return int(COUNTER_FILE.read_text().strip())
        except (ValueError, OSError):
            return 0
    return 0


def _now_hhmm() -> str:
    return datetime.now().strftime("%H:%M")


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def cmd_peek() -> int:
    """Print current counter without incrementing. No lock needed."""
    print(_read_counter(), end="")
    return 0


def cmd_end(session_num: str) -> int:
    """Log end time for a session."""
    if not session_num:
        print("ERROR: --end requires session number", file=sys.stderr)
        return 1
    try:
        n = int(session_num)
    except ValueError:
        print(f"ERROR: invalid session number: {session_num!r}", file=sys.stderr)
        return 1

    end_time = _now_hhmm()
    end_iso = _now_iso()
    record = {"session": n, "event": "end", "time": end_time, "iso": end_iso}
    with SESSION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")
    print(f"Session {n} ended at {end_time}")
    return 0


def cmd_increment(uuid: str | None = None) -> int:
    """Atomically increment counter, create stub, log start, append INDEX row.

    If `uuid` is provided, also writes `<uuid>\\t<N>\\t<PLATFORM>` to
    `.session-uuid-map` under the same lock. Closes the attribution race
    where parallel sessions would otherwise clobber `.current-session`.
    """
    platform = os.environ.get("PLATFORM", "claude-code")
    service_mode = is_service_session()
    _acquire_lock()
    try:
        current = _read_counter()
        # Note: do NOT auto-close previous session here. Parallel sessions are
        # common. Auto-closing session N when N+1 starts would corrupt timestamps.
        next_n = current + 1
        COUNTER_FILE.write_text(str(next_n))

        if not service_mode:
            # Update .current-session for vault-access-tracker hooks.
            # Skipped in service mode — we do not want trackers to attribute
            # writes to this number.
            FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
            (FEEDBACK_DIR / ".current-session").write_text(str(next_n))

            # Atomic UUID→N mapping write, under same lock as counter advance.
            if uuid:
                _append_uuid_map(uuid, next_n, platform)
    finally:
        _release_lock()

    if service_mode:
        # Service session: counter consumed, no telemetry, no stub, no INDEX.
        print(f"[SERVICE] session {next_n} — no traces", file=sys.stderr)
        print(next_n, end="")
        return 0

    # Log session start
    start_time = _now_hhmm()
    start_iso = _now_iso()
    record = {"session": next_n, "event": "start", "time": start_time, "iso": start_iso}
    with SESSION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    # Create per-session handoff stub
    platform = os.environ.get("PLATFORM", "claude-code")
    HANDOFFS_DIR.mkdir(parents=True, exist_ok=True)
    stub = HANDOFFS_DIR / f"S{next_n}.md"

    if not stub.is_file():
        today = _now_date()
        stub_content = (
            "---\n"
            "tags: [dmrzl, session, handoff]\n"
            "type: handoff\n"
            "status: active\n"
            f"session: {next_n}\n"
            f"date: {today}\n"
            f"platform: {platform}\n"
            f"started: {start_time}\n"
            "ended: ~\n"
            "models: []\n"
            "rating: ~\n"
            "compact: ~\n"
            "title: ~\n"
            "---\n"
            "\n"
            f"# Session {next_n}\n"
            "\n"
            "> Up: [[../INDEX|INDEX]]\n"
        )
        stub.write_text(stub_content, encoding="utf-8")

        # Best-effort INDEX update — do not fail if it errors
        append_index = SCRIPT_DIR / "append-index-row.py"
        if append_index.is_file():
            try:
                import subprocess
                subprocess.run(
                    [
                        sys.executable, str(append_index),
                        str(next_n), today, platform,
                        "(in progress)", "-", "-",
                    ],
                    check=False,
                    capture_output=True,
                )
            except OSError:
                pass
    else:
        print(f"WARNING: stub S{next_n}.md already exists — refusing to overwrite", file=sys.stderr)

    print(next_n, end="")
    return 0


def cmd_resume(session_num: str, start_iso: str) -> int:
    """Create stub + INDEX row for an existing session number without incrementing.

    Used by /dmrzl-service-promote: a session ran in service mode (no stub),
    user decided to convert it to a normal session retroactively. We accept
    the supplied number (validated against the counter to prevent regressions)
    and a start time, and lay down the stub that would normally have been
    created at session start.
    """
    if not session_num:
        print("ERROR: --resume requires session number", file=sys.stderr)
        return 1
    try:
        n = int(session_num)
    except ValueError:
        print(f"ERROR: invalid session number: {session_num!r}", file=sys.stderr)
        return 1
    if not start_iso:
        print("ERROR: --resume requires --start-time ISO8601", file=sys.stderr)
        return 1

    current = _read_counter()
    if n > current:
        print(
            f"ERROR: cannot resume session {n} — counter is at {current}. "
            "Did another session increment past it?",
            file=sys.stderr,
        )
        return 1

    HANDOFFS_DIR.mkdir(parents=True, exist_ok=True)
    stub = HANDOFFS_DIR / f"S{n}.md"
    if stub.exists():
        print(f"ERROR: stub S{n}.md already exists — refusing to clobber", file=sys.stderr)
        return 1

    # Parse start ISO for HH:MM display + date.
    try:
        dt = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
    except ValueError:
        print(f"ERROR: invalid --start-time {start_iso!r} (need ISO8601)", file=sys.stderr)
        return 1
    start_hhmm = dt.strftime("%H:%M")
    today = dt.strftime("%Y-%m-%d")
    platform = os.environ.get("PLATFORM", "claude-code")

    record = {"session": n, "event": "start", "time": start_hhmm, "iso": start_iso, "resumed": True}
    with SESSION_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    stub_content = (
        "---\n"
        "tags: [dmrzl, session, handoff]\n"
        "type: handoff\n"
        "status: active\n"
        f"session: {n}\n"
        f"date: {today}\n"
        f"platform: {platform}\n"
        f"started: {start_hhmm}\n"
        "ended: ~\n"
        "models: []\n"
        "rating: ~\n"
        "compact: ~\n"
        "title: ~\n"
        "promoted_from_service: true\n"
        "---\n"
        "\n"
        f"# Session {n}\n"
        "\n"
        "> Up: [[../INDEX|INDEX]]\n"
    )
    stub.write_text(stub_content, encoding="utf-8")

    # Update .current-session — promotion means trackers should attribute future writes here.
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    (FEEDBACK_DIR / ".current-session").write_text(str(n))

    append_index = SCRIPT_DIR / "append-index-row.py"
    if append_index.is_file():
        try:
            import subprocess
            subprocess.run(
                [
                    sys.executable, str(append_index),
                    str(n), today, platform,
                    "(in progress, promoted)", "-", "-",
                ],
                check=False,
                capture_output=True,
            )
        except OSError:
            pass

    print(f"Resumed session {n} (started {start_hhmm} on {today})")
    return 0


def _print_usage() -> None:
    print(
        "Usage: next-session.py [--peek | --end N | --uuid X | --resume N --start-time ISO | --help]\n"
        "  (no args)        atomically increment counter, create stub, append INDEX row\n"
        "                   (auto-detects UUID from stdin JSON if non-TTY)\n"
        "  --uuid X         increment + atomically map UUID X to new session number\n"
        "  --peek           print next session number without incrementing\n"
        "  --end N          log end-of-session timestamp for session N\n"
        "  --resume N --start-time ISO8601\n"
        "                   create stub + INDEX row for existing session N (promotion path)\n"
        "  --help, -h       show this message",
        file=sys.stderr,
    )


def main() -> int:
    # Always best-effort cleanup of stale service-session marker before any work.
    try:
        cleanup_stale()
    except Exception:  # noqa: BLE001
        pass

    args = sys.argv[1:]
    # Help BEFORE any side effect (S202 found that --help fell through to increment).
    if args and args[0] in ("--help", "-h"):
        _print_usage()
        return 0
    if args and args[0] == "--peek":
        return cmd_peek()
    if args and args[0] == "--end":
        session_num = args[1] if len(args) > 1 else ""
        return cmd_end(session_num)
    if args and args[0] == "--resume":
        if len(args) < 4 or args[2] != "--start-time":
            print("next-session.py: --resume requires N --start-time ISO8601", file=sys.stderr)
            _print_usage()
            return 2
        return cmd_resume(args[1], args[3])
    uuid: str | None = None
    if args and args[0] == "--uuid":
        if len(args) < 2 or not args[1]:
            print("next-session.py: --uuid requires a value", file=sys.stderr)
            return 2
        uuid = args[1]
    elif args:
        # Unknown flag — fail loudly instead of silently incrementing.
        print(f"next-session.py: unknown argument {args[0]!r}", file=sys.stderr)
        _print_usage()
        return 2
    if uuid is None:
        uuid = _try_read_stdin_uuid()
    return cmd_increment(uuid=uuid)


if __name__ == "__main__":
    sys.exit(main())
