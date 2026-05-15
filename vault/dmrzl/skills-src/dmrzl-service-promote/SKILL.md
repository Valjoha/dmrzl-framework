---
name: dmrzl-service-promote
description: "Convert an active service-session into a normal tracked session retroactively. Use when the work in a service session turned out to be valuable and should produce a handoff after all — phrases like 'promote service', 'service promote', 'keep this session', 'actually save this', 'convert to normal'. Creates the S{N}.md stub, appends the INDEX row, removes the marker, restores hooks. The earlier service-mode portion of the session is not retroactively logged; only post-promotion activity is tracked."
audience: public
category: session
platforms: [general]
cache_safe: false
tags: [session, service, meta]
related_skills: [dmrzl-service, dmrzl-service-end, dmrzl-handoff]
type: config
status: active
---
# DMRZL Service Promote

> Up: [[dmrzl/skills|Skills]]

Retroactively convert a service-session into a normal tracked session.

## When to use

- A service-mode session uncovered something worth keeping, and the user wants a handoff for it.
- User says 'promote service', 'keep this', 'actually save this', 'convert to normal'.

## When NOT to use

- Service mode is done and the meta-work was not meant for the project record — use `dmrzl-service-end`.
- No active marker — there is nothing to promote. Tell the user.
- More than one service session is running on this host — promote only the one whose marker matches our process tree.

## Procedure

1. Verify the marker is active for this process tree:
   ```bash
   python3 .platform/runtime/hooks/_service_mode.py status
   ```
   If not active, refuse and explain.

2. Read marker fields. Capture `session_number` and `started_at`.

3. Confirm with the user via `AskUserQuestion`:
   - Question: "Promote service session N to normal? Tracking restarts; earlier service-mode work will not be retroactively logged."
   - Default: Yes.
   - Cancel option: keep service mode active.

4. On user confirmation:
   - Remove the marker via the helper's `clear_marker(remove_tmp=False)`. Tmp dir is preserved — user may want artefacts.
   - Verify hooks are restored: `is-active` must exit 1.
   - Create the stub + INDEX row retroactively:
     ```bash
     python3 .claude/scripts/next-session.py --resume <N> --start-time <ISO>
     ```
   - Update `.claude/feedback-loops/.current-session` to point at N (so trackers attribute future writes).

5. Print a brief confirmation in chat language. Persona feminine forms.
   - Session N is now tracked.
   - Frontmatter notes `promoted_from_service: true` (set by `next-session.py --resume`).
   - Reminder: end this session with `dmrzl-handoff` as usual.

## Do NOT

- Do NOT attempt to recover skill/agent/file telemetry from the service-mode portion. It was discarded by design.
- Do NOT clobber an existing `S{N}.md` — `next-session.py --resume` refuses; surface that error.
- Do NOT promote without explicit confirmation. Promotion is irreversible without manual cleanup.

## Edge cases

- Counter has advanced past N (another session ran in parallel). `--resume` refuses; surface the error and ask the user how to proceed (likely accept the gap and use a fresh number going forward).
- Stub file already exists for N (manual creation, race). `--resume` refuses; tell the user to inspect.
- After promotion, dmrzl-handoff runs as normal. The handoff body should mention promotion in its first line so the reader understands the partial telemetry.

## See also

- Activate: `dmrzl-service`.
- Exit without promoting: `dmrzl-service-end`.
- Standard handoff: `dmrzl-handoff`.
