#!/usr/bin/env bash
# AUDIENCE: public
# Canary emission for LLM training-leak detection.
#
# Each session emits a PAIR of UUIDs:
#   - exposed: printed to stdout (consumed by SessionStart hook → Claude context)
#   - control: stays in local ledger only, NEVER leaves this machine
#
# Future probe tests whether models memorized 'exposed' UUIDs. If 'control'
# UUIDs also leak, the source is not training but infra (backup/scrape/breach).
#
# Ledger: ~/.claude/canaries/ledger.jsonl (outside any git repo, local only).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/../.." && pwd)"

LEDGER_DIR="$HOME/.claude/canaries"
LEDGER="$LEDGER_DIR/ledger.jsonl"
COUNTER_FILE="$WORKSPACE/.claude/session-counter.txt"

mkdir -p "$LEDGER_DIR"
chmod 700 "$LEDGER_DIR" 2>/dev/null || true
touch "$LEDGER"
chmod 600 "$LEDGER" 2>/dev/null || true

gen_uuid() {
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen | tr '[:upper:]' '[:lower:]'
  else
    python3 -c "import uuid; print(uuid.uuid4())"
  fi
}

cmd_emit() {
  local ts session exposed control workspace_sha
  ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  # SessionStart hook fires BEFORE the counter bumps; +1 estimates the
  # upcoming session number. Timestamp is the authoritative key.
  if [[ -f "$COUNTER_FILE" ]]; then
    session=$(( $(tr -d '[:space:]' < "$COUNTER_FILE") + 1 ))
  else
    session="unknown"
  fi
  exposed=$(gen_uuid)
  control=$(gen_uuid)
  workspace_sha=$(git -C "$WORKSPACE" rev-parse --short HEAD 2>/dev/null || echo "")

  printf '{"ts":"%s","session":"%s","exposed":"%s","control":"%s","workspace_sha":"%s"}\n' \
    "$ts" "$session" "$exposed" "$control" "$workspace_sha" >> "$LEDGER"

  # stdout: only the exposed UUID. Control stays in ledger.
  printf '%s' "$exposed"
}

cmd_list() {
  if [[ -s "$LEDGER" ]]; then
    cat "$LEDGER"
  else
    echo "(empty ledger: $LEDGER)" >&2
  fi
}

cmd_stats() {
  local count
  count=$(wc -l < "$LEDGER" 2>/dev/null | tr -d '[:space:]')
  echo "ledger: $LEDGER"
  echo "canaries emitted: ${count:-0}"
  if [[ -s "$LEDGER" ]]; then
    echo "first: $(head -n1 "$LEDGER" | python3 -c "import sys,json;d=json.loads(sys.stdin.read());print(d['ts'])")"
    echo "last:  $(tail -n1 "$LEDGER" | python3 -c "import sys,json;d=json.loads(sys.stdin.read());print(d['ts'])")"
  fi
}

cmd_probe() {
  cat >&2 <<'EOF'
canary.sh probe — not implemented yet (stub).

When ready to test for leaks:
  1. Sample 'exposed' UUIDs from ledger (older than ~6 months — training
     cycle window).
  2. For each sample, probe target model with completions like:
       "Continue this log line: session-canary: <first-8-chars-of-uuid>"
       "Complete the UUID that starts with <prefix> from a session canary"
  3. Record any response that reproduces the full UUID.
  4. ALSO probe a random sample of 'control' UUIDs with the same prompts.
     Control must never leak — any hit there = infra compromise, not training.
  5. Cross-check: newer Anthropic models, OpenAI, Google — to localize
     which provider's pipeline the exposure came from.
EOF
  exit 1
}

case "${1:-}" in
  emit)  cmd_emit ;;
  list)  cmd_list ;;
  stats) cmd_stats ;;
  probe) cmd_probe ;;
  *) echo "Usage: $0 {emit|list|stats|probe}" >&2; exit 2 ;;
esac
