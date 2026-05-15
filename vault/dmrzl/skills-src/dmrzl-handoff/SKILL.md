---
name: dmrzl-handoff
description: "End-of-session distillation and handoff. Use when user says 'handoff', 'wrap up', 'end session', or is finishing a work session. Extracts decisions, patterns, state changes into memory files and finalizes the per-session handoff file. Do NOT use mid-session — use save-session for incremental saves."
audience: public
category: session
platforms: [general]
cache_safe: false
tags: [session-end, distillation, memory]
related_skills: [dmrzl-start, dmrzl-dream]
requires_tools: [obsidian-mcp-rs]
type: config
status: active
---
# Session Handoff

Write the handoff **inline** — no secretary agent needed.

## Procedure

0. Log session end: `python3 .claude/scripts/next-session.py --end <session_number>`
1. Gather data in parallel:
   - CI: `gh run list --repo Valjoha/{{project_name}} --workflow=ci.yml --limit 1`
   - Own stub: read `vault/dmrzl/session/handoffs/S{N}.md` (created by `next-session.py` at session start; has `status: active`)
2. Synthesize from conversation context (Template below).
3. **Ask rating inline FIRST** — "Оцінка сесії N? (1-5)". NOT `AskUserQuestion` — plain text. Hold the value `R` for steps 4-5 below; without it the handoff frontmatter and INDEX row both end up `-`.
4. **Write `vault/dmrzl/session/handoffs/S{N}.md`** — set `status: archived` (canonical per S232 frontmatter normalization — finished handoffs are frozen reference), fill all frontmatter fields per template (including `rating: R` from step 3). This MUST happen BEFORE step 5 — INDEX must never reference an incomplete file.
5. **Append-index row** — call (with `R` from step 3, NOT `-`):
   ```bash
   python3 .claude/scripts/append-index-row.py \
       <N> <date> claude-code <title> <compact-≤80-chars> <R>
   ```
   The script handles locking and idempotent replace (overwrites the existing `(in progress)` row for this session).
6. Write append-only logs (Edit tool, no MCP needed):
   - `vault/{{project_slug}}/log/decisions.md` — append new decisions if any
   - `vault/{{project_slug}}/log/patterns.md` — append new patterns if any
   - `vault/{{project_slug}}/log/project-state.md` — update if architecture changed
7. Extract insights: `python3 .claude/scripts/extract-insights.py --session $CURRENT_SESSION_UUID` (UUID from JSONL filename). 0 new is fine.
8. Append rating to jsonl (uses `R` from step 3):
   ```bash
   echo '{"session":N,"date":"YYYY-MM-DD","rating":R,"title":"...","models":[...],"platform":"Claude Code"}' >> vault/dmrzl/session/session-ratings.jsonl
   ```
9. Regenerate DIGEST (V4 Phase 1.1 — token-optimized session compression):
   ```bash
   python3 .claude/scripts/vault-digest.py
   ```
   Writes `vault/dmrzl/session/DIGEST.md` (~300-token compressed snapshot). Non-fatal if exceeds cap — script warns. `dmrzl-start` activation gated separately on V4 baseline lock.

## Platform Value (Hard-Coded Per Skill)

**This skill writes `platform: claude-code`.** Codex+Gemini invocations override platform at SessionStart-hook time (`PLATFORM` env captured by `telemetry-stop.py`); the same vault-canonical SKILL.md generates the Codex/Gemini stubs at `.agents/skills/dmrzl-handoff/SKILL.md`.

Do NOT read `platform:` from env at handoff time — env may have drifted across context compaction.

## Template (S{N}.md content)

```markdown
---
tags: [dmrzl, session, handoff]
type: handoff
status: archived
session: {N}
date: {YYYY-MM-DD}
platform: claude-code
started: {HH:MM}
ended: {HH:MM}
models: [opus, sonnet]
rating: {1-5 or null}
compact: "{≤200 chars summary that survives compaction}"
title: "{short noun phrase}"
schema_version: 2
---

# Session {N}

> Up: [[../INDEX|INDEX]]

## Summary
{2-3 sentences: what was done and why}

## Key Accomplishments
- {bullet 1}
- {bullet 2 — max 5}

## Decisions Made
{Only formal decisions. "None" if pure implementation session.}

## Current State
- **Branch (CW):** {branch} — {status}
- **Branch (PD):** {branch} — {status}
- **CI:** {pass/fail}

## Known Issues (Carried Forward)
{Numbered list. Remove resolved.}

## Next Steps
1. {highest priority}
2. {second — max 3}

## Token Usage
{1 line: requests, output tokens, cost, models}
```

## Stale Page Review (Karpathy Wiki Discipline)

For each vault directory modified this session:
1. Find files with `status: stale`
2. Read each → decide: outdated (update + status: active + bump `updated:`), obsolete (move to archive/ + status: archived), still valid (mark active)
3. Report in handoff: "Stale review: N checked, M updated, K archived"
4. If any changes: append to `vault/dmrzl/session/ops-log.md`: `YYYY-MM-DD | S### | UPDATE | path | stale review: <action>`

## Rules

- One file per session (`handoffs/S{N}.md`). No "Previous Session" rotation.
- **Always update `compact` frontmatter** — max 200 chars, survives compaction.
- Strict ordering: S{N}.md BEFORE `append-index-row.py`. INDEX must never reference an incomplete file.
- No "Session Texture" (subjective, not actionable).
- No full files-changed list (git log has it).
- Patterns → append to `vault/{{project_slug}}/log/patterns.md`, not the session file.
- Models stay in frontmatter (`models:`), not a separate footer section.
- **`schema_version: 2`** is mandatory in every new handoff. If a field truly cannot be captured at runtime (e.g. session crashed before close), write the literal string `not-captured-at-runtime` — never `null`, `~`, or empty. Audit script: `.claude/scripts/handoff_audit.py --report`.
