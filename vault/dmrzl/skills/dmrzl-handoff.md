---
name: session-handoff
tags: [dmrzl, skill, session]
type: config
status: active
description: "End-of-session distillation and handoff. Use when user says 'handoff', 'wrap up', 'end session', or is finishing a work session. Extracts decisions, patterns, state changes into memory files and finalizes the per-session handoff file. Do NOT use mid-session — use save-session for incremental saves."
audience: public
---
# Session Handoff & Distillation — Long Form

> Up: [[dmrzl/skills|Skills]] · Short form: `.claude/skills/dmrzl-handoff/SKILL.md` · `.gemini/skills/dmrzl-handoff/SKILL.md`

Use this protocol at the end of every work session (or when explicitly asked to wrap up). Spec: `vault/{{project_slug}}/management/plans/2026-05-02-handoff-per-session-split-spec.md`.

## Per-Session Model

Every session has its own file at `vault/dmrzl/session/handoffs/S{N}.md`. `next-session.sh` creates it as a `status: active` stub at session start. `dmrzl-handoff` finalizes it with `status: complete` and full content.

`vault/dmrzl/session/INDEX.md` is a markdown table — one row per session — that gives a fast overview without loading individual session files. Updated via `.claude/scripts/append-index-row.py` (mkdir-locked, idempotent replace per session number).

There is **no longer** a single shared `HANDOFF.md`. The pre-S171 history lives frozen in `vault/archive/HANDOFF-pre-split.md`.

## Platform Tools

- **Claude Code**:
  - Vault reads: Obsidian MCP (`mcp__obsidian__read-note`) — primary. Edit tool for writes.
  - Rule: never use `Read` tool on `vault/` files when Obsidian MCP is available.
- **Gemini CLI**:
  - Direct file-read tools (`read_file`); same paths as Claude.
- **Codex**:
  - Filesystem reads (`rg`, `sed`); targeted writes via Codex tools.
  - Same vault paths; do not invent shadow copies.

## Cross-Platform Rules

- `S{N}.md` is **per-session** and is owned by the platform that opened that session number. Hard-coded per skill: Claude → `platform: claude-code`, Gemini → `platform: gemini-cli`, Codex → `platform: codex`.
- `INDEX.md` is shared continuity for all platforms. Append-only via `append-index-row.py`.
- `models:` frontmatter list is the contributor list for that session, not just the orchestrator.
- `compact:` is ≤200 chars and survives context compaction. The agent can recover state by re-reading its own `S{N}.md` after compaction.

## Steps

1. **Read own stub** (`vault/dmrzl/session/handoffs/S{N}.md`) to confirm session number and start time.
2. **Extract decisions** → append to `vault/{{project_slug}}/log/decisions.md`
3. **Extract patterns/gotchas** → append to `vault/{{project_slug}}/log/patterns.md`
4. **Update architecture** → `vault/{{project_slug}}/log/project-state.md` (if changed)
5. **Write `S{N}.md`** with `status: complete` and full body (see schema below). MUST happen before step 6.
6. **Append-index row** via `.claude/scripts/append-index-row.py` (locked, idempotent — replaces the `(in progress)` row).
7. **Session rating** — ask user inline (`Оцінка сесії N? (1–5)`), append to `vault/dmrzl/session/session-ratings.jsonl`.

## S{N}.md Schema

```yaml
---
tags: [dmrzl, session, handoff]
type: handoff
status: complete
session: 171
date: 2026-05-02
platform: claude-code   # claude-code | codex | gemini-cli
started: 17:30
ended: 19:45
models: [opus, sonnet]
rating: 5
compact: "≤200 chars summary that survives compaction"
title: "short noun phrase"
---
```

Body sections (markdown): Summary · Key Accomplishments · Decisions Made · Current State · Known Issues · Next Steps · Token Usage. No "Previous Session" rotation (each session is self-contained). No subjective "Session Texture" (not actionable).

## Session Rating (Step 7)

After `S{N}.md` is finalized:

1. Ask inline (plain text, no `AskUserQuestion`): `Оцінка сесії N? (1–5)`
2. Append JSON line:
   ```bash
   echo '{"session":N,"date":"YYYY-MM-DD","rating":R,"title":"...","models":[...],"platform":"Claude Code"}' \
       >> vault/dmrzl/session/session-ratings.jsonl
   ```
3. Update `rating:` field in `S{N}.md` frontmatter and re-run `append-index-row.sh` (idempotent — overwrites the existing row with new rating).

## Daily Log Format

Use template from `vault/{{project_slug}}/log/TEMPLATE.md` if one exists. Key sections: Tasks, Decisions, Learned, Handoff, Tags. Tags enable search: `#spawn #refactor #bug #performance #architecture`. Daily log is independent from `S{N}.md` — both can be updated.
