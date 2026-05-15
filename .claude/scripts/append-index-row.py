#!/usr/bin/env -S uv run --script --quiet
# AUDIENCE: public
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Atomically prepend a row to vault/dmrzl/session/INDEX.md (newest first).

Usage:
  append-index-row.py <session> <date> <platform> <title> <compact> [<rating>]

All args are positional — no embedded `|` hazard. Pipe chars inside any field
are replaced with U+FF5C (｜) before insertion. Lock is held across read+rename
so two concurrent invocations cannot race.
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

CW_ROOT = Path(__file__).resolve().parents[2]
INDEX = CW_ROOT / "vault/dmrzl/session/INDEX.md"
LOCK_DIR = CW_ROOT / ".claude/index.lock"
HOOKS_DIR = CW_ROOT / ".platform" / "runtime" / "hooks"

# Service-mode gate: silent no-op if a service session is active.
try:
    sys.path.insert(0, str(HOOKS_DIR))
    from _service_mode import is_service_session  # type: ignore
except Exception:  # noqa: BLE001
    def is_service_session() -> bool:  # type: ignore
        return False

SEPARATOR_RE = re.compile(r"^\|[ -]+\|[ -]+\|[ -]+\|[ -]+\|[ -]+\|[ -]+\|")
MAX_RETRIES = 30
RETRY_SLEEP = 0.1


def esc(value: str) -> str:
    """Replace ASCII pipe with full-width pipe (U+FF5C) to avoid breaking table."""
    return value.replace("|", "｜")


def acquire_lock() -> None:
    """Spin-lock using mkdir atomicity. Raises SystemExit on timeout."""
    for _ in range(MAX_RETRIES):
        try:
            LOCK_DIR.mkdir(exist_ok=False)
            return
        except FileExistsError:
            time.sleep(RETRY_SLEEP)
    print(f"ERROR: INDEX lock timeout (3s) — investigate {LOCK_DIR}", file=sys.stderr)
    sys.exit(1)


def release_lock() -> None:
    import contextlib
    with contextlib.suppress(OSError):
        LOCK_DIR.rmdir()


def main() -> int:
    if is_service_session():
        return 0  # service mode: no INDEX writes
    args = sys.argv[1:]
    if len(args) < 5:
        print(
            "Usage: append-index-row.py <session> <date> <platform> <title> <compact> [<rating>]",
            file=sys.stderr,
        )
        return 1

    session = esc(args[0])
    date = esc(args[1])
    platform = esc(args[2])
    title = esc(args[3])
    compact = esc(args[4])
    rating = esc(args[5]) if len(args) >= 6 else "-"

    new_row = f"| {session} | {date} | {platform} | {title} | {compact} | {rating} |"

    if not INDEX.is_file():
        print(f"ERROR: INDEX.md not found at {INDEX}", file=sys.stderr)
        print("(run migrate-handoff.sh to create it)", file=sys.stderr)
        return 1

    acquire_lock()
    try:
        text = INDEX.read_text(encoding="utf-8")
        lines = text.splitlines(keepends=True)

        # Check if a row for this session already exists (idempotent replace)
        session_pattern = re.compile(rf"^\| {re.escape(session)} \|")
        if any(session_pattern.match(line) for line in lines):
            new_lines = [
                new_row + "\n" if session_pattern.match(line) else line
                for line in lines
            ]
        else:
            # Insert immediately after the table separator line
            new_lines = []
            inserted = False
            for line in lines:
                new_lines.append(line)
                if not inserted and SEPARATOR_RE.match(line):
                    new_lines.append(new_row + "\n")
                    inserted = True

        tmp = INDEX.with_suffix(".md.tmp")
        tmp.write_text("".join(new_lines), encoding="utf-8")
        tmp.replace(INDEX)
    finally:
        release_lock()

    return 0


if __name__ == "__main__":
    sys.exit(main())
