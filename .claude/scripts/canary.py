#!/usr/bin/env -S uv run --script --quiet
# AUDIENCE: public
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Canary emission for LLM training-leak detection.

Each session emits a PAIR of UUIDs:
  - exposed: printed to stdout (consumed by SessionStart hook → Claude context)
  - control: stays in local ledger only, NEVER leaves this machine

Future probe tests whether models memorized 'exposed' UUIDs. If 'control'
UUIDs also leak, the source is not training but infra (backup/scrape/breach).

Ledger: ~/.claude/canaries/ledger.jsonl (outside any git repo, local only).

Usage:
  canary.py emit   # emit pair, print exposed UUID to stdout
  canary.py list   # print raw ledger
  canary.py stats  # summary stats
  canary.py probe  # stub (not implemented)
"""

from __future__ import annotations

import contextlib
import json
import os
import stat
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE = SCRIPT_DIR.parents[1]

LEDGER_DIR = Path.home() / ".claude" / "canaries"
LEDGER = LEDGER_DIR / "ledger.jsonl"
COUNTER_FILE = WORKSPACE / ".claude" / "session-counter.txt"


def _ensure_ledger() -> None:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    # chmod 700 on the directory
    with contextlib.suppress(OSError):
        LEDGER_DIR.chmod(stat.S_IRWXU)
    if not LEDGER.exists():
        LEDGER.touch()
    with contextlib.suppress(OSError):
        LEDGER.chmod(stat.S_IRUSR | stat.S_IWUSR)


def _gen_uuid() -> str:
    return str(uuid.uuid4())


def cmd_emit() -> int:
    _ensure_ledger()
    ts = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    # SessionStart hook fires BEFORE the counter bumps; +1 estimates the
    # upcoming session number. Timestamp is the authoritative key.
    if COUNTER_FILE.is_file():
        try:
            session: str | int = int(COUNTER_FILE.read_text().strip()) + 1
        except ValueError:
            session = "unknown"
    else:
        session = "unknown"

    exposed = _gen_uuid()
    control = _gen_uuid()

    workspace_sha = ""
    try:
        import subprocess

        result = subprocess.run(
            ["git", "-C", str(WORKSPACE), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            workspace_sha = result.stdout.strip()
    except OSError:
        pass

    record = {
        "ts": ts,
        "session": session,
        "exposed": exposed,
        "control": control,
        "workspace_sha": workspace_sha,
    }
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    # stdout: only the exposed UUID. Control stays in ledger.
    sys.stdout.write(exposed)
    sys.stdout.flush()
    return 0


def cmd_list() -> int:
    _ensure_ledger()
    if LEDGER.stat().st_size > 0:
        sys.stdout.write(LEDGER.read_text(encoding="utf-8"))
    else:
        print(f"(empty ledger: {LEDGER})", file=sys.stderr)
    return 0


def cmd_stats() -> int:
    _ensure_ledger()
    lines = LEDGER.read_text(encoding="utf-8").splitlines() if LEDGER.exists() else []
    count = len([ln for ln in lines if ln.strip()])
    print(f"ledger: {LEDGER}")
    print(f"canaries emitted: {count}")
    nonempty = [ln for ln in lines if ln.strip()]
    if nonempty:
        try:
            first = json.loads(nonempty[0])["ts"]
            last = json.loads(nonempty[-1])["ts"]
            print(f"first: {first}")
            print(f"last:  {last}")
        except (json.JSONDecodeError, KeyError):
            pass
    return 0


def cmd_probe() -> int:
    msg = """\
canary.py probe — not implemented yet (stub).

When ready to test for leaks:
  1. Sample 'exposed' UUIDs from ledger (older than ~6 months — training
     cycle window).
  2. For each sample, probe target model with completions like:
       "Continue this log line: session-canary: <first-8-chars-of-uuid>"
       "Complete the UUID that starts with <prefix> from a session canary"
  3. Record any response that reproduces the full UUID.
  4. ALSO probe a random sample of 'control' UUIDs with the same prompts.
     Control must never leak — any hit there = infra compromise, not training.
  5. Cross-check: newer Anthropic models, OpenAI, Google — to localize
     which provider's pipeline the exposure came from."""
    print(msg, file=sys.stderr)
    return 1


COMMANDS = {
    "emit": cmd_emit,
    "list": cmd_list,
    "stats": cmd_stats,
    "probe": cmd_probe,
}


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd not in COMMANDS:
        print(f"Usage: {os.path.basename(sys.argv[0])} {{emit|list|stats|probe}}", file=sys.stderr)
        return 2
    return COMMANDS[cmd]()


if __name__ == "__main__":
    sys.exit(main())
