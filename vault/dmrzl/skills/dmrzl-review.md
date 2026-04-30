---
name: dmrzl-review
tags: [dmrzl, skill]
type: skill
status: active
description: "Two-stage code review for changed files. Stage 1: spec/plan compliance. Stage 2: code quality (ECS patterns, security, performance). Use when user says 'review code', 'check my changes', 'review PR', 'prepare for merge', or after completing a significant task (2+ files or new public API). Do NOT use for git operations."
audience: public
---

# Two-Stage Code Review

> Up: [[dmrzl/skills|Skills]]

Two-stage review system for {{project_name}}. Replaces Light/Deep mode.

## Platform Tools (Claude Code)

- **Diff analysis**: `git diff`, `git log` via Bash
- **Code search**: Rider MCP (`search_in_files_by_text/regex`). Fallback: `Grep`/`Glob`.
- **C# reading**: Rider MCP (`get_file_text_by_path`). Fallback: `Read` tool.
- **Vault reads**: Obsidian CLI. Fallback: `Grep`/`Glob`.
- **Console check**: Unity MCP (`read_console`) for compile errors.

## When to Trigger

- After any task that modifies 2+ files or adds new public API
- On user request ("review code", "check my changes", "review PR")
- Single-file tweaks and config changes skip review

## Stage 1: Spec Compliance

Dispatch as Sonnet subagent, read-only.

**Prompt template:**
```
Review this implementation against the plan/brief.

PLAN: [paste relevant plan section or brief]
CHANGES: git diff [BASE_SHA]..[HEAD_SHA]

Check:
1. Does implementation match the plan's objective?
2. Are all specified files touched?
3. Are there unplanned changes (scope creep)?
4. Are there planned items missing?

Output: PASS or FAIL with specific gaps.
```

## Stage 2: Code Quality

Dispatch as Sonnet subagent, read-only.

**Prompt template:**
```
Review code quality for these changes.

CHANGES: git diff [BASE_SHA]..[HEAD_SHA]
CONTEXT: [1-2 sentences about what was built]

Check:
1. ECS conventions (ECB for structural changes, Burst-compatible, no managed types in jobs)
2. Security (no injection, no data leaks)
3. Performance (no per-frame allocations, proper query filters)
4. Naming and patterns (match existing codebase conventions)

Output: Critical / Important / Minor issues list, or CLEAN.
```

## Issue Handling

- **Critical**: fix immediately before proceeding
- **Important**: fix before merge
- **Minor**: note for later, do not block
- **Disagreement**: push back with technical reasoning, reviewer is advisory

## ECS-Specific Checklist (preserved from code-reviewer agent)

### ECS Safety (Critical)
- Structural changes use collect-first pattern (EntityCommandBuffer)
- Singleton resets happen BEFORE structural changes in same frame
- No `SetSingleton` after `CreateEntity` in same system update
- `EntityQuery` filters match intended component combinations
- System ordering attributes (`UpdateBefore`/`UpdateAfter`) correct
- No accessing destroyed/nonexistent entities

### Burst/Jobs Compatibility
- No managed types (string, class, List<>) inside Burst-compiled code
- Proper `NativeContainer` usage (allocation, disposal, safety handles)
- `[BurstCompile]` on systems and jobs that should be Burst-compiled
- No `Debug.Log` inside Burst

### Logic & Correctness
- No off-by-one errors in loops, array access, hex coordinate math
- Edge cases handled: empty collections, zero values, first/last wave
- Float comparisons use epsilon, not `==`
- No uninitialized `NativeArray`/`NativeList` read before write

### Project Conventions
- `public static` methods for testable math (Extract-to-Static pattern)
- Namespace: `Core.Placement.*`
- FactionMembership is a bitmask (Alpha=0x01, Beta=0x02), not enum
- LogCategory matches system domain
- `Helpers.Log` — never `Debug.Log`

### Testability
- New math/logic has corresponding EditMode test or is Extract-to-Static testable
- Static methods are pure (no side effects, no ECS world dependency)

## Output Format

```markdown
## Code Review: [scope summary]

**Stage 1 (Spec Compliance):** PASS | FAIL
**Stage 2 (Code Quality):** CLEAN | [issue count]
**Files reviewed:** N files, +X/-Y lines

### Critical
- [file:line] — [issue description]

### Important
- [file:line] — [issue description]

### Minor
- [file:line] — [suggestion]

### Verdict
[APPROVE | REQUEST CHANGES | DISCUSS]
[1-2 sentence summary]
```

## Rules

- Always read the actual code — never review from diff summary alone
- Reference specific lines, not vague "this could be better"
- For ECS code, always check against `vault/{{project_slug}}/technical/ecs-rules.md`
- Never auto-approve — always provide at least one observation
