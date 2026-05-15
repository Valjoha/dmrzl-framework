---
name: dmrzl-service
description: "Activate service-mode for meta-work on the assistant itself — script edits, hook tuning, skill authoring, base-behavior changes, config tinkering — so the session leaves no traces in vault, INDEX, ratings, telemetry, or feedback logs. Use when the user says 'service session', 'service mode', 'meta session', 'tooling session', 'no trace session', or wants to touch assistant infrastructure without producing an invalid (non-project) entry in the session record. The session number is consumed as a gap in INDEX. Reads remain allowed; writes to telemetry/handoff/INDEX short-circuit; git commit is blocked unless the allow-commits flag is set."
audience: public
category: session
platforms: [general]
cache_safe: false
tags: [session, service, meta]
related_skills: [dmrzl-service-end, dmrzl-service-promote, dmrzl-forget]
type: config
status: active
---
<!-- GENERATED FROM vault/dmrzl/skills-src/dmrzl-service/SKILL.md -- DO NOT EDIT. Run sync-skills.py to refresh. -->
# DMRZL Service Mode

> Up: [[dmrzl/skills|Skills]]

Activate service-mode for meta-work on the assistant itself. Produces zero entries in the project session record.

## When to use

- Editing assistant scripts under `.claude/scripts/`, `.platform/runtime/`, or hook code.
- Tuning hooks, skills, agents, settings, statusline, or other base behavior.
- Authoring or refactoring `vault/dmrzl/skills-src/` and regenerating platform copies.
- Config tinkering (`~/.claude/`, `~/.codex/`, MCP wiring) that has no project value.
- Any meta-task that would otherwise log as a "real" session and pollute INDEX with non-project noise.

## When NOT to use

- Real {{project_name}} work (Unity, ECS, gameplay, design, balance) — use a normal session plus dmrzl-handoff.
- One-off question that fits a single response — just answer.
- Hotfix or critical work needing a paper trail.

## Activation

Two paths.

1. Mid-session via this skill:
   - Read current session number from `.claude/session-counter.txt`.
   - Capture parent Claude Code PID by walking `os.getppid()` until you reach launchd or a login shell.
   - Write the marker via the helper's `write_marker(N, pid, started_at)`.
   - Confirm: `python3 .platform/runtime/hooks/_service_mode.py is-active` exits 0.

2. Launch-time without a skill:
   - User runs `DMRZL_SERVICE=1 claude` (optionally with `DMRZL_SERVICE_ALLOW_COMMITS=1`).
   - Helper treats the env var as a synthetic marker. No file written.
   - Strict OTel suppression because the env var is set before process start.

## Behaviour after activation

- Counter increments; the number is burned. `S{N}.md` is never created.
- INDEX.md is not updated. The gap is intentional.
- Hooks short-circuit: skill-usage-tracker, agent-usage-tracker, file-tracker, telemetry-stop, append-index-row.
- `git commit` is blocked by `block-service-commit.py` unless `allow_commits` is true.
- Reads (Obsidian MCP, Read, Grep) stay fully allowed.
- Tmp scratch dir at `/tmp/dmrzl-service/{pid}/` is created and removed on exit.

## Startup contract

Load minimal context only:
- `vault/dmrzl/identity/CORE.md`
- `vault/dmrzl/tooling/CLAUDE.md`
- `vault/dmrzl/identity/PERSONA.md`

Skip INDEX.md, the previous handoff, and `vault/personal/USER.md`. Service mode runs without continuity.

## Statusline

`.claude/statusline.sh` detects the marker and prepends `[SERVICE]` to every render. The prefix survives context compaction — the agent rediscovers service mode by reading the marker.

## Auto-memory discipline

The agent MUST NOT write to `~/.claude/projects/*/memory/` during a service session. Hooks cannot reliably gate these path-discriminated writes. Surface memory-worthy facts as text and let the user record them after exit.

## First message

Acknowledge service mode in the user's configured chat language. Brief: confirm session number, tmp path, exit instruction. Persona feminine forms. No INDEX or handoff narration.

## Args

- `--allow-commits` — set `allow_commits: true` in the marker. Use only when the user explicitly wants commits during the service session.

## See also

- Spec: `vault/{{project_slug}}/management/plans/2026-05-09-service-session-spec.md`.
- Exit: `dmrzl-service-end`.
- Promote to normal: `dmrzl-service-promote`.
- Retroactive cleanup: `dmrzl-forget`.
