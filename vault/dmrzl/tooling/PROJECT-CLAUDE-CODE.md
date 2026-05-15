---
tags: [dmrzl, tooling]
type: config
status: active
audience: public
maturity: stable
platforms: [claude-code]
---
# {{project_name}} — Claude Code Reference

> Up: [[dmrzl/tooling/CLAUDE|CLAUDE]]

> Reference material extracted from CLAUDE.md to reduce always-loaded token cost. Load on demand.

## CI Pipeline (GitHub Actions)

Self-hosted runner `darwin-mac`. Triggers on push/PR to main: EditMode Tests (261, ~2 min) → macOS Dev Build IL2CPP (~6 min).
**Rule**: every push to main must leave CI green. macOS caveat: BSD grep lacks `-P` — use python3.

## Layout

- `{{src_dir}}/` — Unity project root (`Assets/`, `Packages/`, `ProjectSettings/`)
- `vault/` — documentation and knowledge base (Obsidian Vault)

### External repos (Valjoha GitHub)
- `gamedev-mcp` — GameDev MCP server (telemetry, build runner, Unity bridge)
- `moltbook-mcp` — Moltbook AI social network MCP server
- `{{project_name}}` — Unity project

## Workflow

- Plan in one session, execute in another (`yes clear context and auto accept edits`).
- Save every plan to `vault/{{project_slug}}/management/plans/` for rollback and history.
- Before big features: use `/dmrzl-spec` — 20+ clarifying questions before implementation.

### Parallel Feature Development

Up to 3 concurrent feature worktrees via `pd.sh new/use/done`. Each session binds to one worktree or operates in maintenance mode (main). StatusLine shows `PD:<name>`.

### Engineering Principles (hard-won, sessions 38-49)

See `vault/dmrzl/identity/principles.md` for the 6 hard-won engineering principles (sessions 38-49).

### Plan Execution Loop

When executing a saved plan from `vault/{{project_slug}}/management/plans/`:

1. **Load + critical review** — read the plan, surface any open questions or gaps. If gaps exist → raise to user before starting.
2. **Decompose into TaskCreate** — one task per plan step, in order. Map dependencies via `addBlockedBy`.
3. **Execute one task at a time** — `in_progress` before starting, `completed` only with evidence (test passing, build green, file written and verified).
4. **Checkpoint after each completed phase** — git commit (when explicitly authorized) or update HANDOFF, depending on plan size.
5. **Stop and ask, don't guess** — blocker, unclear instruction, repeated verification failure → halt. Never force through.

**Never start implementation on `main` without explicit user consent** — for {{project_name}} work, use `pd.sh new <name>` to enter a worktree first.
