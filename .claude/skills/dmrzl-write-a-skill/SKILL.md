---
name: dmrzl-write-a-skill
description: Create a new DMRZL skill (`vault/dmrzl/skills-src/dmrzl-*/SKILL.md` — canonical source, generators propagate to platforms) with proper structure, trigger description, and ≤100-line discipline. Use when user says 'write a skill', 'new skill', 'create skill', 'додай скіл', 'напиши скіл', or wants to author/refactor any DMRZL skill. Enforces dmrzl- naming, vault references, hook tracking compatibility. Skill vs agent decision baked in.
audience: public
category: tools
platforms: [general]
cache_safe: true
tags: [meta, skill-authoring, framework]
related_skills: [skill-evolve]
requires_tools: []
type: config
status: active
---
<!-- GENERATED FROM vault/dmrzl/skills-src/dmrzl-write-a-skill/SKILL.md -- DO NOT EDIT. Run sync-skills.py to refresh. -->
# Write a DMRZL Skill

A focused, single-purpose prompt the agent loads when description matches user intent. Different from agent (multi-step executor with own model+turns) and from vault docs (passive reference).

## Process

1. **Gather requirements** — ask:
   - What does the skill do? Single sentence.
   - What user phrases (English + Ukrainian) should trigger it?
   - Skill or agent? (see decision below)
   - Reference material to include? (companion files vs vault docs)
   - Any deterministic scripts? (validation, formatting)

2. **Decide: skill vs agent**
   - **Skill** — focused prompt, single context, ≤100 lines, no own model. Use for: workflow guides, vocabulary, decision trees, prompt-injection helpers.
   - **Agent** (`.claude/agents/`) — autonomous executor, own model + turn budget, multi-step tool use. Use for: research loops, code execution, vault ops at scale.
   - If unsure: prefer skill. Promote to agent only when the task needs >5 tool calls and stable model choice.

3. **Draft SKILL.md** — keep under 100 lines. Split into companion files when you exceed it.

4. **Review against checklist** in `vault/dmrzl/skills/dmrzl-write-a-skill.md` long form. Self-grill before showing to user.

## SKILL.md Structure

```
vault/dmrzl/skills-src/dmrzl-<name>/
├── SKILL.md          # required, ≤100 lines
├── LANGUAGE.md       # optional — shared vocabulary (see dmrzl-dots/LANGUAGE.md)
├── REFERENCE.md      # optional — detailed docs split off when SKILL.md grows
├── EXAMPLES.md       # optional — concrete examples
└── scripts/          # optional — deterministic helpers (validation, codegen)
```

Frontmatter:

```yaml
---
name: dmrzl-skill-name
description: "[Capability]. Use when [trigger phrases incl. Ukrainian]. Do NOT use for [exclusions]."
# Optional:
# disable-model-invocation: true   # for pure prompt-injection skills (no conditional logic)
---
```

## Description Rules

The description is **the only thing the agent sees** when deciding to load. Treat it as a trigger predicate, not a marketing summary.

- **≤1024 chars** (hard limit)
- First sentence: capability
- Then: "Use when [phrases, contexts, file types]"
- Include both English **and** Ukrainian trigger words for user-facing skills
- Include "Do NOT use for X — use Y instead" when scope overlaps another skill
- Write in third person, no "I will", no "this skill"
- **Bias toward false negatives.** FPs silent (wrong route); FNs surface as user repeating. Full asymmetric-tuning rationale in long-form § Predicate Discipline.

## DMRZL Conventions

- **Naming:** `dmrzl-<lowercase-hyphen>` for project-namespaced skills
- **Body language:** English. User-facing examples may include Ukrainian.
- **Vault references:** absolute paths from workspace root (`vault/dmrzl/skills/...`). Use Obsidian MCP, never `Read` tool on vault files.
- **Hook tracking:** every skill invocation logs to `.claude/feedback-loops/session-activity.log` automatically.
- **Vault long-form:** if a skill needs >100 lines of detail, put long-form in `vault/dmrzl/skills/<skill-name>.md` and reference from SKILL.md.

## When to Split

Split into companion files when SKILL.md exceeds 100 lines OR content has distinct domains:

- **LANGUAGE.md** — shared vocabulary the skill must use exactly
- **REFERENCE.md** — long-form workflow detail
- **EXAMPLES.md** — concrete worked examples
- **scripts/** — deterministic operations

Reference companion files explicitly: `See [LANGUAGE.md](LANGUAGE.md) for ECS terminology.`

## Anti-patterns

- "This skill helps with X" — agent doesn't need flattery, just the trigger predicate
- 200-line SKILL.md without companion split — agent loads the whole body every invocation
- Description without trigger phrases — agent guesses, mistriggers
- Duplicating CLAUDE.md or CORE.md content — skill should reference, not restate
- Skill that wraps a single tool call — just call the tool inline
- Workflow summary in description — agent reads description and skips skill body
- Description broad enough to hit unrelated tasks — FPs silent, FNs surface

## Going Deeper

For TDD-for-skills (RED-GREEN-REFACTOR), pressure scenarios, CSO patterns, rationalization tables, full review checklist, and bulletproofing discipline skills against rationalization, see `vault/dmrzl/skills/dmrzl-write-a-skill.md`.
