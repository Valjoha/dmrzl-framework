#!/usr/bin/env python3
# AUDIENCE: public
# Unified file-tracker — PostToolUse / AfterTool on file-touching tools.
# Cross-platform: handles Claude Code names (Read/Edit/Write/mcp__obsidian__*)
# AND Gemini CLI names (read_file/write_file/replace) via single dispatch dict.
#
# Schema: {ts}\t[{namespace}]\tS{N}\t{op}\t{method}\t{filename}\t{folder}
"""File tracker hook — logs file operations to session-activity.log."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))
from _paths import workspace_root
from _service_mode import is_service_session

# --- Tool routing table: (op, method) per tool_name ---
TOOL_ROUTES: dict[str, tuple[str, str]] = {
    # Claude Code
    "Read": ("R", "read"),
    "Edit": ("W", "edit"),
    "Write": ("W", "write"),
    "mcp__obsidian__read-note": ("R", "obsidian_read"),
    "mcp__obsidian__edit-note": ("W", "obsidian_edit"),
    "mcp__obsidian__create-note": ("W", "obsidian_create"),
    # Gemini CLI
    "read_file": ("R", "gemini_read"),
    "write_file": ("W", "gemini_write"),
    "replace": ("W", "gemini_replace"),
    # Codex CLI
    "apply_patch": ("W", "codex_patch"),
    "view": ("R", "codex_view"),
}

# --- Noise extensions to skip ---
SKIP_EXTS = {
    ".meta", ".png", ".jpg", ".tga", ".psd", ".fbx",
    ".obj", ".wav", ".mp3", ".ogg", ".dll", ".so", ".dylib",
}

WORKSPACE = workspace_root()
VAULT_ROOT = WORKSPACE / "vault"
CODE_ROOT = Path("{{project_root}}/Assets")
LOG_DIR = WORKSPACE / ".claude" / "feedback-loops"
LOG_FILE = LOG_DIR / "session-activity.log"
SESSION_FILE = LOG_DIR / ".current-session"
SESSION_MAP = LOG_DIR / ".session-map"


def parse_input(data: dict) -> tuple[str, str, str, str, str]:
    """Extract (session_id, tool_name, file_path, mcp_filename, mcp_folder)."""
    sid = data.get("session_id", "")
    tool = data.get("tool_name", data.get("toolName", ""))
    ti = data.get("tool_input", data.get("params", data))
    if not isinstance(ti, dict):
        ti = {}
    fpath = ti.get("file_path") or ti.get("absolute_path") or ti.get("path") or ""
    fname = ti.get("filename", "")
    folder = ti.get("folder", "")
    return str(sid), str(tool), str(fpath), str(fname), str(folder)


def classify_namespace(abs_path: Path) -> tuple[str, str]:
    """Return (namespace, rel) for an absolute path."""
    try:
        rel_vault = abs_path.relative_to(VAULT_ROOT)
        return "vault", str(rel_vault)
    except ValueError:
        pass
    try:
        rel_code = abs_path.relative_to(CODE_ROOT)
        return "code", "Assets/" + str(rel_code)
    except ValueError:
        pass
    scripts_dir = WORKSPACE / ".claude" / "scripts"
    if str(abs_path).startswith(str(HOOKS_DIR) + "/") or str(abs_path).startswith(str(scripts_dir) + "/"):
        return "script", str(abs_path.relative_to(WORKSPACE))
    parent_claude = WORKSPACE / ".claude"
    abs_str = str(abs_path)
    if (abs_str.endswith(".json") or abs_str.endswith(".env")) and abs_str.startswith(str(parent_claude)):
        return "config", str(abs_path.relative_to(WORKSPACE))
    if abs_str == str(WORKSPACE / "CLAUDE.md"):
        return "config", "CLAUDE.md"
    home = Path.home()
    for prefix in ("Projects/dmrzl-framework/", "Projects/dmrzl-skills/", "Projects/dmrzl-memory/"):
        if abs_str.startswith(str(home / prefix)):
            return "dist", str(abs_path.relative_to(home / "Projects"))
    return "other", abs_str


def resolve_session(session_id: str) -> str:
    """Resolve session number from map cache or .current-session file."""
    if session_id and SESSION_MAP.exists():
        for line in SESSION_MAP.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0] == session_id:
                return parts[1]

    current = SESSION_FILE.read_text(encoding="utf-8").strip() if SESSION_FILE.exists() else "?"

    if session_id and current != "?":
        with SESSION_MAP.open("a", encoding="utf-8") as f:
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            f.write(f"{session_id}\t{current}\t{ts}\n")
        return current

    return current


def rotate_log_if_needed() -> None:
    """Rotate log to historical when ≥1000 lines."""
    if not LOG_FILE.exists():
        return
    lines = LOG_FILE.read_text(encoding="utf-8")
    count = lines.count("\n")
    if count >= 1000:
        hist = LOG_DIR / "session-activity-historical.log"
        with hist.open("a", encoding="utf-8") as f:
            f.write(lines)
        LOG_FILE.write_text("", encoding="utf-8")


def main() -> int:
    if is_service_session():
        return 0  # service mode: no logging
    raw = sys.stdin.read().strip()
    if not raw:
        return 0

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return 0

    session_id, tool_name, file_path, mcp_filename, mcp_folder = parse_input(data)

    route = TOOL_ROUTES.get(tool_name)
    if route is None:
        return 0

    op, method = route

    # Resolve absolute path
    if file_path:
        abs_path = Path(file_path)
    elif mcp_filename:
        if mcp_folder:
            abs_path = VAULT_ROOT / mcp_folder / mcp_filename
        else:
            abs_path = VAULT_ROOT / mcp_filename
    else:
        return 0

    # Skip noise extensions
    if abs_path.suffix.lower() in SKIP_EXTS:
        return 0

    namespace, rel = classify_namespace(abs_path)

    # Split rel → folder + filename
    rel_path = Path(rel)
    filename = rel_path.name
    folder = str(rel_path.parent) if rel_path.parent != Path(".") else ""

    session = resolve_session(session_id)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(f"{ts}\t[{namespace}]\tS{session}\t{op}\t{method}\t{filename}\t{folder}\n")

    rotate_log_if_needed()
    return 0


if __name__ == "__main__":
    sys.exit(main())
