---
description: "End-of-session distillation and handoff. Use when user says 'handoff', 'wrap up', 'end session', or is finishing a work session. Extracts decisions, patterns, state changes into memory files and writes HANDOFF.md. Do NOT use mid-session — use save-session for incremental saves."
audience: public
---
# Session Handoff

Write the handoff **inline** — no secretary agent needed.

## Procedure

0. Log session end: `bash .claude/scripts/next-session.sh --end <session_number>`
1. Gather data in parallel:
   - CI: `gh run list --repo {{github_owner}}/{{project_name}} --workflow=ci.yml --limit 1`
   - Current HANDOFF: `mcp__obsidian__read-note(vault: "vault", filename: "HANDOFF.md", folder: "dmrzl/session")`
2. Synthesize from conversation context (Template below)
3. Write vault files inline (`mcp__obsidian__edit-note` or `Edit`):
   - `vault/dmrzl/session/HANDOFF.md` — full handoff
   - `vault/{{project_slug}}/log/decisions.md` — append new decisions if any
   - `vault/{{project_slug}}/log/patterns.md` — append new patterns if any
   - `vault/{{project_slug}}/log/project-state.md` — update if architecture changed
4. Extract insights: `python3 .claude/scripts/extract-insights.py --session $CURRENT_SESSION_UUID` (UUID = visible in JSONL filename). 0 new is fine.
5. Session rating — ask inline: "Rate session N? (1-5)" (translated to your configured `LANGUAGE`). NOT `AskUserQuestion` — plain text. Append via Bash (Obsidian MCP can't handle .jsonl):
   ```bash
   echo '{"session":N,"date":"YYYY-MM-DD","rating":R,"title":"...","models":[...],"platform":"Claude Code"}' >> vault/dmrzl/session/session-ratings.jsonl
   ```

## Template (~50 lines max)

```markdown
---
compact: "S{N} | {what changed}. {state}. Next: {1-2 items}."
---

## Current Session: {date} (Session {N}: {title})

### Summary
{2-3 sentences: what was done and why}

### Key Accomplishments
- {bullet 1}
- {bullet 2 — max 5}

### Decisions Made
{Only formal decisions. "None" if pure implementation session.}

### Current State
- **Branch (CW):** {branch} — {status}
- **Branch (PD):** {branch} — {status}
- **CI:** {pass/fail}

### Known Issues (Carried Forward)
{Numbered list. Remove resolved.}

### Next Steps
1. {highest priority}
2. {second — max 3}

### Token Usage
{1 line: requests, output tokens, cost, models}

---
**Session**: {date} | **Models**: {list} | **Status**: Complete.

---

## Previous Session: {date} (Session {N-1}: {title})
{2-3 sentences from previous Current Session}
```

## Stale Page Review (Karpathy Wiki Discipline)

For each vault directory modified this session:
1. Find files with `status: stale`
2. Read each → decide: outdated (update + status: active + bump `updated:`), obsolete (move to archive/ + status: archived), still valid (mark active)
3. Report in handoff: "Stale review: N checked, M updated, K archived"
4. If any changes: append to `vault/dmrzl/session/ops-log.md`: `YYYY-MM-DD | S### | UPDATE | path | stale review: <action>`

## Rules

- Move previous "Current Session" → "Previous Session" (keep only 2 visible)
- **Always update `compact` frontmatter** — max 200 chars, survives compaction
- No "Session Texture" (subjective, not actionable)
- No full files-changed list (git log has it)
- Patterns → append to `vault/{{project_slug}}/log/patterns.md`, not HANDOFF
- Platform + models in footer line, not separate section
