#!/usr/bin/env python3
# AUDIENCE: public
# DMRZL SessionStart hook — injects platform-aware startup instructions +
# a session canary (for future LLM training-leak detection).
# Directly registered on Codex; called through session_start_message.sh on Gemini.
"""SessionStart hook: emit startup context JSON to stdout."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))
from _paths import workspace_root

WORKSPACE = workspace_root()
CANARY_SCRIPT = WORKSPACE / ".claude" / "scripts" / "canary.py"

PLATFORM = os.environ.get("PLATFORM", "claude-code")


def get_canary() -> str:
    """Emit canary token (best-effort — never blocks session start)."""
    try:
        result = subprocess.run(
            ["python3", str(CANARY_SCRIPT), "emit"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        return ""


def check_dream_overdue() -> str:
    """Return a curator nudge string if dream cycle is ≥7 days overdue, else ''."""
    try:
        dream_log = WORKSPACE / "vault" / "dmrzl" / "session" / "DREAM_LOG.md"
        if not dream_log.exists():
            return ""
        text = dream_log.read_text(encoding="utf-8")
        # Match (YYYY-MM-DD) headers or `last-dream: YYYY-MM-DD` frontmatter
        dates = re.findall(r"\((\d{4}-\d{2}-\d{2})\)", text)
        m = re.search(r"last-dream:\s*(\d{4}-\d{2}-\d{2})", text)
        candidate = m.group(1) if m else (max(dates) if dates else None)
        if not candidate:
            return ""
        last = date.fromisoformat(candidate)
        days_since = (date.today() - last).days
        if days_since >= 7:
            return (
                f"\n\n[curator-nudge] Last vault dream cycle was {days_since} days ago. "
                "Consider running `/dmrzl-dream` if vault hygiene matters this session. "
                "Pinned files (frontmatter `pinned: true`) are always preserved."
            )
    except Exception:
        pass
    return ""


PLATFORM_TOOLING = {
    "claude-code": "CLAUDE.md",
    "gemini-cli": "GEMINI.md",
    "codex": "CODEX.md",
}

PLATFORM_SKILL_INVOCATION = {
    "claude-code": "invoke Skill(dmrzl-start)",
    "gemini-cli": 'invoke activate_skill(name: "dmrzl-start")',
    "codex": "read the files listed below directly (Codex has no skill system)",
}


def build_message(canary: str, dream_nudge: str, platform: str) -> str:
    tooling_file = PLATFORM_TOOLING.get(platform, "<your-platform>.md")
    skill_invocation = PLATFORM_SKILL_INVOCATION.get(
        platform, "read the files below directly"
    )
    msg = (
        f"IMPORTANT: You are running on platform `{platform}`. Before responding to the user, "
        "you MUST silently load these files in order:\n"
        "  1. vault/dmrzl/session/INDEX.md (session table — ALWAYS FIRST)\n"
        "  2. From INDEX, identify S{maxN-1} (most recent completed session) and load "
        "vault/dmrzl/session/handoffs/S{maxN-1}.md\n"
        "  3. vault/dmrzl/identity/CORE.md\n"
        f"  4. vault/dmrzl/tooling/{tooling_file}  ← exact filename for your platform — DO NOT "
        "load any other tooling file\n"
        "  5. vault/dmrzl/identity/PERSONA.md\n"
        "  6. vault/personal/USER.md (if it exists; ignore if missing)\n\n"
        f"Preferred entry point on this platform: {skill_invocation}. The skill performs the "
        "loads plus an atomic session counter and creates the per-session handoff stub.\n\n"
        "Vault layout uses 4 top-level folders: dmrzl/, <your-project-slug>/, personal/, archive/. "
        "There is no agents/ folder at the vault root."
    )
    msg += dream_nudge
    if canary:
        msg += f"\n\n[session-canary: {canary}]"
    return msg


def record_uuid_mapping(payload: dict) -> None:
    """No-op as of S216.

    UUID → S{N} mapping is now written atomically by `next-session.py` under
    the same lock as the counter advance. This avoids the race where parallel
    sessions advanced `.current-session` between this hook reading it and
    actually writing the map line. See `next-session.py:_append_uuid_map`.

    Kept as no-op to preserve test surface and import compatibility.
    """
    return None


def main() -> int:
    # Drain stdin (hook contract — harness may send data)
    raw = sys.stdin.read()
    payload: dict = {}
    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {}

    record_uuid_mapping(payload)

    canary = get_canary()
    dream_nudge = check_dream_overdue()
    msg = build_message(canary, dream_nudge, PLATFORM)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": msg,
        }
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
