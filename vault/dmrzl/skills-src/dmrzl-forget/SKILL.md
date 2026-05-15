---
name: dmrzl-forget
description: "Retroactively delete all traces of a previously recorded session. Use when the user wants to remove session N from the project record after the fact — phrases like 'forget session N', 'delete session N', 'remove session N', 'wipe S100', 'clean session noise', 'forget N'. Targets a single session number; supports dry-run by default and only commits with explicit --commit. Trashes files (not rm); the cleanup is recoverable from the system trash. Refuses to operate on the currently active session."
audience: public
category: session
platforms: [general]
cache_safe: false
tags: [session, cleanup, retroactive]
related_skills: [dmrzl-service, dmrzl-service-end]
type: config
status: active
---
# DMRZL Forget

> Up: [[dmrzl/skills|Skills]]

Retroactive cleanup of a previously recorded session's traces.

## When to use

- A normal session turned out to be noise (scheduled checkpoint spam, single-task triviality, content-free greeting) and shouldn't pollute the project record.
- User explicitly says 'forget N', 'delete session N', 'remove session N', 'wipe S100'.

## When NOT to use

- The session is actively running. Refuse with a clear message; user must end it first.
- The session is the most recent and contained real work — they almost certainly don't want to forget it. Confirm intent before proceeding.
- Cleanup of confidential leakage from auto-memory (`~/.claude/projects/*/memory/`). That is not in scope; user must clean memory by hand.

## Procedure

### Phase 1: dry-run (default)

1. Argument validation: a single session number, format `S{N}` or `{N}`. Refuse ranges in V1.
2. Verify N is not currently active:
   - Read `.claude/feedback-loops/.current-session` — if it equals N, refuse.
   - Read service-marker — if `session_number == N`, refuse.
3. Walk the trace surfaces and build a plan. For each line print whether the action is `trash`, `edit`, or `skip` (when nothing matches).
4. Trace surfaces (V1 scope):
   - `vault/dmrzl/session/handoffs/S{N}.md` — trash
   - `vault/dmrzl/session/INDEX.md` — edit (remove the row whose first column is `N`)
   - `vault/dmrzl/session/session-ratings.jsonl` — edit (drop the line whose `session` field equals N)
   - `vault/dmrzl/session/scratchpad/*-{N}-*.md` — trash matching files
   - `vault/dmrzl/session/enriched/S{N}-*.md` — trash
   - `vault/dmrzl/session/summaries/S{N}-*.md` — trash
   - `.claude/feedback-loops/session-activity.log` — edit (drop lines whose tab-separated session field is `S{N}`)
   - `.claude/feedback-loops/.session-uuid-map` — edit (drop lines whose second column is N)
5. NOT in V1 scope (do not touch):
   - `vault/{{project_slug}}/log/decisions.md`, `patterns.md`, `project-state.md` — domain-indexed, no per-session tagging convention exists today.
   - `~/.claude/projects/.../memory/*.md` — out of scope; user must clean memory separately.
6. Print the dry-run summary and stop. Tell the user to re-run with `--commit` to execute.

### Phase 2: commit

7. Re-run the same plan computation (state may have changed since dry-run).
8. For each `trash` action: `trash <path>` (macOS native; reversible from the system trash).
9. For each `edit` action: read file, build new content with the offending lines removed, write atomically (temp file + rename under flock if available, else simple rewrite).
10. Print confirmation per file. Final tally: trashed N, edited M.

## Args

- `<N>` (required) — session number to forget. Accepts `S100` or `100`.
- `--commit` — execute the plan. Without this, runs as dry-run and only prints the plan.

## Safety

- Default is dry-run. `--commit` is required for any write/delete.
- Use `trash`, never `rm`. Files are recoverable from the system trash.
- Refuses on active session.
- Idempotent: rerun does nothing if traces are gone.

## Edge cases

- Some traces missing (e.g., S{N}.md was already manually deleted). Skip those lines; report `skip: not present`. No error.
- INDEX.md row format drift: rely on the first column matching `N` exactly inside `| N |`. If no row matches, skip with `skip: no row`.
- session-ratings.jsonl malformed lines: ignore JSON parse errors per line; only drop lines whose parsed `session` equals N.
- Multiple scratchpad files for the session (different platforms): trash all matches.

## See also

- Activate service mode (prevent future traces): `dmrzl-service`.
- Spec: `vault/{{project_slug}}/management/plans/2026-05-09-service-session-spec.md`.
