#!/usr/bin/env python3
# AUDIENCE: public
# Shared hook telemetry — append-only JSONL log of hook fires across all platforms.
# Solves S200 finding: Codex session JSONL has no hook_* events, so we self-record.
"""Hook telemetry helper.

Usage from a hook script (Python):

    from _hook_telemetry import log_hook_event
    log_hook_event("safety-check", decision="block", reason="rm -rf detected",
                   tool_name="Bash", session_id=stdin_json.get("session_id"))

Usage from a hook script (bash):

    python3 "$HOOKS_DIR/_hook_telemetry.py" \
        --hook safety-check --decision block --reason "rm -rf" --tool Bash

Schema (JSONL line):
    ts: ISO-8601 UTC
    session_id: from hook stdin (Codex/Gemini) or env CLAUDE_SESSION_ID
    platform: PLATFORM env var or "claude-code"
    hook: hook script name (without ext)
    event: PreToolUse|PostToolUse|SessionStart|Stop
    tool: matched tool_name (Bash, apply_patch, mcp__*, ...)
    decision: allow|block|warn|noop
    reason: short human-readable explanation
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))
from _paths import workspace_root

WORKSPACE = workspace_root()
LOG_DIR = WORKSPACE / ".claude" / "feedback-loops"
LOG_FILE = LOG_DIR / "hook-events.jsonl"

DECISIONS = {"allow", "block", "warn", "noop"}


_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


def _lookup_uuid_in_map(uuid: str) -> str | None:
    """Resolve UUID → S{N} via `.session-uuid-map`. Latest entry wins.

    S216 fix: parallel sessions race on `.current-session`, so a hook fired
    by session N may misread the global counter and mis-attribute its event.
    The UUID map is written atomically by `next-session.py` under the
    counter lock, so the (UUID, N) pair is always correct at session start.
    Returns None if UUID not yet recorded.
    """
    map_file = LOG_DIR / ".session-uuid-map"
    if not map_file.exists():
        return None
    try:
        last: str | None = None
        for line in map_file.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0] == uuid:
                last = parts[1]
        return last
    except OSError:
        return None


def _resolve_session_id(explicit: str | None) -> str:
    """Return the canonical short session number S{N}, never a UUID.

    Resolution order:
      1. test fixtures (`smoke-*`, `test-*`) — passed through unchanged
      2. short numeric IDs (≤16 chars, non-UUID) — returned as-is
      3. UUID → look up in `.session-uuid-map` (S216 attribution-race fix)
      4. fallback to `.current-session` (legacy path; races under parallel)
    """
    if explicit:
        if explicit.startswith(("smoke-", "test-")):
            return explicit  # test fixtures
        if not _UUID_RE.match(explicit) and explicit.isascii() and len(explicit) <= 16:
            return explicit  # short session number / numeric ID
        if _UUID_RE.match(explicit):
            mapped = _lookup_uuid_in_map(explicit)
            if mapped:
                return mapped
    sid_file = LOG_DIR / ".current-session"
    if sid_file.exists():
        return sid_file.read_text(encoding="utf-8").strip()
    return "unknown"


def log_hook_event(
    hook: str,
    *,
    decision: str = "allow",
    reason: str | None = None,
    event: str | None = None,
    tool_name: str | None = None,
    session_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Append a single hook telemetry record. Never raises."""
    if decision not in DECISIONS:
        decision = "noop"
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "session_id": _resolve_session_id(session_id),
            "platform": os.environ.get("PLATFORM", "claude-code"),
            "hook": hook,
            "event": event,
            "tool": tool_name,
            "decision": decision,
            "reason": reason,
        }
        if extra:
            record["extra"] = extra
        with LOG_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # Telemetry must never block the hook.
        pass


def emit_event(
    *,
    hook: str,
    decision: str = "allow",
    reason: str | None = None,
    event: str | None = None,
    tool: str | None = None,
    session_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    """Compatibility wrapper for hooks migrated from the old shell layer."""
    log_hook_event(
        hook,
        decision=decision,
        reason=reason,
        event=event,
        tool_name=tool,
        session_id=session_id,
        extra=extra,
    )


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Hook telemetry CLI shim")
    parser.add_argument("--hook", required=True)
    parser.add_argument("--decision", default="allow")
    parser.add_argument("--reason", default=None)
    parser.add_argument("--event", default=None)
    parser.add_argument("--tool", dest="tool_name", default=None)
    parser.add_argument("--session", dest="session_id", default=None)
    args = parser.parse_args()
    log_hook_event(
        args.hook,
        decision=args.decision,
        reason=args.reason,
        event=args.event,
        tool_name=args.tool_name,
        session_id=args.session_id,
    )
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
