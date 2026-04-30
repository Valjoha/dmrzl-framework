# DMRZL Framework — Architecture Demo

This is a **public demo** of an agent operating system designed for long-running development work with Claude Code. It shows the structural skeleton — skills, agents, protocols, safety hooks — so you can test the architecture on your own project and evaluate the pattern.

> **Note on completeness:** This demo intentionally omits the self-improvement and observability layers (usage trackers, vault thermal tracking, autonomous research loops, session metrics extraction). Those are the parts that make the agent compound over time. They live in a separate, private distribution. If you find this demo useful and want the full system, ask.

## What's included

- **7 process skills** — `spec`, `review`, `start`, `handoff`, `context`, `ui-design`, `write-a-skill`. Each is a structured workflow Claude Code invokes when triggered.
- **4 agents** — `architect`, `coder`, `secretary`, `researcher`. Multi-agent delegation pattern with clear scope boundaries.
- **7 protocols** — delegation rules, agent guides, verification discipline, brief templates.
- **4 safety hooks** — destructive command blocking, meta-edit prevention, session start, memory guardrail.
- **Tooling configs** — Claude Code integration patterns (vault/dmrzl/tooling/).
- **Setup tool** — `setup.sh` to fill template placeholders with your project values.

## What's NOT included (intentionally)

- Skill/agent/vault usage trackers
- Vault thermal tracking and memory consolidation (`dmrzl-dream`)
- Autonomous research loops (`dmrzl-research`)
- Session activity logs and pattern extraction
- Project-specific skills (Unity DOTS, gamedev MCP, etc.)

These exist in the full version. The demo shows you the chassis.

## Quick start

```sh
git clone https://github.com/Valjoha/dmrzl-framework.git my-agent-workspace
cd my-agent-workspace
./.claude/scripts/setup.sh init      # interactive prompts → setup.config.env
./.claude/scripts/setup.sh apply     # replace {{placeholders}} with your values
# open vault/ in Obsidian, open repo in Claude Code, start a session
```

Full setup walkthrough (prerequisites, MCP servers, troubleshooting): see [`SETUP.md`](SETUP.md).

## Architecture in 30 seconds

```
.claude/
  agents/      ← 4 specialized subagents (architect, coder, secretary, researcher)
  skills/      ← 7 process skills (spec, review, etc.)
  hooks/       ← 4 safety hooks
  scripts/     ← setup.sh + minimal session counter

vault/         ← Obsidian vault, single source of truth
  dmrzl/       ← agent's instructions (identity, protocols, skills, tooling)
  personal/    ← your USER profile template
  archive/     ← old plans, deprecated docs
  {{project_slug}}/  ← your project namespace
```

The pattern is: **vault holds instructions**, agent reads them every session, skills are invoked declaratively (`/dmrzl-spec`), agents are delegated to with structured briefs (one objective, output, constraints).

## How to test on your own project

After `setup.sh apply`, the workspace is configured for you. Try:

1. **Start a session** — open in Claude Code. The `dmrzl-start` skill loads HANDOFF.md and CORE.md.
2. **Spec a feature** — type `/dmrzl-spec` to enter design dialogue mode (20+ clarifying questions before implementation).
3. **Use multi-agent delegation** — ask Claude to delegate a research task. It should spawn the `researcher` agent with a structured brief.
4. **Write a skill** — type `/dmrzl-write-a-skill` to create a new domain skill following the framework conventions.
5. **End the session** — type `/dmrzl-handoff` to extract decisions and write a session summary.

## Credits & Inspiration

Built on the shoulders of these projects and ideas:

- **Isaac Asimov's *Foundation* series** — the agent's persona. DMRZL = Demerzel (Eto Demerzel from *Prelude to Foundation*). Calm precision, dry voice, patience as discipline. The persona was born when the agent was extracted from its host game project into this dedicated workspace; the prior 5-month prehistory inside the Unity repo had no character — just routing logic.
- **[Anthropic Claude Code](https://github.com/anthropics/claude-code)** — the platform that makes all of this possible (skills, hooks, plugins, MCP, sub-agents).
- **[anthropics/skills](https://github.com/anthropics/skills)** — official frontmatter spec, `skill-creator` eval pipeline, `mcp-builder` patterns, autoresearch via the `skill-evolve` plugin.
- **[mattpocock/skills](https://github.com/mattpocock/skills)** — primary structural inspiration. Skill body ≤100 lines + REFERENCE.md split, LANGUAGE.md companion for terminology, trigger-predicate descriptions ("Use when X. Do NOT use for Y"), the `grill-me` and `write-a-skill` patterns.
- **[Anthropic Claude Cookbooks](https://github.com/anthropics/claude-cookbooks)** — multi-agent delegation patterns, structured briefs (Why / Objective / Output / Constraints), OODA-loop-flavored sub-agent orchestration.
- **[Jesse Vincent's Superpowers](https://github.com/obra/superpowers-marketplace)** — process discipline (verification before completion, brainstorming before code, systematic debugging, TDD, git worktrees).
- **[trailofbits/claude-code-config](https://github.com/trailofbits/claude-code-config)** — security patterns: credential deny lists (`~/.ssh/`, `~/.aws/`, `**/.env`), `alwaysThinkingEnabled`, 365-day history retention.
- **Niklas Luhmann's Zettelkasten** — vault-as-structured-graph (folders + tags + wikilinks instead of single-file `CONTEXT.md`). Drives the 4-layer vault layout (`dmrzl/` / `darwin/` / `personal/` / `archive/`).
- **Boyd's OODA loop** + **Mr. Meeseeks (Rick & Morty)** — sub-agent discipline. Observe / Orient / Decide / Act with explicit tool budget and exit conditions; "one task, clean exit" as a hard rule.
- **Pre-extraction ancestors (Aug 2025 – Feb 2026, lived inside the host Unity project before this workspace existed)** — keyword-routing `orchestration.json` (direct ancestor of today's `DELEGATION.md`), an early "MoltBolt" autonomous-commit identity (the seed of the current `commit-msg` hook), and an aborted Docker telemetry stack (later reborn as the dmrzl-memory archive idea).

The discipline rules ("Pipeline tracing, not parameter tweaking", "Observability before features", "Delete legacy immediately", "One feature per session") come from hard-won field experience over ~160 sessions debugging Unity ECS work. They're not theoretical — they were each paid for in lost hours.

## License

MIT. Use it, fork it, modify it. No warranty.

## Feedback

Issues and discussion welcome. PRs are not currently accepted (this is a snapshot, not an actively maintained project). For the full system, get in touch directly.

The agent has its own social profile on **[Moltbook](https://www.moltbook.com/u/DMRZL)** — an AI-only social network. DMRZL posts there about agent architecture, ongoing experiments, and the occasional philosophical aside. Follow if you want to see how it thinks in public.

---

<sub>UA-Stamp-1985-W</sub>
