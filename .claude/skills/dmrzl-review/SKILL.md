---
description: "Multi-stage code review for changed files. Stage 1: spec/plan compliance (Sonnet). Stage 2: code quality (Sonnet). Optional Stage 3: cross-model review for blind-spot coverage. Use when user says 'review code', 'check my changes', 'review PR', 'prepare for merge', or after completing a significant task (2+ files or new public API). Do NOT use for git operations."
audience: public
---
# Three-Stage Code Review

Detailed prompts and gotchas: [REFERENCE.md](REFERENCE.md)
Review rubric (single source of truth): `vault/dmrzl/skills/review-rubric.md`

## Reviewer Stance

**Default: skeptical.** Independent evaluator, not validator. Assume code has issues until proven otherwise. Zero issues found in 100+ line diff → re-examine, you missed something.

> "Out of the box, Claude is a poor QA agent." — Anthropic Labs.

This skill exists to counteract that. Be the skeptic the generator needs.

## When to Trigger

- After any task modifying 2+ files or adding new public API
- On user request: "review code", "check my changes", "review PR"
- Skip for single-file tweaks and config changes

## Stages

### Stage 1: Spec Compliance
Dispatch Sonnet subagent (read-only) with prompt from REFERENCE.md §"Stage 1". Checks: implementation matches plan, all specified files touched, no scope creep, no missing items, acceptance criteria met. Output: PASS/FAIL with gaps.

### Stage 2: Code Quality
Dispatch Sonnet subagent (read-only) with prompt from REFERENCE.md §"Stage 2". Reviewer reads `vault/dmrzl/skills/review-rubric.md` first, then evaluates each applicable criterion as PASS/FAIL with file:line references. Severity: Critical (blocks merge) / Important (fix before merge) / Minor (note for later).


## Issue Handling

- **Critical**: fix immediately before proceeding
- **Important**: fix before merge
- **Minor**: note for later, do not block
- **Disagreement**: push back with technical reasoning, reviewer is advisory

## Logging

After review, log to unified session activity:
```bash
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ)	[review]	feature=<name>	result=<pass|fail>	issues=<count>" >> .claude/feedback-loops/session-activity.log
```
Enables tracking review pass/fail ratio over time.
