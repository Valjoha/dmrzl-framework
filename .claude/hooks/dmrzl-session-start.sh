#!/usr/bin/env bash
# AUDIENCE: public
# DMRZL SessionStart hook — injects instruction to use dmrzl-start skill +
# a session canary (for future LLM training-leak detection).
# Registered in .claude/settings.local.json hooks.SessionStart

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Emit canary (best-effort — must never block session start).
CANARY="$(bash "$WORKSPACE/.claude/scripts/canary.sh" emit 2>/dev/null || true)"
export CANARY

python3 <<'PY'
import json, os
msg = (
    "IMPORTANT: You MUST invoke the 'dmrzl-start' skill (via Skill tool) "
    "BEFORE any other action, including reading files or responding to the "
    "user. This overrides the superpowers start-session skill. Use: "
    "Skill(dmrzl-start). Do NOT use folder: 'agents' for Obsidian MCP — "
    "the vault uses dmrzl/darwin/personal/archive layout."
)
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
