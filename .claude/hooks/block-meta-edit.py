#!/usr/bin/env python3
# AUDIENCE: public
# PreToolUse: block edits to Unity .meta files. Cross-platform.
# S202 fix: Codex apply_patch payload is raw diff text (not file_path JSON);
# old block-meta-edit.sh missed it entirely. Use _codex_patch parser to
# handle Codex/Claude/Gemini formats uniformly.
"""Block writes/patches that target Unity .meta files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))
from _codex_patch import iter_target_paths
try:
    from _hook_telemetry import log_hook_event
except ImportError:
    def log_hook_event(*_a, **_kw): pass


def main() -> int:
    raw = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    if not raw:
        return 0
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    sid = data.get("session_id")
    targets = list(iter_target_paths(data))
    if not targets:
        log_hook_event("block-meta-edit", decision="noop", reason="no target path",
                       event="PreToolUse", tool_name="apply_patch", session_id=sid)
        return 0

    blocked = [p for p in targets if p.endswith(".meta")]
    if blocked:
        sys.stderr.write(
            f"BLOCKED: Never edit .meta files directly — Unity manages these automatically.\n"
            f"Blocked path(s): {', '.join(blocked)}\n"
            "If you need to change asset settings, use the Unity Editor or UnityMCP tools.\n"
        )
        log_hook_event("block-meta-edit", decision="block",
                       reason=f".meta path: {blocked[0]}",
                       event="PreToolUse", tool_name="apply_patch", session_id=sid)
        return 2

    log_hook_event("block-meta-edit", decision="allow",
                   event="PreToolUse", tool_name="apply_patch", session_id=sid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
