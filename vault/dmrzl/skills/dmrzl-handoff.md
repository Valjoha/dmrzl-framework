---
name: session-handoff
tags: [dmrzl, skill, session]
type: skill
status: active
description: "End-of-session distillation and handoff. Use when user says 'handoff', 'wrap up', 'end session', or is finishing a work session. Extracts decisions, patterns, state changes into memory files and writes HANDOFF.md. Do NOT use mid-session — use save-session for incremental saves."
audience: public
---

# Session Handoff & Distillation

> Up: [[dmrzl/skills|Skills]]

Use this protocol at the end of every work session (or when explicitly asked to wrap up).

## Platform Tools

- **Claude Code**:
  - Vault reads: Obsidian CLI (`obsidian read file=X`) — primary. Grep/Glob as fallback.
  - Vault writes: `Edit` tool. New files: `Write` tool.
  - Rule: never use `Read` tool on `vault/` files when Obsidian CLI is available.
- **Codex / Pi / OpenClaw**:
  - Vault reads: direct filesystem reads (`rg`, `sed`, targeted file reads).
  - Vault writes: targeted edits through the platform's file-edit tools.
  - Rule: prefer the live vault files in `vault/dmrzl/` and `vault/{{project_slug}}/`; do not invent platform-local shadow copies.

## Cross-Platform Rules

- `HANDOFF.md` is shared continuity for all platforms. Keep it platform-agnostic.
- Always record the runtime that produced the handoff:
  - `Platform:` one of `Claude Code`, `Codex`, `Pi`, `OpenClaw`
  - `Models used:` every model that materially contributed to the session
- `Platform` is the execution surface, not the project name.
- `Models used` is the contributor list, not just the final orchestrator model.

## Steps

1. **Review today's daily log** (`vault/{{project_slug}}/log/YYYY-MM-DD.md`) if one exists
2. **Extract decisions** → append to `vault/{{project_slug}}/log/decisions.md`
3. **Extract patterns/gotchas** → append to `vault/{{project_slug}}/log/patterns.md`
4. **Update architecture** → `vault/{{project_slug}}/log/project-state.md` (if changed)
5. **Write HANDOFF.md** → `vault/dmrzl/session/HANDOFF.md`
6. **Session rating** — ask the user to rate the session (see below)

## HANDOFF.md Format

```markdown
# Session Handoff

## Current Session: YYYY-MM-DD (Session N: short title, platform session)

### Summary

One short paragraph describing the session outcome.

### Session Texture

- **Momentum:** [high/medium/low — was the session flowing or grinding?]
- **In-flight:** [what was actively being worked on when session ended]
- **Energy shift:** [did momentum change during session? when and why?]

### Key Accomplishments

1. ...

### Decisions Made

1. ...

### Current State

- what's working
- what's in progress
- what's intentionally deferred

### Known Issues

1. ...

### Next Steps

1. ...

### Previous Session

Session N-1 (YYYY-MM-DD): short reference.

---

**Session created**: YYYY-MM-DD
**Platform**: Codex
**Orchestrator**: DMRZL | Codex | Pi | OpenClaw
**Models used**: gpt-5.4, sonnet
**Status**: short end-state
**User feedback**: pending | ★N/5 — short note
```

Keep the section names stable so every platform can read and update the same structure.

## Session Rating (Step 6)

After HANDOFF.md is written, ask the user for:

1. **Rating** — "Rate this session? (1–5)" with choices:
   `["1 — failure", "2 — weak", "3 — ok", "4 — good", "5 — excellent"]`
2. **Note** — "Want to leave a note? (optional)" — free text, skip if user declines

(Translate the user-facing strings to your configured `LANGUAGE` before asking.)

Use the platform-native interaction method:
- Claude Code: `AskUserQuestion`
- Codex / Pi / OpenClaw: normal direct user prompt or the platform's equivalent input tool

Then:
- Append JSON line to `.claude/feedback-loops/session-ratings.jsonl`:
  `{"date": "YYYY-MM-DD", "rating": N, "note": "...", "ts": "ISO8601"}`
- Append `**Session rating:** ★N/5 — "note"` to today's vault memory file
- If 3+ entries exist in the log, show the rolling average (last 5 sessions)

## Daily Log Format

Use template from `vault/{{project_slug}}/log/TEMPLATE.md` if it exists. Key sections: Tasks, Decisions, Learned, Handoff, Tags.
Tags enable search: `#spawn #refactor #bug #performance #architecture`
