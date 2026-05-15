#!/usr/bin/env python3
# AUDIENCE: public
"""MEMORY.md line count guardrail."""

import json
import sys
import subprocess
from pathlib import Path

# Add script dir to path for _hook_telemetry import
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from _hook_telemetry import emit_event
except ImportError:
    def emit_event(*args, **kwargs): pass

def main():
    # Handle both stdin (JSON) and argv[1] (legacy Claude)
    input_text = ""
    if len(sys.argv) > 1:
        input_text = sys.argv[1]
    else:
        try:
            input_text = sys.stdin.read()
        except EOFError:
            pass

    # Only check if the edit targeted MEMORY.md
    if "MEMORY.md" not in input_text:
        # Don't print allow here yet, need to see if it's JSON context
        pass
    else:
        memory_file = Path("~/.claude/projects/-Users-{{user_handle}}-Projects-{{workspace_dir}}/memory/MEMORY.md").expanduser()
        if memory_file.exists():
            try:
                line_count = len(memory_file.read_text().splitlines())
                
                if line_count >= 190:
                    msg = f"MEMORY.md is at {line_count}/200 lines — CRITICAL. Extract content to topic files NOW before adding anything."
                    print(msg, file=sys.stderr)
                    emit_event(hook="memory-guardrail", decision="block", reason=f"MEMORY.md ≥190 lines ({line_count})", event="PostToolUse", tool="apply_patch")
                    # For Gemini/Codex
                    print(json.dumps({"decision": "deny", "reason": msg}))
                    return
                elif line_count >= 180:
                    msg = f"MEMORY.md is at {line_count}/200 lines — approaching limit. Consider extracting stable sections to topic files."
                    print(msg, file=sys.stderr)
                    emit_event(hook="memory-guardrail", decision="warn", reason=f"MEMORY.md ≥180 lines ({line_count})", event="PostToolUse", tool="apply_patch")
            except Exception as e:
                print(f"Error reading memory file: {e}", file=sys.stderr)

    # Allow path: silent exit. Legacy `{"decision": "allow"}` violates schema
    # (decision is "approve"|"block" only); silent stdout means continue.

if __name__ == "__main__":
    main()
