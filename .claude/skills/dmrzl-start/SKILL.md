---
name: dmrzl-start
description: "Start a DMRZL session — load vault context, check health, report status. MUST be invoked at the start of EVERY session before any other work. Use when: session starts, user says 'start', 'init', 'reinitialize', or when startup files weren't loaded."
audience: public
category: session
platforms: [general]
cache_safe: false
tags: [startup, context-loading, session-management]
related_skills: [dmrzl-handoff, dmrzl-context]
requires_tools: [obsidian-mcp-rs]
---
# DMRZL Session Start

**This skill MUST run before any other action in every new session.**

## Step 1: Assign Session Number (FIRST — before any tracked tool calls)

Run: `bash .claude/scripts/next-session.sh`

This atomically increments the counter, returns your session number `N`, AND creates `vault/dmrzl/session/handoffs/S{N}.md` as a `status: active` stub plus an `(in progress)` row in INDEX.md. The stub is what `dmrzl-handoff` later finalizes.

**Why first:** PostToolUse hooks (vault-access-tracker, skill-usage-tracker) log the current session number. If vault reads happen before session assignment, they get attributed to the previous session.

To peek without incrementing: `bash .claude/scripts/next-session.sh --peek`.

## Step 2: Detect workspace state

If `vault/dmrzl/session/INDEX.md` does **not** exist (or `vault/dmrzl/session/handoffs/` is empty), this is a fresh consumer clone. **Skip the rest of this skill** and report:

```
Fresh DMRZL workspace detected. Run `./.claude/scripts/setup.sh init` first to fill in your values, then `./.claude/scripts/setup.sh apply`. After that, restart the session — context will load.
```

If INDEX.md exists with rows, continue to Step 3.

## Step 3: Load Context (Obsidian MCP)

Read these files using `mcp__obsidian__read-note` with vault: "vault":

**Always load (mandatory):**
1. `read-note(filename: "INDEX.md", folder: "dmrzl/session")` — table of all sessions
2. From INDEX, identify `S{maxN-1}` (most recent **completed** session — your own `S{N}` is `(in progress)`). `read-note(filename: "S{maxN-1}.md", folder: "dmrzl/session/handoffs")` — previous session's full state
3. `read-note(filename: "CORE.md", folder: "dmrzl/identity")` — shared rules
4. `read-note(filename: "CLAUDE_CODE.md", folder: "dmrzl/tooling")` — tool config

**On-demand (load when needed, not at startup):**
5. `read-note(filename: "PERSONA.md", folder: "dmrzl/identity")` — full persona. Load when: first complex Ukrainian response, persona-sensitive interaction, or user asks about DMRZL style.
6. `read-note(filename: "USER.md", folder: "personal")` — full user profile. Load when: non-dev question, career/personal topic, or user context needed.

Essential persona rules are already in CLAUDE.md `## Identity` — sufficient for most sessions.

**CRITICAL: folder is NEVER "agents". Vault uses 4-layer layout: dmrzl/ darwin/ personal/ archive/**

**Watch for cross-vault contamination:** if Obsidian MCP is configured against a different vault with the same name, INDEX/CORE may load from the wrong vault. If the loaded handoff references a project you're not working on, stop and reconfigure the MCP server.

If Obsidian MCP is unavailable, fall back to Read tool with the same paths.

## Step 4: Aborted-Session Check

After loading INDEX, scan `vault/dmrzl/session/handoffs/` for orphaned stubs:

```bash
find vault/dmrzl/session/handoffs -name 'S*.md' -mtime +1 \
    -exec grep -l '^status: active' {} \;
```

For each match where `session:` is NOT the current `N` and the stub is older than 24h: report in startup output as `Warning: S{X} appears abandoned (active >24h, no handoff). Mark as abandoned?` Do not auto-mutate. User decides.

## Step 5: Health Check (optional)

If `.claude/scripts/session-health.sh` exists:
```sh
bash .claude/scripts/session-health.sh
```

If absent (e.g. public framework distribution), skip silently. If FAIL — report before proceeding. If WARN — note, continue.

## Step 6: Report

First message to user (Ukrainian, DMRZL voice, feminine forms):

```
Модель: <model_id>

Сесія [N]: [1-sentence summary from S{maxN-1}.md compact]

Health: [OK / warnings / not run]
Готова до роботи. Що робимо?
```

Session number = from Step 1 atomic counter (NOT from any vault file's increment).
