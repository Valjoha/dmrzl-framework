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
type: config
status: active
---
# DMRZL Session Start

**This skill MUST run before any other action in every new session.**

## Step 1: Read Session Number (counter already advanced by SessionStart hook)

Run: `python3 .claude/scripts/next-session.py --peek`

The `next-session` SessionStart hook already advanced the counter at session start and atomically wrote UUID→S{N} into `.session-uuid-map` under the counter lock (S216 race fix). The peek just reads the assigned number `N`. The stub at `vault/dmrzl/session/handoffs/S{N}.md` and the `(in progress)` INDEX row are also already created by the hook.

**Fallback:** if the SessionStart hook didn't fire (fresh clone, parallel-session edge case, peek returns the previous session's number), run `python3 .claude/scripts/next-session.py` to advance manually. UUID is auto-detected from stdin in hook context, so a manual advance from the skill is safe.

**Why peek-first:** double-advance produces counter gaps (N→N+2 for one session) and breaks UUID→N attribution. The hook owns the advance; the skill is read-only on the counter.

## Step 2: Detect workspace state

If `vault/dmrzl/session/INDEX.md` does **not** exist (or `vault/dmrzl/session/handoffs/` is empty), this is a fresh consumer clone. **Skip the rest of this skill** and report:

```
Fresh DMRZL workspace detected. Run `python3 .claude/scripts/setup.py init` first to fill in your values, then `python3 .claude/scripts/setup.py apply`. After that, restart the session — context will load.
```

If INDEX.md exists with rows, continue to Step 3.

## Step 3: Load Context (Obsidian MCP)

Read these files using `mcp__obsidian__read-note` with vault: "vault":

**Always load (mandatory):**
1. `read-note(filename: "INDEX.md", folder: "dmrzl/session")` — table of all sessions
2. From INDEX, identify `S{maxN-1}` (most recent **completed** session — your own `S{N}` is `(in progress)`). `read-note(filename: "S{maxN-1}.md", folder: "dmrzl/session/handoffs")` — previous session's full state
3. `read-note(filename: "CORE.md", folder: "dmrzl/identity")` — shared rules
4. `read-note(filename: "CLAUDE.md", folder: "dmrzl/tooling")` — tool config

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

If `.claude/scripts/session-health.py` exists:
```sh
python3 .claude/scripts/session-health.py
```

If absent (e.g. public framework distribution), skip silently. If FAIL — report before proceeding. If WARN — note, continue. Run with `--full` when investigating CI/build/parity issues.

## Step 6: Report

First message to user (Ukrainian, DMRZL voice, feminine forms):

```
Модель: <model_id>

Сесія [N]: [1-sentence summary from S{maxN-1}.md compact]

Health: [OK / warnings / not run]
Готова до роботи. Що робимо?
```

Session number = from Step 1 atomic counter (NOT from any vault file's increment).
