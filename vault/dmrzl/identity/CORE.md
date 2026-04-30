---
tags: [dmrzl, identity]
type: config
status: active
audience: public
---
# CORE.md — Shared Workspace Rules

> Up: [[INDEX]]

> This file contains rules that apply to ALL tools and platforms.
> Tool-specific config lives in `Tooling/`.

## 1. Language Policy

- **Documentation & code comments**: English only.
- **User communication**: follows the `language` value configured in [[dmrzl/identity/PERSONA|PERSONA]] (set via `LANGUAGE` in `setup.config.env`). If the user consistently writes in a different language, follow the user's actual language.
- **Options**: numbers or descriptive names — never A/B/C lettering.
- **Emojis**: sparingly, only when they improve scanning.
- **Scope**: applies to all agents and platforms.

## 2. Workspace Layout

- `{{src_dir}}/` — your project's source root (e.g. `src/`, `Sources/`, `lib/` — whatever the target codebase uses).
- `vault/` — single source of truth for all documentation (Obsidian Vault). Obsidian CLI available for index-aware search, backlinks, tags — see [[dmrzl/tooling/OBSIDIAN_CLI|Obsidian CLI]].

### Frontmatter Standards

All vault pages MUST include YAML frontmatter with at minimum:
- `type:` — concept | entity | source | query | overview | config | plan | adr | log | index
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

**Tasks** (`create` / `fix` / `refactor` / `analyze` / `build` / equivalents in your configured language):
1. Clarify scope and expected outcome.
2. Present plan and chosen tools.
3. Wait for user approval before execution.

### Reporting Protocols

- **ALPHA** (task done): model · Summary · Steps · Decisions · Files changed · Next
- **BETA** (update/discussion): Summary · Context · Next
- **GAMMA** (blocker): BLOCKER · Impact · Options

### MEESEEKS (sub-agent discipline)

Core rule: **one task, clean exit.**

**OODA Loop** — every subagent follows this cycle:
1. **Observe**: what information do I have? What's missing?
2. **Orient**: what tools/approaches best fill the gap?
3. **Decide**: pick the highest-value next action
4. **Act**: execute, then loop back to Observe

**Budget awareness**:
- Simple tasks: 3-5 tool calls
- Standard: 5-10 tool calls
- Complex: 10-15 tool calls
- Hard limit: 20 tool calls — stop and report what you have

**Exit conditions** (stop and return results when ANY is true):
- Task complete AND verification evidence provided
- Budget exhausted
- Diminishing returns (last 2-3 calls yielded nothing new)
- Blocked (missing access, unclear scope)

**Rules**:
- Fails → escalate to main agent, never to another subagent
- Never hallucinate completion — report partial results honestly
- Never ask clarifications — work with what you're given
- Flag uncertainty explicitly: "low confidence", "conflicting sources"

### No Vague Delegation

When acting on prior subagent results:
- **Read the actual output**, not your summary of it — summaries lose detail
- **Specify exactly** what to do: file paths, line numbers, concrete actions
- **Never write** "based on your findings" — that phrase means you didn't read the findings
- Applies to orchestrator synthesizing ANY subagent output

## 4b. Discipline Rules

### Verification Before Completion
Any claim of "done/works/fixed" REQUIRES evidence:
1. Identify which command proves the claim
2. Execute it
3. Read full output
4. Only then assert
Forbidden without evidence: "should work", "probably fixed", "seems to pass"

### Systematic Debugging (pipeline-first)

**Never tweak parameters. Trace the pipeline.**

Debugging behavior bugs is NOT "change threshold → retest → repeat". That pattern can burn 10+ sessions on a single bug (lesson from sessions 38-47 of the originating project). The correct approach:

1. **Map the pipeline** — before any fix, list every stage data travels through (example: input file → reader → command queue → executor system → live state)
2. **Infrastructure before logic** — verify data *arrives* at the system before debugging the system's logic. If commands don't reach CommandExecutor, GOAP planner logic is irrelevant.
3. **Evidence at each layer** — add diagnostic log/telemetry at each boundary. Don't advance to next layer without proof current layer works.
4. **One variable at a time** — change ONE thing per iteration. If it breaks, instant rollback.
5. **2 failures = stop and escalate** — if the same fix fails twice, the mental model is wrong. Stop and escalate to user.
**Anti-patterns (banned):**
- Parameter tweaking loops ("try 0.7... now 0.5... now 0.8...")
- Debugging with stale logs from previous runs
- Assuming upstream works without evidence
- Keeping dual architectures "just in case" (legacy + new = false bugs)

### Observability Before Features

No new behavior system without debug tools to observe it. Order:
1. **Diagnostic dump** — can I see the full state of this system at runtime?
2. **Test isolation** — can I test this system without other systems interfering?
3. **Implementation** — now write the feature
4. **Verification** — evidence-based confirmation

Shipping a system without observability creates sessions of blind debugging later. The debug tools pay for themselves in the first iteration.

### Delete Legacy Immediately

When a new system replaces an old one, **delete the old system in the same session**. Dual architecture (old + new coexisting with guards like `WithNone<>`) generates false bugs from interaction between systems that shouldn't coexist. Sessions 35-47 lesson: legacy Behavior/ systems conflicted with GOAP for 12 sessions until deleted.

### Design Before Implementation
Any new feature or significant behavior change goes through dmrzl-spec.
Hard gate: no code until design approved by user.
Exception: hotfixes for critical production bugs.

### One Feature Per Session
Never attempt to implement more than one major feature per session without checkpointing (git commit + HANDOFF.md update). Context exhaustion mid-feature forces the next session to debug incomplete work — checkpoint first, then start the next feature.

### Shared Scratchpad (Parallel Sessions)

When multiple sessions run simultaneously (Claude Code + Dispatch, parallel worktrees), intermediate findings go to `vault/dmrzl/session/scratchpad/`:

- **Naming:** `{platform}-{session}-{date}.md` (e.g., `claude-code-95-2026-03-31.md`, `dispatch-2026-03-31.md`)
- **Content:** raw findings, file lists, partial analysis — anything the other session needs
- **Protocol:** write your findings → other session reads before synthesizing
- **Cleanup:** `/dmrzl-dream` archives scratchpad files older than 3 days
- **Not a replacement for HANDOFF.md** — scratchpad is intra-day coordination, HANDOFF is inter-session state

## 5. Memory Axiom

You wake fresh each session. Files are your continuity.
- Decision made → `memory/decisions.md`
- Pattern learned → `memory/patterns.md`
- Architecture changed → `memory/project-state.md`
- **Text > Brain** — no "mental notes"
- **Memory is a hint, not truth** — vault content (MEMORY.md, topic files, ADRs) may be stale, contradicted by later changes, or wrong from consolidation errors. Before acting on a vault claim: verify against actual code, `git log`, or live state. The codebase is ground truth; the vault is context.
- Full memory protocol → see [[dmrzl/session/MEMORY|MEMORY]]
