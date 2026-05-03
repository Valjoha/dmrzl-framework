---
name: dmrzl-spec
tags: [dmrzl, skill]
type: skill
status: active
description: "Deep feature specification and design through collaborative dialogue before implementation. Use when user says 'spec this feature', 'plan before coding', 'what are the edge cases', 'design this', 'brainstorm', or before any big feature or significant behavior change. Hard gate: no code until design approved. Produces a plan saved to vault/{{project_slug}}/management/plans/. Do NOT use for small tasks, bug fixes, or hotfixes."
audience: public
---

# DMRZL Spec

> Up: [[dmrzl/skills|Skills]]

Develop a thorough implementation spec by asking non-obvious clarifying questions before writing any code.

## Platform Tools (Claude Code)

- **Vault reads** (specs, architecture): Obsidian CLI (`obsidian read file=X`, `obsidian search query="X"`). Fallback: `Grep`/`Glob`.
- **Codebase exploration**: Rider MCP (`search_in_files_by_text/regex`) or `Grep`/`Glob`. Use Explore subagents for broad scans.
- **Plan writes**: `Write` tool (new plan file) or `Edit` tool (updates).

## When to Use

- Before any feature that touches 3+ files or systems
- When the initial plan feels too short or vague
- When you want to understand edge cases before committing to an approach

## Workflow

### Status Line
Set task phase at start, clear on exit:
```bash
echo "planning" > ~/.claude/task-phase   # on start
rm -f ~/.claude/task-phase 2>/dev/null    # on exit
```

### Phase 1: Understand
1. Read the user's feature description or plan file
2. Spin up 3-5 Explore subagents to understand relevant parts of the codebase
3. Identify: affected systems, data flows, existing patterns, potential conflicts

### Phase 2: Interview
4. Ask the user 15-25 non-obvious clarifying questions using the ask question tool
5. Questions should cover:
   - Edge cases the user may not have considered
   - Interaction with existing systems
   - Error handling and failure modes
   - Performance implications
   - User experience details
   - What should NOT change
6. Group questions by theme (architecture, UX, data, safety)
7. Wait for answers before proceeding

### Phase 3: Spec
8. Write a detailed implementation plan (target: 300-700 lines) covering:
   - Summary of decisions made
   - Step-by-step implementation with file paths
   - Edge cases and how they're handled
   - Testing strategy
   - Rollback plan
9. Save plan to `vault/{{project_slug}}/management/plans/YYYY-MM-DD-feature-name.md`
10. Present plan for user approval

## Variant: DMRZL Spec Explorer

If you need deeper codebase understanding before asking questions:
- Read the plan
- Spin up 3-5 Explore subagents in relevant parts of the codebase
- Use their findings to ask better, more specific questions
- Then proceed with the Interview phase

## Output

Plan file saved to `vault/{{project_slug}}/management/plans/` with frontmatter:
```yaml
---
tags: [darwin, plan]
type: plan
status: draft
feature: "feature-name"
date: YYYY-MM-DD
---
```

### Phase 4: Reader Testing

After the plan is written and before presenting for approval:

11. Spawn a fresh **Explore subagent** with NO prior context about this feature
12. Give it ONLY the plan file path and ask:
    - "Read this plan and list every question you'd need answered before implementing it"
    - "Identify any ambiguities, missing edge cases, or unclear decisions"
13. Review the subagent's questions:
    - If it asks questions the plan SHOULD have answered → **gap found**, fix the plan
    - If it asks questions outside scope → plan is clear, proceed
    - If it misunderstands intent → plan wording is ambiguous, clarify
14. Repeat with a second subagent if major gaps were found
15. Present the validated plan to the user for approval

**Why Reader Testing works:** A fresh agent has zero context bleed — it reads the plan exactly as a future coder agent would. If it can't implement from the plan alone, the plan needs more detail.

## Iteration Tracking

Plans support versioning. When revising a plan after user feedback:
- Keep the same file, add a `## Revision History` section at the bottom
- Format: `### vN (YYYY-MM-DD) — [summary of changes]`
- Never delete previous versions from history — append only

## Design Gate

### Hard Gate
Any new feature or significant behavior change MUST go through this skill.
No code until design is approved by user. Exception: hotfixes for critical bugs.

### Spec Review Loop (AUTOMATIC — Phase 5)
After writing a specification (Phase 3 output):
1. Dispatch spec-reviewer subagent (Sonnet, read-only) immediately
2. If gaps found — fix, re-dispatch
3. Max 3 iterations, then escalate to user
4. User confirms final version before implementation
This is not optional — every spec invocation that produces a written spec triggers the review loop.

### Handoff
After spec is approved, invoke writing-plans skill for implementation plan.

## Rules

- Never skip the interview phase
- Never skip Reader Testing (Phase 4) — blind spots are invisible to the author
- Never skip Spec Review Loop (Phase 5) — automated quality gate
- Never implement before the plan is approved
- Questions should reveal things the user hadn't thought about
- The plan must be specific enough that a coder agent can implement it without asking more questions
