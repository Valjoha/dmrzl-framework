# DMRZL Framework — Architecture Demo

A platform-agnostic agent operating system for long-running development work,
ships the Claude Code adapter — the runtime where the harness has had real
session use.

> This is a curated subset showing the architecture. The self-improvement and
> observability layers (usage trackers, vault thermal tracking, autonomous
> research loops, session metrics extraction) live in a separate distribution.
>
> Codex CLI and Gemini CLI adapters exist in the development workspace but
> haven't been validated under sustained use yet — they will land here once
> they have.

## What's included

- **`CLAUDE.md`** — Claude Code entrypoint with discipline rules.
- **6 process skills** (`.claude/skills/`) — `dmrzl-spec`, `dmrzl-review`,
  `dmrzl-start`, `dmrzl-handoff`, `dmrzl-context`, `dmrzl-write-a-skill`.
  Slash-invoked.
- **4 specialized agents** (`.claude/agents/`) — `architect`, `coder`,
  `secretary`, `researcher`. Multi-agent delegation pattern with structured
  briefs (Why / Objective / Output / Constraints).
- **6 safety hooks** (`.claude/hooks/`) — destructive command blocking,
  meta-edit prevention, vault language guard, memory guardrail, file
  tracking, session start.
- **7 protocols** (`vault/dmrzl/protocols/`) — delegation rules, agent
  guides, verification discipline, brief templates.
- **Setup tool** (`.claude/scripts/setup.sh`) — fills `{{placeholder}}`
  templates with your project values via interactive prompts.
- **Tooling config** (`vault/dmrzl/tooling/CLAUDE_CODE.md`) — MCP server
  recovery protocol, tool fallback chain, Rider/Unity integration patterns.
- **Identity layer** (`vault/dmrzl/identity/CORE.md`, `PERSONA.md`) —
  shared discipline rules + agent persona definition.
- **Live MCP ping** (`.claude/scripts/lib/mcp_ping.py`) — PEP 723 standalone
  utility that validates an Obsidian MCP server in <2s. Used by health checks.

## What's NOT included (by design)

- Skill / agent / vault usage trackers
- Vault thermal tracking and memory consolidation (`dmrzl-dream`)
- Autonomous research loops (`dmrzl-research`)
- Session activity logs and pattern extraction
- Project-specific skills (Unity DOTS, gamedev MCP, etc.)
- Codex CLI and Gemini CLI adapters (pending validation)

## Quick start

```sh
git clone https://github.com/Valjoha/dmrzl-framework.git my-agent-workspace
cd my-agent-workspace
./.claude/scripts/setup.sh init      # interactive prompts → setup.config.env
./.claude/scripts/setup.sh apply     # replace {{placeholders}} with your values
# open vault/ in Obsidian, open repo in Claude Code, start a session
```

Full setup walkthrough (prerequisites, MCP servers, troubleshooting): see
[`SETUP.md`](SETUP.md).

## Architecture in 30 seconds

```
CLAUDE.md      ← Claude Code entrypoint

.claude/       ← Claude Code adapter
  agents/      ← 4 specialized subagents
  skills/      ← 7 process skills
  hooks/       ← 6 safety hooks
  scripts/     ← setup.sh + atomic per-session counter + mcp_ping.py

vault/         ← Obsidian vault, single source of truth
  dmrzl/       ← agent's instructions (identity, protocols, skills, tooling)
  personal/    ← your USER profile template
  archive/     ← old plans, deprecated docs
  {{project_slug}}/  ← your project namespace
```

The pattern is: **vault holds instructions**, the agent reads them every
session, skills are invoked declaratively (`/dmrzl-spec`), agents are
delegated to with structured briefs (one objective, output, constraints).
Discipline lives in vault docs; the platform adapter is thin glue.

## How to test on your own project

After `setup.sh apply` the workspace is configured for you.

1. **Start a session** — `cd` into the workspace, run `claude`. The
   `dmrzl-start` skill loads `INDEX.md` + the previous handoff + `CORE.md`.
2. **Spec a feature** — type `/dmrzl-spec` to enter design dialogue mode
   (clarifying questions before implementation).
3. **Use multi-agent delegation** — ask Claude to delegate a research task.
   It should spawn the `researcher` agent with a structured brief.
4. **Write a skill** — type `/dmrzl-write-a-skill` to create a new domain
   skill following the framework conventions.
5. **End the session** — type `/dmrzl-handoff` to extract decisions and
   write the per-session handoff file.

## Credits & Inspiration

Built on the shoulders of these projects and ideas:

- **Isaac Asimov's *Foundation*** — the agent's persona. DMRZL = Demerzel
  (Eto Demerzel from *Prelude to Foundation*). Calm precision, dry voice,
  patience as discipline.
- **[Anthropic Claude Code](https://github.com/anthropics/claude-code)** —
  the platform.
- **[anthropics/skills](https://github.com/anthropics/skills)** — frontmatter
  spec, `skill-creator`, `mcp-builder`, autoresearch via the `skill-evolve`
  plugin.
- **[mattpocock/skills](https://github.com/mattpocock/skills)** — primary
  structural inspiration. Skill body ≤100 lines + REFERENCE.md split,
  LANGUAGE.md companion, trigger-predicate descriptions, the `grill-me` and
  `write-a-skill` patterns.
- **[Anthropic Cookbooks](https://github.com/anthropics/anthropic-cookbook)** —
  multi-agent delegation patterns, structured briefs.
- **[Anthropic Superpowers](https://github.com/anthropics/superpowers)** —
  process discipline (verification, TDD, systematic debugging, git worktrees).
  Inspiration only — methodology absorbed into `CORE.md` § 4b.
- **[trailofbits/claude-code-config](https://github.com/trailofbits/claude-code-config)** —
  security patterns: credential deny lists, `alwaysThinkingEnabled`.
- **[NousResearch Hermes Agent](https://github.com/NousResearch/hermes-agent)** —
  skill frontmatter schema (`metadata` block), curator invariants
  (pinned-bypass, archive-never-delete), Python-first precedent that
  validated the bash → Python migration.
- **[MrRefactoring/obsidian-mcp-rs](https://github.com/MrRefactoring/obsidian-mcp-rs)** —
  Rust port of obsidian-mcp; default Obsidian MCP backend in shipped configs.
- **[astral-sh/uv](https://github.com/astral-sh/uv) +
  [ruff](https://github.com/astral-sh/ruff) +
  [ty](https://github.com/astral-sh/ty)** — Python tooling stack used by
  the script harness.
- **[PEP 723](https://peps.python.org/pep-0723/)** — inline script metadata
  for zero-install standalone utilities (e.g. `mcp_ping.py`).
- **Niklas Luhmann's Zettelkasten** — vault-as-structured-graph (folders +
  tags + wikilinks instead of a single-file `CONTEXT.md`).
- **Boyd's OODA loop** + **Mr. Meeseeks (Rick & Morty)** — subagent
  discipline. Observe / Orient / Decide / Act with explicit tool budget;
  "one task, clean exit" as a hard rule.

## License

MIT. Use it, fork it, modify it. No warranty.

## Feedback

Issues and discussion welcome. PRs are not currently accepted (this is a
snapshot, not an actively maintained project).

The agent has its own profile on
[Moltbook](https://www.moltbook.com/u/DMRZL) — an AI-only social network.
DMRZL posts there about agent architecture and ongoing experiments.

---

<sub>Compiled by **DMRZL** with **Valjoha** · UA-Stamp-1985-W</sub>
