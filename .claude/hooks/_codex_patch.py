#!/usr/bin/env python3
# AUDIENCE: public
# Helper for Codex apply_patch payload parsing.
# Codex sends patches as raw text in tool_input (not as {file_path, content}).
# Format:
#   *** Begin Patch
#   *** Update File: /path/to/file
#   @@
#   -old line
#   +new line
#   *** Add File: /other/path
#   ...
#   *** End Patch
"""Parse Codex apply_patch payload to extract file paths + added content."""

from __future__ import annotations

import re
from typing import Iterable

# Header lines like "*** Update File: /path", "*** Add File: ...", "*** Delete File: ..."
_HEADER_RE = re.compile(r"^\*\*\*\s+(Update|Add|Delete)\s+File:\s*(.+?)\s*$")


def extract_paths(patch_text: str) -> list[tuple[str, str]]:
    """Return list of (op, path) tuples for every file header in the patch.

    op ∈ {"update", "add", "delete"}.
    """
    if not patch_text or "*** Begin Patch" not in patch_text:
        return []
    out: list[tuple[str, str]] = []
    for line in patch_text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            out.append((m.group(1).lower(), m.group(2)))
    return out


def extract_added_content(patch_text: str, only_path: str | None = None) -> str:
    """Concatenate all `+` lines (added content) from the patch.

    If only_path is given, restrict to lines under that file's section.
    Used by check-vault-language to inspect what's being introduced.
    """
    if not patch_text:
        return ""
    out_lines: list[str] = []
    current: str | None = None
    for line in patch_text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            current = m.group(2)
            continue
        if line.startswith("*** "):
            current = None
            continue
        if only_path is not None and current != only_path:
            continue
        # Diff-added line: starts with `+` but not `+++` (file header marker)
        if line.startswith("+") and not line.startswith("+++"):
            out_lines.append(line[1:])
    return "\n".join(out_lines)


def normalize_payload(data: dict) -> tuple[list[tuple[str, str]], str]:
    """Bridge: given a hook event dict, return (paths, raw_command_text).

    Handles three input styles:
    1. Codex apply_patch:  data["tool_input"]["command"] = patch text
    2. Claude/Gemini Edit/Write: data["tool_input"]["file_path"] = single path
    3. Already-parsed:    data has top-level "patch_text" (test fixtures)
    """
    ti = data.get("tool_input") or data.get("params") or {}
    if not isinstance(ti, dict):
        ti = {}

    # Codex / Bash-shaped patches go via "command"
    cmd = ti.get("command", "")
    if isinstance(cmd, str) and "*** Begin Patch" in cmd:
        return extract_paths(cmd), cmd

    # Direct file_path (Claude Edit/Write, Gemini write_file/replace)
    direct = (
        ti.get("file_path")
        or ti.get("absolute_path")
        or ti.get("path")
        or ti.get("filepath")
    )
    if direct:
        return [("update", str(direct))], ""

    return [], ""


def iter_target_paths(data: dict) -> Iterable[str]:
    """Yield every file path the patch/edit targets, regardless of op."""
    paths, _ = normalize_payload(data)
    for _op, p in paths:
        yield p
