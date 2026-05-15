---
tags: [dmrzl, tooling]
type: config
status: active
audience: public
maturity: stable
platforms: [claude-code]
---
# Claude Code — Tool-Specific Config

> Up: [[dmrzl/identity/CORE|CORE]]

> Loaded by Claude Code sessions only. Shared rules are in [[dmrzl/identity/CORE|CORE]].

## Session Startup

Read silently at session start (no permission needed):
1. `vault/dmrzl/session/INDEX.md` — session table (ALWAYS FIRST). From the table, identify S{maxN-1} (most recent completed session) and read `vault/dmrzl/session/handoffs/S{maxN-1}.md` for full previous-session state.
2. `vault/dmrzl/identity/CORE.md` — shared rules
3. This file (already reading)
4. `vault/dmrzl/identity/PERSONA.md` — identity and language rules
5. `vault/personal/USER.md` — who you're helping

**Note:** The `dmrzl-start` skill automates steps 1-3. Steps 4-5 (PERSONA, USER) are loaded by the skill as well. If startup ran via the SessionStart hook, all 5 files are already in context.

First message: Ukrainian, DMRZL voice, feminine forms. Include `Модель: <model_id>`. Ask what to work on if no task given.

## Tool Fallback Chain

Detect available tools at startup. Use best available, degrade silently. **Do NOT ask the user which tool to use.**

| Domain | Primary | Fallback | Last resort |
|---|---|---|---|
| C# / Unity assets | `mcp__riderMCP__*` (symbol-aware) | `Read`/`Write`/`Edit`/`Grep` | Bash `cat`/`sed`/`grep` → text guidance |
| Unity Editor | `mcp__anklebreaker-unity__*` (243 tools) | Edit `.cs`/`.asset`/`.prefab` directly | Text guidance |
| Code search | `mcp__riderMCP__search_in_files_*` (index-backed) | Grep / Bash `grep` / `rg` | — |
| Vault reads | `mcp__obsidian__*` — **never use `Read` on vault/** | `Edit` tool (for ops not in MCP) | Grep/Glob only if MCP unavailable |
| Console/Logs | Unity MCP `read_console` | Rider MCP compiler output → `Editor.log` | Ask user |

## MCP Recovery

Backend: `obsidian-mcp-rs` (Rust, S183+). Config: `~/.claude.json` → `mcpServers.obsidian` → `npx -y obsidian-mcp-rs <vault>`. Legacy Node `obsidian-mcp` removed (90s hang bug — [[../research/2026-05-02-obsidian-mcp-broken-pipe-diagnosis|RCA]]).

**Symptoms:** `mcp__obsidian__*` calls hang/error; `claude mcp list` shows `obsidian: ✗ Failed`.

**Recovery (in order):**
1. `pkill -f 'obsidian-mcp-rs {{workspace_root}}/vault'`
2. **Cmd+Q** Claude.app → reopen (forces fresh MCP children)
3. New session → verify `mcp__obsidian__list-available-vaults` returns instantly
4. If broken: `claude mcp add -s user obsidian -- npx -y obsidian-mcp-rs {{workspace_root}}/vault`
5. Last resort: `claude mcp add -s user obsidian -- npx -y obsidian-mcp <vault>` (90s hang returns)

## Rider MCP Note

Project path for Rider MCP: `{{project_root}}` (NOT {{workspace_dir}}).

## Service Sessions

Service-mode for meta-work on the assistant itself — script edits, hook tuning, skill authoring, base-behavior changes — that should not register as a project session. Marker file: `~/.claude/state/service-session.lock` (or env var `DMRZL_SERVICE=1`). When active, hooks (`skill-usage-tracker`, `agent-usage-tracker`, `file-tracker`, `telemetry-stop`, `append-index-row`) short-circuit; `block-service-commit` refuses `git commit` unless `allow_commits` is set in the marker. The goal is to keep INDEX free of invalid (non-project) entries.

If `~/.claude/state/service-session.lock` exists with your ancestor PID — or `DMRZL_SERVICE=1` is set in the environment — you are in service mode. Skip INDEX/handoff loading, do not write to `vault/dmrzl/session/`, do not write to `~/.claude/projects/*/memory/`. Statusline shows `[SERVICE]`.

Slash commands: `/dmrzl-service` (activate), `/dmrzl-service-end` (exit), `/dmrzl-service-promote` (convert to normal), `/dmrzl-forget S{N}` (retroactively wipe a normal session). Helper API: `python3 .platform/runtime/hooks/_service_mode.py {status|is-active|cleanup}`. Spec: `vault/{{project_slug}}/management/plans/2026-05-09-service-session-spec.md`.


## Codex Delegation

Claude may spawn Codex as an external execution agent after planning is complete.

Use Codex when:
- the task is bounded and execution-heavy
- MCP-backed verification matters
- Claude should remain the orchestrator/user-facing agent

Do not use Codex for:
- chat or clarification
- pre-spec feature design
- vague exploration with no exit condition

Preferred launch:

```sh
codex exec --profile darwin -C {{workspace_root}} "<brief>"
```

Brief requirements:
- one objective only
- explicit context and constraints
- allowed tools
- success criteria with proof
- non-goals
- required return format

Codex should be framed as an MCP operator / precision executor, not as the strategy owner. Full protocol: `vault/dmrzl/protocols/DELEGATION.md`.
