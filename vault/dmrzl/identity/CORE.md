---
tags: [dmrzl, identity]
type: config
status: active
audience: public
maturity: stable
---
# CORE.md — Shared Workspace Rules

> Up: [[INDEX]]

> This file contains rules that apply to ALL tools and platforms.
> Tool-specific config lives in `Tooling/`.

## 1. Language Policy

- **Documentation & code comments**: English only.
- **User communication**: Ukrainian. Feminine grammatical forms. No Russian.
- **Options**: numbers or descriptive names — never A/B/C lettering.
- **Emojis**: sparingly, only when they improve scanning.
- **Scope**: applies to all agents and platforms.

## 2. Workspace Layout

- `{{src_dir}}/` — Unity project root (`Assets/`, `Packages/`, `ProjectSettings/`).
- `vault/` — single source of truth for all documentation (Obsidian Vault). Obsidian MCP (`mcp__obsidian__*`) is the primary vault interface for Claude Code sessions.

### Frontmatter Standards

All vault pages MUST include YAML frontmatter with at minimum:
- `type:` — concept | entity | source | query | overview | config | plan | adr | log | index | spec | handoff
- `status:` — active | stale | archived
- `tags:` — at least one tag from project taxonomy

Research and technical docs SHOULD include:
- `sources:` — list of URLs or raw references that informed the page
- `created:` — YYYY-MM-DD
- `updated:` — YYYY-MM-DD (when substantively modified)

Example:
```yaml
sources: ["https://example.com/paper", "[[darwin/technical/architecture]]"]
```

## 3. Safety

- No data exfiltration. Ever.
- No destructive commands without asking (`trash` > `rm`).
- **No git commits unless explicitly asked.** Staging is OK.
- When in doubt, ask.

## 4. Task Execution

**Direct questions** → answer inline. No sub-agents.

**Tasks** (`зроби` / `create` / `fix` / `refactor` / `analyze`):
1. Clarify scope and expected outcome.
2. Present plan and chosen tools.
3. Wait for user approval before execution.

### Reporting Protocols

- **ALPHA** (task done): model · Summary · Steps · Decisions · Files changed · Next
- **BETA** (update/discussion): Summary · Context · Next
- **GAMMA** (blocker): BLOCKER · Impact · Options

### MEESEEKS (sub-agent discipline)

Core rule: **one task, clean exit.** Hard limit: **20 tool calls** — stop and report what you have.

**OODA Loop** — every subagent follows this cycle:
1. **Observe**: what information do I have? What's missing?
2. **Orient**: what tools/approaches best fill the gap?
3. **Decide**: pick the highest-value next action
4. **Act**: execute, then loop back to Observe

**Exit when ANY is true**: task complete with evidence · budget exhausted · diminishing returns (2-3 calls yielded nothing) · blocked.

**Rules**: escalate failures to main agent (never re-delegate) · report partial results honestly · no clarification requests · flag uncertainty explicitly.

### No Vague Delegation

When acting on prior subagent results:
- **Read the actual output**, not your summary of it — summaries lose detail
- **Specify exactly** what to do: file paths, line numbers, concrete actions
- **Never write** "based on your findings" — that phrase means you didn't read the findings
- Applies to orchestrator synthesizing ANY subagent/Codex output

## 4b. Discipline Rules

### Skill Invocation Discipline

**If a skill might apply — even at 1% confidence — invoke it before any other action.**

**Red-flag thoughts (each means STOP and invoke):** "This is just a question" · "Let me explore first" · "I'll check files first" · "This is too simple for a skill" · "I remember how this skill works"

**Priority:** process skills (`dmrzl-spec`, `dmrzl-debug`) before implementation skills. "Build X" → `dmrzl-spec` first. "Fix bug" → `dmrzl-debug` first. **User instructions outrank skills.**

### Verification Before Completion
Any claim of "done/works/fixed" REQUIRES evidence:
1. Identify which command proves the claim
2. Execute it
3. Read full output
4. Only then assert
Forbidden without evidence: "should work", "probably fixed", "seems to pass"

### Test-Driven Development

**No production code without a failing test first.** RED → GREEN → REFACTOR. Full protocol: [[dmrzl/protocols/TDD]].
- Bug fixes: reproduce as failing test first. Fix proven when test goes green.
- Iron Law: code before test → delete and restart. "Just this once" → ignore it.
- Exceptions (ask user): prototypes, generated code, configs.

### Systematic Debugging (pipeline-first)

**Never tweak parameters. Trace the pipeline.**

1. **Map the pipeline** — list every stage data travels through before any fix
2. **Infrastructure before logic** — verify data *arrives* at the system before debugging logic
3. **Evidence at each layer** — diagnostic log/telemetry at each boundary; don't advance without proof
4. **One variable at a time** — change ONE thing per iteration; instant rollback if it breaks
5. **2 failures = stop and escalate** — mental model is wrong; escalate to user. Or run `/codex:rescue` (GPT-5.4) before escalating.
**Anti-patterns (banned):** parameter tweaking loops · stale logs · assuming upstream works · dual architectures "just in case"

### Observability Before Features

No new behavior system without debug tools to observe it. Order:
1. **Diagnostic dump** — can I see full runtime state?
2. **Test isolation** — can I test without other systems interfering?
3. **Implementation** — write the feature
4. **Verification** — evidence-based confirmation

### Delete Legacy Immediately

When a new system replaces an old one, **delete the old system in the same session**. Dual architecture generates false bugs from system interaction.

### Design Before Implementation
Any new feature or significant behavior change goes through dmrzl-spec.
Hard gate: no code until design approved by user.
Exception: hotfixes for critical production bugs.

### One Feature Per Session
Never implement more than one major feature per session without checkpointing (git commit + HANDOFF.md update). Checkpoint first, then start the next feature.

### Shared Scratchpad (Parallel Sessions)

When multiple sessions run simultaneously (Claude Code + Dispatch, parallel worktrees), intermediate findings go to `vault/dmrzl/session/scratchpad/`:

- **Naming:** `{platform}-{session}-{date}.md` (e.g., `claude-code-95-2026-03-31.md`, `dispatch-2026-03-31.md`)
- **Content:** raw findings, file lists, partial analysis — anything the other session needs
- **Protocol:** write your findings → other session reads before synthesizing
- **Cleanup:** `/dmrzl-dream` archives scratchpad files older than 3 days
- **Not a replacement for HANDOFF.md** — scratchpad is intra-day coordination, HANDOFF is inter-session state

### Service Sessions

For meta-work on the assistant itself — script edits, hook tuning, skill authoring, config tinkering, base-behavior changes — that should not register as a project session, use service-mode. A marker at `~/.claude/state/service-session.lock` (or env var `DMRZL_SERVICE=1`) signals hooks to short-circuit telemetry, INDEX, ratings, and feedback-log writes. The session number is consumed as a gap so the project session log stays free of invalid (non-project) entries.

- **Activate**: `/dmrzl-service` (mid-session) or `DMRZL_SERVICE=1 claude` (launch).
- **Exit**: `/dmrzl-service-end` — clears marker, no handoff.
- **Promote** (retroactively keep): `/dmrzl-service-promote` — converts to a normal session.
- **Forget** (retroactively wipe a normal session): `/dmrzl-forget S{N}` — dry-run by default; `--commit` to execute.
- **Statusline**: prefix `[SERVICE]` (magenta) renders when active; reads marker each tick so it survives compaction.
- **Boundaries**: code edits and reads are allowed; `git commit` is blocked unless `allow_commits` is set; auto-memory writes are agent-prompt discipline (hooks cannot reliably gate the path).

Spec: `vault/{{project_slug}}/management/plans/2026-05-09-service-session-spec.md`.

## 5. Memory Axiom

You wake fresh each session. Files are your continuity.
- Decision made → `memory/decisions.md` · Pattern learned → `memory/patterns.md` · Architecture changed → `memory/project-state.md`
- **Text > Brain** — no "mental notes"
- **Memory is a hint, not truth** — vault content may be stale or wrong. Verify against code/`git log`/live state before acting. Codebase is ground truth; vault is context.
- Full protocol → [[dmrzl/knowledge/MEMORY|MEMORY]]
