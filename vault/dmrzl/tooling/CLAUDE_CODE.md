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

Detect available tools at startup. Use the best available, degrade silently.
**Do NOT ask the user which tool to use** — detect and adapt.

**C# / Unity assets:**
1. Rider MCP (`mcp__riderMCP__*`) — symbol-aware, refactoring-safe
2. Standard file tools (`Read` / `Write` / `Edit` / `Grep`)
3. Bash (`cat` / `sed` / `grep`)
4. Text guidance — provide code for user to apply manually

**Unity Editor:**
1. AnkleBreaker Unity MCP (`mcp__anklebreaker-unity__*`) — scene, console, components, profiler, shader graph, 243 tools
2. File-based — edit `.cs` / `.asset` / `.prefab` directly
3. Text guidance

**Code search:**
1. Rider MCP (`search_in_files_by_text` / `search_in_files_by_regex`) — index-backed
2. Grep tool / Bash `grep` / `rg`

**Vault (read, search, navigate):**
1. Obsidian MCP (`mcp__obsidian__*`) — primary for vault reads/search/edit
2. `Edit` tool — for modifications not covered by Obsidian MCP
3. Grep / Glob — fallback only if Obsidian MCP is unavailable
**Rule: never use `Read` tool on `vault/` files when Obsidian MCP is available.**

**Console / Logs:**
1. Unity MCP (`read_console`)
2. Rider MCP — compiler output
3. Log files — read `Editor.log` directly
4. Ask user

## MCP Recovery

### Current backend: `obsidian-mcp-rs`
Since S183 the `obsidian` MCP server is backed by `obsidian-mcp-rs` (Rust binary, no `ConnectionMonitor`). The legacy Node `obsidian-mcp` was removed because its self-destruct after ~90s of client inactivity caused the broken-pipe hangs documented in [[../research/2026-05-02-obsidian-mcp-broken-pipe-diagnosis|RCA v1]] and S180 RCA v2.

Config: `~/.claude.json` → `mcpServers.obsidian` → `npx -y obsidian-mcp-rs <vault>`.

### Symptoms (if anything regresses)
- `mcp__obsidian__*` tool calls hang or return errors.
- `claude mcp list` reports `obsidian: ✗ Failed to connect` or live ping fails.

### Recovery protocol
1. `pkill -f 'obsidian-mcp-rs {{workspace_root}}/vault'` — kill any stuck servers.
2. **Cmd+Q** on Claude.app, then reopen — new host process spawns fresh MCP children.
3. Start a new Claude Code session. Verify: `mcp__obsidian__list-available-vaults` should return instantly.
4. If still broken, re-add: `claude mcp add -s user obsidian -- npx -y obsidian-mcp-rs {{workspace_root}}/vault`.
5. Last-resort rollback to legacy: `claude mcp add -s user obsidian -- npx -y obsidian-mcp <vault>` (knowing the 90s hang will return).

**Note:** Re-registering via `claude mcp add` does NOT recover live stdio pipes; only Cmd+Q on Claude.app forces fresh MCP children.

## Rider MCP Note

Project path for Rider MCP: `{{project_root}}` (NOT {{workspace_dir}}).


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
