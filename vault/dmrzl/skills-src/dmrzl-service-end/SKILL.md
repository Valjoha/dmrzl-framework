---
name: dmrzl-service-end
description: "Exit a service-mode session cleanly. Use when the user wants to leave service mode without converting it to a normal tracked session — phrases like 'end service', 'service end', 'service session done', 'exit service', 'wrap service', 'close service'. Removes the marker, deletes the tmp scratch dir, prints duration and number consumed. Does NOT write any handoff file, INDEX row, or rating. The session number stays a gap forever. For conversion to a normal session use dmrzl-service-promote instead."
audience: public
category: session
platforms: [general]
cache_safe: false
tags: [session, service, meta]
related_skills: [dmrzl-service, dmrzl-service-promote]
type: config
status: active
---
# DMRZL Service End

> Up: [[dmrzl/skills|Skills]]

Cleanly exit a service-mode session. Null-write equivalent of dmrzl-handoff.

## When to use

- The service-mode meta-work is done and was not meant to enter the project record.
- User says 'end service', 'service done', 'wrap service', 'exit service'.

## When NOT to use

- Mid-session — service mode is fine running for a while; only end when actually done.
- The work turned out to be worth recording as a project session — use `dmrzl-service-promote` instead.

## Procedure

1. Verify the marker exists for this process tree:
   ```bash
   python3 .platform/runtime/hooks/_service_mode.py status
   ```
   Exit 1 means no active service session — refuse to do anything; tell the user.

2. Read marker fields (session_number, started_at, tmp_dir).

3. Compute duration: `now - started_at`.

4. Remove the marker file and tmp dir via the helper's `clear_marker(remove_tmp=True)`.

5. Verify removal: a second `is-active` call must exit 1.

6. Print a concise summary in the user's chat language. Persona feminine forms.
   - Session number consumed (gap in INDEX is expected).
   - Duration.
   - Confirmation that no traces remain in vault, telemetry, or feedback logs.
   - Reminder that auto-memory was not gated by hooks; if any memory-worthy fact was queued, surface it now for the user to decide.

## Do NOT

- Do NOT write to `vault/dmrzl/session/handoffs/`, INDEX.md, decisions.md, patterns.md, or session-ratings.jsonl.
- Do NOT call `next-session.py --end` (which logs to session-log.jsonl) — service sessions are not in that log.
- Do NOT auto-invoke dmrzl-handoff. They are separate ceremonies.

## Edge cases

- Marker is for a different PID (orphan from a parallel session): refuse and tell the user. Use `--takeover` argument to forcibly clear, but warn that it may break the other live session.
- Crash between marker-read and marker-clear: `cleanup_stale()` in the next normal session will catch it via PID liveness check.
- Tmp dir already deleted manually: `clear_marker` is idempotent on tmp.

## Args

- `--takeover` — clear the marker regardless of whose PID it points to. Use for crash recovery only.

## See also

- Activate: `dmrzl-service`.
- Promote to normal: `dmrzl-service-promote`.
