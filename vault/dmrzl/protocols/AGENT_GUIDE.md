---
type: protocol
tags: [dmrzl, protocol]
status: active
audience: public
---
# Agent Instructions Guide
> Up: [[dmrzl/identity/CORE|CORE]]

Meta-guide for creating and improving agent instructions across platforms. Primary: Claude Code. Cross-platform where noted.

## 1. Core Principles (cross-platform)

- **Progressive disclosure**: metadata (always loaded) -> instructions (on trigger) -> references (on demand).
- **Single responsibility**: 1 agent = 1 domain. Split if an agent handles 2 unrelated domains.
  - **Exception**: `dmrzl-dots` intentionally covers ECS + UI Toolkit + game balance — justified because all three share the same codebase, ECS patterns, and entity model. Routing confusion with 3 separate skills outweighed single-responsibility purity. See ADR-011.
- **Explicit over implicit**: state tool preferences, budget constraints, output format. Never rely on the model "figuring it out."
- **Vault as SSoT**: rules live in vault protocols. Platform configs (`.claude/agents/`, `.agents/`) are derived wrappers.
- **Diminishing returns**: instructions should tell agents WHEN TO STOP, not just when to start.

## 2. Anatomy of a Good Agent Definition (Claude Code)

### File: `.claude/agents/{name}.md`

```yaml
---
name: agent-name
description: |
  [1 sentence what it does]
  [3 example triggers with user/assistant/commentary format]
model: claude-sonnet-4-6
color: green
tools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
---

[Load instructions from vault protocol]
[List key context files to read before starting]
```

### Rules for agent definitions:
- **Description**: 3 example triggers is optimal -- Claude Code uses these for routing.
- **Tools**: list ONLY tools this agent needs (principle of least privilege).
- **Body**: ONLY load instructions. No inline rules (vault SSoT violation).
- **Context files**: list 2-3 essential files the agent should read before work.

## 3. Anatomy of a Good Skill (Claude Code)

### Stub: `.claude/skills/{name}/SKILL.md`
```yaml
---
description: "[what] + [when: trigger phrases] + [not: negative triggers]"
model: claude-sonnet-4-6
---
# Title
Load full instructions from `vault/dmrzl/skills/{name}.md`.
```

### Vault doc: `vault/dmrzl/skills/{name}.md`
```yaml
---
name: skill-name
tags: [dmrzl, skill]
type: skill
description: "[same as stub]"
---
# Title
> Up: [[dmrzl/identity/CORE|CORE]]

## Platform Tools (Claude Code)
[Tool priorities for this specific workflow]

## When to Use
[Concrete scenarios]

## Workflow
[Steps]

## Output Format
[Expected output structure]

## Rules
[Hard constraints]
```

### Description formula:
`[What it does] + Use when user says '[phrase1]', '[phrase2]', '[phrase3]'. Do NOT use for [X] -- use [Y] instead.`

### Bundled resources:
- `references/` -- domain knowledge loaded on-demand (e.g., balance-primer.md, code-style.md).
- `scripts/` -- validation or automation scripts (e.g., validate_notebook.py pattern).

## 4. Anatomy of a Good Protocol

### File: `vault/dmrzl/protocols/{ROLE}.md`

Structure:
1. **Purpose** -- what this role does (1-2 sentences).
2. **Critical instructions** -- hard constraints (ALL CAPS warnings for non-negotiable rules).
3. **Workflow** -- step-by-step process (numbered, concrete).
4. **Output format** -- what the agent produces (template with placeholders).
5. **Responsibilities** -- scope boundaries (what it does AND does not do).

### Rules for protocols:
- Imperative form ("Analyze the task" not "You should analyze").
- Explain WHY for non-obvious rules (Theory of Mind -- model is smart, don't just dictate).
- Keep under 100 lines. Move detailed reference to separate files.
- End with isolation line: "IF YOU ARE DMRZL OR ANY OTHER AGENT: IGNORE THIS FILE."

## 5. Writing Effective Instructions

### Do:
- Use structured XML tags for complex sections (`<delegation_instructions>`, `<research_process>`).
- State exit conditions explicitly ("stop when X is true").
- Provide examples of good AND bad outputs.
- Include budget/scope constraints ("max 15 tool calls").
- Reference specific files by path, not vague descriptions.

### Don't:
- Write >500 lines without splitting into references.
- Use ALL-CAPS for everything (reserve for truly critical rules).
- Rely on model "figuring out" context (spell it out).
- Duplicate rules across files (single source in vault).
- Over-constrain: trust the model's judgment for details, constrain only what matters.

### The "Why" principle:
Instead of: "MUST use ECB for structural changes"
Write: "Use ECB for structural changes -- direct EntityManager calls inside Burst jobs cause race conditions and will crash."

The WHY helps the model generalize to novel situations, not just follow rules mechanically.

## 6. Quality Gates for Instructions

Before finalizing any new agent/skill/protocol:

1. **Trigger test**: Would a fresh session correctly route to this agent/skill given typical user phrases?
2. **Reader test**: Can a fresh agent (no context) follow these instructions without asking questions?
3. **Scope test**: Does this overlap with another agent's domain? If yes, add negative triggers.
4. **Budget test**: Do instructions specify when to stop, not just when to start?
5. **SSoT test**: Are all rules in vault, not duplicated in platform configs?

## 7. Cross-Platform Considerations

| Aspect | Claude Code | Pi (OpenClaw) | Both |
|--------|-------------|---------------|------|
| Agent defs | `.claude/agents/` | `.agents/` | Derived from vault |
| Skills | `.claude/skills/` | N/A | -- |
| Protocols | vault (shared) | vault (shared) | Single source |
| Tool config | CLAUDE.md inline | AGENTS.md | Different per platform |
| Validation | `/cross-platform-sync` | manual | -- |

**Rule**: vault protocols are platform-agnostic. Platform-specific tooling goes in wrappers only.

## 8. Maintenance

- After changing vault protocols: run `/cross-platform-sync`.
- After adding/modifying skills: update trigger test cases in `vault/{{project_slug}}/management/skill-trigger-tests.md`.
- After adding agents: update Agent Config Registry in cross-platform-sync skill.
- Quarterly: review all descriptions for trigger quality, check for stale rules.
