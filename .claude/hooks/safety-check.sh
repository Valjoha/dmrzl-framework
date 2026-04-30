#!/bin/bash
# AUDIENCE: public
# Safety hook — blocks destructive shell commands
# Called by Claude Code pre-tool-use hook for Bash tool
# Input: JSON on stdin with tool_input.command

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('command',''))" 2>/dev/null)

[ -z "$COMMAND" ] && exit 0

# Block destructive patterns
if echo "$COMMAND" | grep -qE '(rm\s+-rf|rm\s+-r\s+/|git\s+reset\s+--hard|git\s+clean\s+-fd|git\s+checkout\s+--\s+\.)'; then
  echo "BLOCKED: Destructive command detected: $COMMAND" >&2
  echo "Use 'trash' instead of 'rm', or ask user explicitly for destructive operations." >&2
  exit 2
fi

# Block git commit/push unless user explicitly asked.
# Bypass: prefix command with PD_ALLOW_COMMIT=1 after user confirmation.
if echo "$COMMAND" | grep -qE '(git\s+commit|git\s+push)'; then
  if [ -z "$PD_ALLOW_COMMIT" ] && ! echo "$COMMAND" | grep -q 'PD_ALLOW_COMMIT=1'; then
    echo "BLOCKED: git commit/push requires explicit user request." >&2
    echo "After user confirms, prefix command with 'PD_ALLOW_COMMIT=1 ' to bypass." >&2
    exit 2
  fi
fi

exit 0
