#!/bin/bash
# AUDIENCE: public
# MEMORY.md line count guardrail
# Fires PostToolUse on Edit|Write — warns when MEMORY.md approaches 200-line limit

INPUT="$1"
MEMORY_FILE="$HOME/.claude/projects/-Users-{{user_handle}}-Projects-{{workspace_dir}}/memory/MEMORY.md"

# Only check if the edit targeted MEMORY.md
if ! echo "$INPUT" | grep -q 'MEMORY.md'; then
  exit 0
fi

if [ ! -f "$MEMORY_FILE" ]; then
  exit 0
fi

LINES=$(wc -l < "$MEMORY_FILE")

if [ "$LINES" -ge 190 ]; then
  echo "MEMORY.md is at $LINES/200 lines — CRITICAL. Extract content to topic files NOW before adding anything."
  exit 2
elif [ "$LINES" -ge 180 ]; then
  echo "MEMORY.md is at $LINES/200 lines — approaching limit. Consider extracting stable sections to topic files."
fi

exit 0
