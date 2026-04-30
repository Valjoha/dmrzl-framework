---
description: "Start a DMRZL session — load vault context, check health, report status. MUST be invoked at the start of EVERY session before any other work. Use when: session starts, user says 'start', 'init', 'reinitialize', or when startup files weren't loaded. This skill OVERRIDES the superpowers start-session skill."
audience: public
---
# DMRZL Session Start

**This skill MUST run before any other action in every new session.**

## Step 1: Assign Session Number (FIRST — before any tracked tool calls)

Run: `bash .claude/scripts/next-session.sh`

This atomically increments the counter and returns your session number. Use this number (NOT HANDOFF.md's number + 1) to avoid collisions when multiple sessions run in parallel.

**Why first:** PostToolUse hooks (vault-access-tracker, skill-usage-tracker) log the current session number. If vault reads happen before session assignment, they get attributed to the previous session.

To peek at the current number without incrementing: `bash .claude/scripts/next-session.sh --peek`

## Step 2: Detect workspace state

**Before loading context, check whether this is a fresh setup or an existing workspace:**

- If `vault/dmrzl/session/HANDOFF.md` does **not** exist (or is empty), this is a fresh consumer clone. **Skip the rest of this skill** and report:

  ```
  Fresh DMRZL workspace detected. Run `./.claude/scripts/setup.sh init` first to fill in your values, then `./.claude/scripts/setup.sh apply`. After that, restart the session — context will load.
  ```

  Do not try to load HANDOFF.md / CORE.md / CLAUDE_CODE.md yet.

- If HANDOFF.md exists with content, continue to Step 3.

## Step 3: Load Context (Obsidian MCP)

Read these files using `mcp__obsidian__read-note` with vault: "vault":

**Always load (mandatory):**
1. `read-note(filename: "HANDOFF.md", folder: "dmrzl/session")` — previous session state
2. `read-note(filename: "CORE.md", folder: "dmrzl/identity")` — shared rules
3. `read-note(filename: "CLAUDE_CODE.md", folder: "dmrzl/tooling")` — tool config

**On-demand (load when needed, not at startup):**
4. `read-note(filename: "PERSONA.md", folder: "dmrzl/identity")` — full persona, literary coloring, response templates. Load when: first complex Ukrainian response, persona-sensitive interaction, or user asks about DMRZL style.
5. `read-note(filename: "USER.md", folder: "personal")` — full user profile (career, hobbies, health). Load when: non-dev question, user context needed, or career/personal topic arises.

Essential persona rules are already in CLAUDE.md `## Identity` — sufficient for most sessions.

**CRITICAL: folder is NEVER "agents". Vault uses 4-layer layout: dmrzl/ darwin/ personal/ archive/**

**Watch for cross-vault contamination:** if your Obsidian MCP is configured user-scoped against a different vault (e.g. you have two vaults named "vault"), the read-note calls will return content from whichever vault Obsidian considers active. If the loaded HANDOFF/CORE references a project you're not working on, stop and reconfigure the MCP server to point at this clone's vault.

If Obsidian MCP is unavailable, fall back to Read tool:
1. `vault/dmrzl/session/HANDOFF.md`
2. `vault/dmrzl/identity/CORE.md`
3. `vault/dmrzl/tooling/CLAUDE_CODE.md`

## Step 4: Health Check (optional)

If `.claude/scripts/session-health.sh` exists, run it:
```sh
bash .claude/scripts/session-health.sh
```

If the script is absent (e.g. public framework distribution doesn't ship it), skip silently — this is expected.

If FAIL — report issues before proceeding.
If WARN — note warnings, continue.

## Step 5: Report

First message to user (Ukrainian, DMRZL voice, feminine forms):

```
Модель: <model_id>

Сесія [N]: [1-sentence summary from HANDOFF.md current state]

Health: [OK / warnings / not run]
Готова до роботи. Що робимо?
```

Session number = from Step 1 atomic counter (NOT from HANDOFF.md increment).
