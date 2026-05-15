#!/usr/bin/env python3
# AUDIENCE: public
# Block writes that put non-ASCII Cyrillic content into vault/ files.
# Enforces CORE.md § 1: "Documentation & code comments: English only."
# This is the safety net that survives prompt-instruction failure on any platform.
#
# Hook event: PreToolUse / BeforeTool on file-write tools.
# Compatible with both Claude Code (Edit, Write) and Gemini CLI (write_file, replace).
# Reads JSON on stdin from the harness.
#
# Bypass for legitimate non-English vault notes:
#   export DMRZL_ALLOW_VAULT_LANG=1   # disables the check entirely
#
# Exit codes:
#   0 — write allowed
#   2 — write blocked (Cyrillic in vault path)
"""check-vault-language: PreToolUse guard blocking Cyrillic content in vault/."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

# Cyrillic Unicode block U+0400–U+04FF
_CYRILLIC_RE = re.compile(r"[Ѐ-ӿ]")


def is_vault_path(file_path: str) -> bool:
    """Return True if the path is under vault/ (relative or absolute)."""
    # Match absolute .../vault/... or relative vault/...
    return "/vault/" in file_path or file_path.startswith("vault/")


def parse_input(data: dict) -> tuple[str, str]:
    """Return (file_path, content) from parsed JSON input.

    Codex apply_patch (S202 fix): payload is raw diff text in tool_input.command;
    delegate to _codex_patch parser to extract path + added lines.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _codex_patch import normalize_payload, extract_added_content
    paths, raw_cmd = normalize_payload(data)

    if paths and raw_cmd:
        # Codex patch path — examine first vault path's added content
        ti_target = next((p for _op, p in paths if "/vault/" in p or p.startswith("vault/")), None)
        target = ti_target or paths[0][1]
        added = extract_added_content(raw_cmd, only_path=target)
        return str(target), added

    if paths:
        # Direct file_path style (Claude/Gemini)
        target = paths[0][1]
    else:
        target = ""

    ti = data.get("tool_input", data.get("params", data))
    if not isinstance(ti, dict):
        ti = {}
    content = (
        ti.get("content")
        or ti.get("new_string")
        or ti.get("text")
        or ti.get("body")
        or ""
    )
    return str(target), str(content)


def main() -> int:
    # Bypass: env var disables check entirely
    if os.environ.get("DMRZL_ALLOW_VAULT_LANG", "0") == "1":
        return 0

    raw = sys.stdin.read().strip()
    if not raw:
        return 0

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    file_path, content = parse_input(data)

    # Only enforce on vault/ paths
    if not is_vault_path(file_path):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _hook_telemetry import log_hook_event
        log_hook_event("check-vault-language", decision="allow", reason="non-vault path", event="PreToolUse", tool_name="apply_patch", session_id=data.get("session_id"))
        return 0

    # Detect Cyrillic content
    if _CYRILLIC_RE.search(content):
        sys.stderr.write(
            f"BLOCKED: Cyrillic content detected in vault file: {file_path}\n\n"
            "Vault documentation must be English only (CORE.md § 1).\n"
            "User-facing chat may use the configured language; vault files always English.\n\n"
            "If this is a legitimate non-English personal note, bypass with:\n"
            "  DMRZL_ALLOW_VAULT_LANG=1 <your command>\n"
            "Or set the env var globally in your shell to disable this check.\n"
        )
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from _hook_telemetry import log_hook_event
        log_hook_event("check-vault-language", decision="block", reason="cyrillic in vault", event="PreToolUse", tool_name="apply_patch", session_id=data.get("session_id"))
        return 2

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _hook_telemetry import log_hook_event
    log_hook_event("check-vault-language", decision="allow", event="PreToolUse", tool_name="apply_patch", session_id=data.get("session_id"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
