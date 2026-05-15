#!/usr/bin/env python3
# AUDIENCE: public
"""block-service-commit: block `git commit` during service-session mode.

Service sessions write no traces by default. Committing code from a service
session would leave a permanent record of the work, defeating the purpose
(NDA, experimental runs, throwaway). The marker can opt-in via
`allow_commits: true`, set by `/dmrzl-service --allow-commits`.

Wire this into PreToolUse with matcher "Bash" — it short-circuits only when
the command line contains `git commit` (with regex word boundary) and the
service marker is active without an explicit commit allowance.

Exit codes:
  0 — allow (not service mode, or allow_commits true, or not a git commit)
  2 — block (service mode active without allow_commits, command is git commit)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))
from _service_mode import get_service_marker

# Match `git commit` as a complete subcommand (not `git commit-tree`, `git foo --commit`).
GIT_COMMIT_RE = re.compile(r"(?:^|[\s;&|()`])git\s+commit(?!\S)")


def main() -> int:
    marker = get_service_marker()
    if not marker:
        return 0
    if marker.get("allow_commits"):
        return 0

    try:
        payload = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, OSError):
        return 0

    tool_input = payload.get("tool_input", {})
    if not isinstance(tool_input, dict):
        return 0
    command = tool_input.get("command", "")
    if not isinstance(command, str) or not command:
        return 0

    if not GIT_COMMIT_RE.search(command):
        return 0

    print(
        "BLOCKED: git commit refused — service-session mode is active "
        f"(session {marker.get('session_number', '?')}, no traces).\n"
        "Options:\n"
        "  • /dmrzl-service-end — exit service mode, then commit normally\n"
        "  • /dmrzl-service-promote — convert this session to a normal one\n"
        "  • Restart with /dmrzl-service --allow-commits if commits were intended",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
