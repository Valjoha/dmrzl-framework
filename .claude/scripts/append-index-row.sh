#!/usr/bin/env bash
# AUDIENCE: public
# Atomically prepend a row to vault/dmrzl/session/INDEX.md (newest first).
#
# Usage: append-index-row.sh <session> <date> <platform> <title> <compact> <rating>
#
# All args are positional — no embedded `|` hazard. Pipe chars inside any field
# are replaced with U+FF5C (｜) before insertion. Lock is held across awk+rename
# so two concurrent invocations cannot race.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/../.." && pwd)"
INDEX="$WORKSPACE/vault/dmrzl/session/INDEX.md"
LOCK_DIR="$WORKSPACE/.claude/index.lock"

# Pipe-escape (markdown table delimiter)
esc() { printf '%s' "$1" | tr '|' '｜'; }

session="$(esc "${1:?session required}")"
date="$(esc "${2:?date required}")"
platform="$(esc "${3:?platform required}")"
title="$(esc "${4:-}")"
compact="$(esc "${5:-}")"
rating="$(esc "${6:--}")"

new_row="| ${session} | ${date} | ${platform} | ${title} | ${compact} | ${rating} |"

if [ ! -f "$INDEX" ]; then
    echo "ERROR: INDEX.md not found at $INDEX" >&2
    echo "(run migrate-handoff.sh to create it)" >&2
    exit 1
fi

# Acquire lock (retry up to 3s). NO stale-cleanup: lock window is ~10ms.
attempts=0
while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    attempts=$((attempts + 1))
    if [ "$attempts" -gt 30 ]; then
        echo "ERROR: INDEX lock timeout (3s) — investigate $LOCK_DIR" >&2
        exit 1
    fi
    sleep 0.1
done
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

# If a row for this session already exists, replace it in place (idempotent for
# the stub→complete transition). Otherwise prepend after the table separator.
if grep -q "^| ${session} |" "$INDEX"; then
    awk -v sess="${session}" -v new_row="$new_row" '
        $0 ~ "^\\| " sess " \\|" { print new_row; next }
        { print }
    ' "$INDEX" > "$INDEX.tmp" && mv "$INDEX.tmp" "$INDEX"
else
    awk -v new_row="$new_row" '
        BEGIN { inserted = 0 }
        !inserted && /^\|[ -]+\|[ -]+\|[ -]+\|[ -]+\|[ -]+\|[ -]+\|/ {
            print
            print new_row
            inserted = 1
            next
        }
        { print }
    ' "$INDEX" > "$INDEX.tmp" && mv "$INDEX.tmp" "$INDEX"
fi
