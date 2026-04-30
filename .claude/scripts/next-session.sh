#!/usr/bin/env bash
# AUDIENCE: public
# Atomic session counter — returns next session number and logs start time.
# Uses mkdir as a POSIX-portable atomic lock.
# Usage: bash .claude/scripts/next-session.sh
#   --peek    show current number without incrementing
#   --end N   log end time for session N

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="$(cd "$SCRIPT_DIR/../.." && pwd)"
COUNTER_FILE="$WORKSPACE/.claude/session-counter.txt"
LOCK_DIR="$WORKSPACE/.claude/session-counter.lock"
SESSION_LOG="$WORKSPACE/.claude/session-log.jsonl"

# Stale lock cleanup (>10 seconds old)
if [ -d "$LOCK_DIR" ]; then
    lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK_DIR" 2>/dev/null || echo 0) ))
    if [ "$lock_age" -gt 10 ]; then
        rmdir "$LOCK_DIR" 2>/dev/null || true
    fi
fi

# Peek mode — no lock needed, just read
if [ "${1:-}" = "--peek" ]; then
    if [ -f "$COUNTER_FILE" ]; then
        cat "$COUNTER_FILE" | tr -d '[:space:]'
    else
        echo "0"
    fi
    exit 0
fi

# End mode — log end time for a session
if [ "${1:-}" = "--end" ]; then
    session_num="${2:-}"
    if [ -z "$session_num" ]; then
        echo "ERROR: --end requires session number" >&2
        exit 1
    fi
    end_time="$(date '+%H:%M')"
    end_iso="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
    # Append end marker
    echo "{\"session\":${session_num},\"event\":\"end\",\"time\":\"${end_time}\",\"iso\":\"${end_iso}\"}" >> "$SESSION_LOG"
    echo "Session ${session_num} ended at ${end_time}"
    exit 0
fi

# Acquire lock (retry up to 3 seconds)
attempts=0
while ! mkdir "$LOCK_DIR" 2>/dev/null; do
    attempts=$((attempts + 1))
    if [ "$attempts" -gt 30 ]; then
        echo "ERROR: could not acquire session counter lock after 3s" >&2
        exit 1
    fi
    sleep 0.1
done

# Ensure lock is released on exit
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

# Read current, increment, write
if [ -f "$COUNTER_FILE" ]; then
    current=$(cat "$COUNTER_FILE" | tr -d '[:space:]')
else
    current=0
fi

# Note: we do NOT auto-close the previous session here.
# Parallel sessions are common (multiple terminals). Auto-closing session N
# when session N+1 starts would corrupt session-log.jsonl timestamps.
# Sessions are closed explicitly via --end or left open (no end = abnormal exit).

next=$((current + 1))
echo "$next" > "$COUNTER_FILE"

# Update .current-session for vault-access-tracker hooks
FEEDBACK_DIR="$WORKSPACE/.claude/feedback-loops"
[ -d "$FEEDBACK_DIR" ] || mkdir -p "$FEEDBACK_DIR"
echo "$next" > "$FEEDBACK_DIR/.current-session"

# Log session start
start_time="$(date '+%H:%M')"
start_iso="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "{\"session\":${next},\"event\":\"start\",\"time\":\"${start_time}\",\"iso\":\"${start_iso}\"}" >> "$SESSION_LOG"

echo "$next"
