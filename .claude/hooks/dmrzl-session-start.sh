#!/usr/bin/env bash
# AUDIENCE: public
# DMRZL SessionStart hook — injects platform-neutral startup instructions +
# a session canary (for future LLM training-leak detection).
# Registered in .claude/settings.json (Claude Code) and .gemini/settings.json (Gemini CLI).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Tell next-session.sh which platform created this session (consumed by stub frontmatter).
export PLATFORM="${PLATFORM:-claude-code}"
export WORKSPACE

# Emit canary (best-effort — must never block session start).
CANARY="$(bash "$WORKSPACE/.claude/scripts/canary.sh" emit 2>/dev/null || true)"
export CANARY

python3 <<'PY'
import json, os, re, datetime
from pathlib import Path

WORKSPACE = Path(os.environ.get("WORKSPACE", os.getcwd()))
msg = (
    "IMPORTANT: Before responding to the user, you MUST silently load these files "
    "in order:\n"
    "  1. vault/dmrzl/session/INDEX.md (session table — ALWAYS FIRST)\n"
    "  2. From INDEX, identify S{maxN-1} (most recent completed session) and load "
    "vault/dmrzl/session/handoffs/S{maxN-1}.md\n"
    "  3. vault/dmrzl/identity/CORE.md\n"
    "  4. vault/dmrzl/tooling/<your-platform>.md (CLAUDE_CODE.md, CODEX.md, or GEMINI_CLI.md)\n"
    "  5. vault/dmrzl/identity/PERSONA.md\n"
    "  6. vault/personal/USER.md (if it exists; ignore if missing)\n\n"
    "If running on Claude Code with the dmrzl-start skill installed, prefer invoking "
    "Skill(dmrzl-start) — it does the loads plus an atomic session counter and creates "
    "the per-session handoff stub. On other platforms (Codex, Gemini CLI), read the "
    "files directly using the available file-read tool.\n\n"
    "Vault layout uses 4 top-level folders: dmrzl/, <your-project-slug>/, personal/, archive/. "
    "There is no agents/ folder at the vault root."
)

# Dream overdue check (Hermes-style curator nudge)
# If last-dream > 7 days ago, add a non-blocking reminder.
try:
    dream_log = WORKSPACE / "vault" / "dmrzl" / "session" / "DREAM_LOG.md"
    if dream_log.exists():
        text = dream_log.read_text(encoding="utf-8")
        # Look for the most recent date in any of the supported formats:
        #  - `last-dream: YYYY-MM-DD` (frontmatter or vault file)
        #  - `## Dream Cycle N — Session N (YYYY-MM-DD)` (DREAM_LOG.md headers)
        dates = re.findall(r"\((\d{4}-\d{2}-\d{2})\)", text)
        m = re.search(r"last-dream:\s*(\d{4}-\d{2}-\d{2})", text)
        candidate = m.group(1) if m else (max(dates) if dates else None)
        if candidate:
            last = datetime.date.fromisoformat(candidate)
            days_since = (datetime.date.today() - last).days
            if days_since >= 7:
                msg += (
                    f"\n\n[curator-nudge] Last vault dream cycle was {days_since} days ago. "
                    f"Consider running `/dmrzl-dream` if vault hygiene matters this session. "
                    f"Pinned files (frontmatter `pinned: true`) are always preserved."
                )
except Exception:
    pass  # Never block session start

canary = os.environ.get("CANARY", "").strip()
if canary:
    msg += f"\n\n[session-canary: {canary}]"
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": msg,
    }
}))
PY
