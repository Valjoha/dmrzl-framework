---
name: dmrzl-spec
description: "Deep feature specification and design through collaborative dialogue before implementation. Use when user says 'spec this feature', 'plan before coding', 'what are the edge cases', 'design this', 'brainstorm', 'let's think through', or before any big feature or significant behavior change. Hard gate: no code until design approved. Produces a plan saved to vault/{{project_slug}}/management/plans/. Do NOT use for small tasks, bug fixes, or hotfixes."
audience: public
category: workflow
platforms: [general]
cache_safe: true
tags: [design, spec, brainstorm, planning, hard-gate]
related_skills: [dmrzl-grill, dmrzl-research, dmrzl-review]
requires_tools: [obsidian-mcp-rs]
type: config
status: active
---
# Spec Developer + Design Gate
Load full instructions from `vault/dmrzl/skills/dmrzl-spec.md`.

## Design Before Implementation (Hard Gate)
Any new feature or significant behavior change MUST go through this skill.
No code until design is approved by user. Exception: hotfixes for critical bugs.

## Workflow
1. Explore project context (files, docs, recent commits)
2. Ask clarifying questions — one at a time, 20+ for big features
3. Propose 2-3 approaches with trade-offs and recommendation
4. Present design sections, get user approval after each
5. Write spec to `vault/{{project_slug}}/management/plans/YYYY-MM-DD-<topic>-spec.md`
6. **Spec review loop (AUTOMATIC):**
   - Dispatch spec-reviewer subagent (Sonnet, read-only) immediately
   - If gaps found — fix, re-dispatch
   - Max 3 iterations, then escalate to user
7. User confirms final version before implementation
8. Hand off to writing-plans skill for implementation plan
