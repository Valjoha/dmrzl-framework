#!/usr/bin/env python3
# AUDIENCE: public
"""PreToolUse advisory hook for Bash commands with better dedicated tools."""

from __future__ import annotations

import json
import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))
try:
    from _hook_telemetry import log_hook_event
except ImportError:
    def log_hook_event(*_a, **_kw): pass


@dataclass(frozen=True)
class Advisory:
    reason: str
    suggestion: str


def _parse_first_segment(command: str) -> list[str]:
    segment = re.split(r"\s*(?:&&|\|\||;|\|)\s*", command.strip(), maxsplit=1)[0]
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return []


def classify(command: str) -> Advisory | None:
    stripped = command.strip()
    if not stripped:
        return None

    tokens = _parse_first_segment(stripped)
    if not tokens:
        return None

    program = Path(tokens[0]).name

    if program == "cat" and len(tokens) == 2 and not tokens[1].startswith("-"):
        return Advisory("cat file", "Use a file read tool for single-file reads.")

    if program == "grep" and len(tokens) >= 2 and any(opt.startswith("-") and any(c in opt for c in "rln") for opt in tokens[1:]):
        return Advisory("grep search", "Use a search tool for text/file searches.")

    if program in {"head", "tail"} and len(tokens) >= 2:
        has_line_count = any(t.startswith("-") and t[1:].isdigit() for t in tokens[1:])
        if has_line_count:
            return Advisory(f"{program} file", "Use a file read tool with line limits.")

    if program == "sed" and any(t == "-i" or t.startswith("-i") for t in tokens[1:]):
        return Advisory("sed in-place edit", "Use the patch/edit tool for file mutations.")

    if program == "find" and len(tokens) >= 4 and tokens[1] == "." and "-name" in tokens[2:]:
        return Advisory("find name search", "Use a file search tool for name lookups.")

    if re.search(r"(^|[;&|]\s*)echo\b.+\s>\s*\S+", stripped):
        return Advisory("echo redirect write", "Use the patch/edit tool for file writes.")

    return None


def main() -> int:
    raw = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    if not raw:
        return 0
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    tool_input = data.get("tool_input") or data.get("params") or {}
    if not isinstance(tool_input, dict):
        return 0

    command = tool_input.get("command") or tool_input.get("cmd") or ""
    if not isinstance(command, str):
        return 0

    advisory = classify(command)
    if advisory is None:
        return 0

    sys.stderr.write(f"ADVISORY: {advisory.suggestion}\n")
    log_hook_event(
        "bash-tool-advisor",
        decision="warn",
        reason=advisory.reason,
        event="PreToolUse",
        tool_name=data.get("tool_name") or "Bash",
        session_id=data.get("session_id"),
        extra={"command": command[:160], "suggestion": advisory.suggestion},
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
