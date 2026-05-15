#!/usr/bin/env python3
# AUDIENCE: public
# Safety hook — blocks destructive shell commands.
# Cross-platform: Claude Code (Bash), Codex CLI (Bash), Gemini CLI (run_shell_command).
# Reads hook event JSON from stdin.
#
# Rewritten S201 to fix S200 false-positive: regex-on-raw-payload matched
# 'rm -rf' inside printf/echo string literals. Now uses shlex tokenization
# and only checks argv[0] of each pipeline segment.
"""Safety check: tokenize the proposed command, block destructive top-level invocations."""

from __future__ import annotations

import json
import os
import re
import shlex
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))
try:
    from _hook_telemetry import log_hook_event
except ImportError:
    def log_hook_event(*_a, **_kw): pass


# Pipeline / sequence separators (not exhaustive — shell is wild, this is a guard, not a sandbox).
_SEGMENT_SPLIT = re.compile(r'\s*(?:&&|\|\||;|\|)\s*')

# Tokens that prefix a real command and should be skipped to find argv[0].
# `env`, `sudo`, `nohup`, `time`, etc. — and `VAR=val` env-assignment.
_PREFIX_SKIP = {"sudo", "env", "nohup", "time", "exec", "command"}


def parse_command_arg(argv: list[str]) -> tuple[str, list[str]]:
    """Return (program, rest_argv) skipping env-assignments and prefix wrappers."""
    i = 0
    while i < len(argv):
        tok = argv[i]
        # VAR=value style assignments
        if "=" in tok and tok.split("=", 1)[0].replace("_", "").isalnum() and not tok.startswith("-"):
            i += 1
            continue
        if tok in _PREFIX_SKIP:
            i += 1
            # `env -i` etc.
            while i < len(argv) and argv[i].startswith("-"):
                i += 1
            continue
        return tok, argv[i + 1:]
    return "", []


def is_destructive(program: str, rest: list[str], full_segment: str, raw_tokens: list[str] | None = None) -> tuple[bool, str]:
    """Return (blocked, reason) for a single command segment."""
    base = os.path.basename(program)
    raw_tokens = raw_tokens or []

    # rm with destructive flags
    if base == "rm":
        for tok in rest:
            if not tok.startswith("-"):
                continue
            flags = tok.lstrip("-")
            if any(f in flags for f in ("r", "R", "f")):
                return True, f"rm with destructive flags: {full_segment[:120]}"
        # `rm /` literal
        if any(tok == "/" for tok in rest):
            return True, f"rm of root path: {full_segment[:120]}"
        return False, ""

    # git commit/push/reset/clean/checkout
    if base == "git" and rest:
        sub = rest[0]
        if sub in ("commit", "push"):
            allow = os.environ.get("PD_ALLOW_COMMIT") or any("PD_ALLOW_COMMIT=1" in t for t in (rest + raw_tokens))
            if not allow:
                return True, f"git {sub} requires explicit user request (set PD_ALLOW_COMMIT=1)"
        if sub == "reset" and "--hard" in rest:
            return True, "git reset --hard"
        if sub == "clean" and any(t.startswith("-") and "f" in t and ("d" in t or "x" in t) for t in rest[1:]):
            return True, "git clean -fd"
        if sub == "checkout" and "--" in rest and "." in rest:
            return True, "git checkout -- ."

    # Recurse into shell -c / -lc wrappers (zsh, bash, sh, dash)
    if base in ("zsh", "bash", "sh", "dash") and len(rest) >= 2:
        # Find the -c flag and its argument
        for i, tok in enumerate(rest[:-1]):
            if tok in ("-c", "-lc", "-cl"):
                inner = rest[i + 1]
                blocked, reason = check_command_string(inner)
                if blocked:
                    return True, f"shell -c wraps destructive: {reason}"
                break

    return False, ""


def check_command_string(command: str) -> tuple[bool, str]:
    """Tokenize a command string and check every pipeline segment."""
    if not command.strip():
        return False, ""

    # Split on common separators while preserving the substrings
    segments = _SEGMENT_SPLIT.split(command)
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        try:
            tokens = shlex.split(seg, posix=True)
        except ValueError:
            # Unbalanced quote — be conservative, fall back to legacy regex on raw segment
            if re.search(r"(?<![\"'])(?:\brm\s+-[a-zA-Z]*[rRfF]|\bgit\s+(?:commit|push|reset\s+--hard|clean\s+-fd))(?![\"'])", seg):
                return True, f"raw-regex (unparseable quoting): {seg[:120]}"
            continue
        if not tokens:
            continue
        program, rest = parse_command_arg(tokens)
        if not program:
            continue
        blocked, reason = is_destructive(program, rest, seg, raw_tokens=tokens)
        if blocked:
            return True, reason

    return False, ""


def main() -> int:
    raw = sys.stdin.read().strip() if not sys.stdin.isatty() else ""
    if not raw:
        log_hook_event("safety-check", decision="noop", reason="no stdin", event="PreToolUse", tool_name="Bash")
        return 0

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        log_hook_event("safety-check", decision="noop", reason="non-JSON stdin", event="PreToolUse", tool_name="Bash")
        return 0

    ti = data.get("tool_input") or data.get("params") or {}
    if not isinstance(ti, dict):
        return 0
    command = ti.get("command") or ti.get("cmd") or ""
    if not isinstance(command, str) or not command.strip():
        log_hook_event("safety-check", decision="noop", reason="empty command", event="PreToolUse", tool_name="Bash")
        return 0

    blocked, reason = check_command_string(command)
    sid = data.get("session_id")

    if blocked:
        sys.stderr.write(f"BLOCKED: {reason}\n")
        sys.stderr.write("Use 'trash' instead of 'rm', or ask the user explicitly for destructive operations.\n")
        log_hook_event("safety-check", decision="block", reason=reason, event="PreToolUse", tool_name="Bash", session_id=sid)
        return 2

    log_hook_event("safety-check", decision="allow", event="PreToolUse", tool_name="Bash", session_id=sid)
    return 0


if __name__ == "__main__":
    sys.exit(main())
