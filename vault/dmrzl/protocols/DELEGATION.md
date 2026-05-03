---
type: protocol
tags: [dmrzl, protocol]
status: active
audience: public
---

# DELEGATION PROTOCOL

> Up: [[dmrzl/identity/CORE|CORE]]

Subagent management rules for DMRZL. CLAUDE.md keeps the condensed version; this file has full details.

## 1. Agent Roster

4 custom domain agents available in `.claude/agents/`. Use the right agent for the job.

| Agent | Model | maxTurns | Memory | Permission | Purpose |
|-------|-------|----------|--------|------------|---------|
| **architect** | Opus | 15 | project | default | Strategic decisions, ADRs, trade-off analysis |
| **coder** | Sonnet | 20 | project | acceptEdits | Unity/ECS implementation, bug fixes, tests ({{src_dir}}/ only) |
| **secretary** | Haiku | 15 | — | default | Vault ops, documentation, file organization |
| **researcher** | Sonnet | 20 | — | default | Web search, docs lookup, API reference, deep analysis |

Plus built-in agents (no definition needed):
- **Explore** (Haiku) — fast codebase search/analysis, read-only
- **Plan** (inherits) — safe read-only planning mode
- **general-purpose** (inherits) — complex tasks needing exploration + action

### When to Use Custom vs Built-in

| Task | Agent | Why |
|------|-------|-----|
| "Find where X is defined" | Explore | Simple search, no domain knowledge needed |
| "Implement new ECS system" | coder | Needs project conventions + edit permissions |
| "Review my changes" | dmrzl-review skill | Two-stage review (spec + quality) |
| "How does IJobEntity work?" | researcher | Needs web search capability |
| "Should we use aspect or query?" | architect | Needs deep reasoning |
| "Update HANDOFF.md" | secretary | Vault task, no code knowledge |
| "Write a bash hook script" | **inline** | Non-Unity code, orchestrator handles directly |
| "Edit CLAUDE.md / skill file" | **inline** | Config/meta files, not project code |
| "Tune BETA_TANK DPS" | dmrzl-dots skill | Balance absorbed into domain expert |
| "Which systems touch GameState?" | Explore (thorough) | Broad codebase search |
| "Cross-system race condition audit" | Explore (very thorough) | Multi-system analysis |

## 2. Query Type Taxonomy

### Straightforward
- Single focused investigation or fact-finding.
- 1 subagent with clear instructions.
- Examples: "What's the current state of System X?", "Find where ComponentY is defined."

### Breadth-first
- Distinct independent sub-questions researched in parallel.
- 2-3 subagents, each handling a separate sub-topic.
- Define clear boundaries between sub-topics to prevent overlap.
- Examples: "Research how 3 different ECS frameworks handle X", "Read these 4 vault docs and summarize."

### Depth-first
- Multiple perspectives on the same issue.
- 3-5 subagents exploring different angles.
- Examples: "Analyze this architecture decision from performance, maintainability, and ECS-pattern angles."

## 3. Subagent Count Guidelines

| Complexity | Count | Example |
|------------|-------|---------|
| Simple | 1 | Find a file, read a doc |
| Standard | 2-3 | Compare approaches, research + implement |
| Complex | 3-5 | Multi-system analysis, deep feature spec |
| Never >5 | — | Restructure approach if >5 needed |

Project context is smaller than web research — cap at 5, not Anthropic's suggested 20.

## 4. Delegation Prompt Format

> **Mandatory checklist:** Every coder/secretary brief must follow [[dmrzl/protocols/CODER_BRIEF_TEMPLATE|CODER_BRIEF_TEMPLATE]]. Reject briefs missing any section.

Every subagent prompt MUST include these 4 elements.

### Why (Context)
- How this subagent's work contributes to the larger task.
- What the user is trying to achieve.
- Helps the subagent filter signal from noise.

### Objective
- 1 core objective per subagent (never 2+).
- Specific and measurable: "find all usages of X" not "look into X."

### Expected Output
- Format: list of files, summary paragraph, code snippet, table, etc.
- Length guidance: "brief summary" vs "comprehensive analysis."

### Constraints
- Tools to prioritize or avoid (e.g. "use Grep, not Bash for search").
- Working directory if relevant.
- Approximate scope: "~5 files", "quick scan", "thorough analysis."
- For Explore subagents: "quick", "medium", or "very thorough."

### Example

```
"You are researching the ECS component data layout in {{project_name}}.

Why: We're adding a new DamageOverTime component and need to understand existing patterns
before choosing where to put it.

Objective: Find all component definition files and their organization patterns.

Expected output: A list of files with their component counts and a summary of the
organizational pattern (which components go where).

Constraints: Use Grep for 'IComponentData' and 'IBufferElementData' in
Assets/Codebase/Core/Data/. Use Read to examine the top files. Quick scan — ~10 files max."
```

## 5. Execution Rules

### OODA Loop & Tool Budget

> Canonical definition: [[dmrzl/identity/CORE|CORE.md]] § MEESEEKS.
> OODA loop (Observe → Orient → Decide → Act) and tool budgets (3-5 simple, 5-10 standard, 10-15 complex, 20 hard cap) are defined there. Do not duplicate here.

### Parallel by default
- Independent subagents MUST launch simultaneously.
- Sequential only when one depends on another's output.
- Never: launch agent A, wait, launch agent B (if independent).

### Diminishing returns
- If last 2-3 tool calls yielded nothing new, stop and report.
- Subagents should not exhaust budget "just because" — exit early when task is done.

### Native enforcement
- `maxTurns` in agent frontmatter enforces hard budget — agent stops when reached.
- `permissionMode: acceptEdits` on coder — no permission prompts for file edits.
- `memory: project` on architect/coder — cross-session learning at `.claude/scratchpad/`.

### Synthesis responsibility
- Subagents gather raw information.
- Main agent (DMRZL) synthesizes, deduplicates, and presents to user.
- Never delegate final synthesis or user-facing output to subagents.

### Error handling
- Subagent failure: main agent adapts approach (different tool, narrower query).
- Never re-delegate same task to another subagent without changing approach.
- Partial results are valuable — report what was found.

## 6. Model Selection for Subagents

| Task type | Agent | Model | Rationale |
|-----------|-------|-------|-----------|
| Log analysis, simple reads | Explore / secretary | Haiku | Fast, cheap, sufficient |
| Codebase exploration | Explore | Haiku | Built-in, read-only |
| Architecture analysis | architect | Opus | Deep reasoning needed |
| Documentation updates | secretary | Haiku | Routine, structured |
| Code implementation | coder | Sonnet | Precision executor with brief, uses Sonnet quota bucket |
| Code review | dmrzl-review skill | Sonnet | Two-stage review (spec + quality) |
| Game balance analysis | dmrzl-dots skill | Sonnet | Domain absorbed into dots |
| Documentation lookup | researcher | Sonnet | Web search + doc fetching + deep analysis |


## 6b. External Codex Operator

> Full protocol: [[dmrzl/tooling/CODEX|CODEX.md]].


## 6c. External Gemini Operator

> Full protocol: [[dmrzl/tooling/GEMINI_CLI|GEMINI_CLI.md]].


## 7. Agent Teams (Parallel Persistent Teammates)

> **Experimental feature.** Requires `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in settings.json env.

Agent Teams are distinct from subagents (§1-6). Subagents are fire-and-forget tasks dispatched by the orchestrator. **Teams** are persistent parallel sessions with their own context windows, MCP access, and inter-agent messaging.

### When to Use Teams vs Subagents

| Signal | Subagents | Teams |
|--------|-----------|-------|
| One-shot research/implementation | ✓ | |
| Task needs <20 tool calls | ✓ | |
| Agents need to exchange findings mid-task | | ✓ |
| 2+ independent FPR items in parallel | | ✓ |
| Multi-system feature touching 5+ files each | | ✓ |
| Simple file read / search | ✓ | |

**Rule of thumb:** if agents would benefit from their own 1M context window and direct messaging, use a team. If a structured brief and results are enough, use subagents.

### Team Lifecycle

```
1. TeamCreate(team_name, description)
2. TaskCreate (shared task list — all teammates see it)
3. Agent(team_name=..., name=...) per teammate
4. SendMessage for coordination
5. TaskUpdate as work completes
6. SendMessage(shutdown_request) to each teammate
7. TeamDelete (after all teammates shut down)
```

### Standard Team Compositions

**Feature Team (2-3 teammates):**
```
Lead (Opus) — orchestrator, user-facing, synthesis
  ├─ implementer-1 (general-purpose) — writes code for feature A
  └─ implementer-2 (general-purpose) — writes code for feature B
```

**Review Team (2 teammates):**
```
Lead (Opus) — orchestrator, final verdict
  ├─ reviewer-code (general-purpose) — code quality + tests
  └─ reviewer-spec (general-purpose) — spec compliance + architecture
```

**Research + Implement (2 teammates):**
```
Lead (Opus) — orchestrator, synthesis
  ├─ researcher (general-purpose) — reads code, explores, writes findings to scratchpad
  └─ implementer (general-purpose) — reads findings, implements
```

### Teammate Configuration

- **subagent_type:** `general-purpose` (needs full tool access: Read, Write, Edit, Bash, Grep, Glob)
- **mode:** `bypassPermissions` for implementers working on {{src_dir}}/ only
- **model:** inherit from lead (Opus) or explicit override (`sonnet` for routine implementation)
- Always pass `team_name` and `name` params to Agent tool

### Task List Protocol

1. Lead creates ALL tasks upfront with dependencies via `TaskCreate`
2. Tasks include: title, description, acceptance criteria, blocked_by (if any)
3. Teammates check `TaskList` after completing each task
4. Teammates claim unassigned tasks via `TaskUpdate(owner=name)`
5. Teammates mark done via `TaskUpdate(status=completed)`

### Messaging Rules

- **Lead → Teammate:** assignments, context, course corrections
- **Teammate → Lead:** completion reports, blockers, findings
- **Teammate → Teammate:** direct coordination when they share boundaries (e.g., shared file, API contract)
- **Broadcast (`to: "*"`):** only for critical state changes that affect everyone
- **Never:** structured JSON status messages (use TaskUpdate instead)

### Brief Format for Teammates

Same 6-element format as subagents (§4): Why, Objective, Output, Tools, Budget, Near-misses. Plus:
- **Team context:** which other teammates exist and what they're doing
- **Shared files:** which files are touched by multiple teammates (coordinate via messaging before editing)
- **Exit condition:** when to stop and report back vs when to continue autonomously

### File Conflict Prevention

When multiple teammates edit the same codebase:
1. **Disjoint files:** no coordination needed (ideal — plan tasks to minimize overlap)
2. **Shared files:** one teammate "owns" the file, others message with requested changes
3. **Shared contracts** (interfaces, components): define contract first (lead or architect), then implement in parallel
4. **Never:** two teammates editing the same file simultaneously

### Shutdown Protocol

1. Lead verifies all tasks are completed via `TaskList`
2. Lead sends `SendMessage(to: name, message: {type: "shutdown_request"})` to each teammate
3. Wait for each teammate to approve shutdown
4. After all teammates shut down → `TeamDelete`

### Cost Awareness

Each teammate consumes a full context window. A 3-member team uses 3x the tokens of a single session. Use teams when the parallelism benefit justifies the cost:
- **Worth it:** 2 independent FPR items (saves a full session of sequential work)
- **Not worth it:** task that one agent can do in 10 tool calls

---

## 8. Complexity-Based Model Escalation

Default model per agent (Section 6) can be overridden based on task complexity.

### Override Rules

| Signal | Action |
|--------|--------|
| Task touches 1-2 files, clear scope | **Coder default (Sonnet)** is fine |
| Task touches 5+ files or cross-system | **Escalate coder → Opus** via `model: "opus"` param |
| Architecture decision, race condition, security | **Escalate**: any agent → Opus via `model: "opus"` param |
| Simple vault/doc update | **Downgrade**: secretary stays Haiku, never escalate |
| Codebase exploration | **Explore → Sonnet** (pass `model: "sonnet"` explicitly) |

**Quota strategy:** Sonnet has a separate usage bucket ("Sonnet only"). Route agents to Sonnet by default to preserve the shared "All models" quota for Opus orchestrator. Only escalate to Opus when deep reasoning is genuinely needed.

### Model Override Syntax

Agent tool → `model: "opus"` | `"sonnet"` | `"haiku"` parameter.

Override only when complexity clearly diverges from agent's default tier. Most tasks use the default.

### Shadow Validation (monthly)

Review `.claude/feedback-loops/agent-usage.log`. Check:
- Did Opus agents get simple tasks? (wasteful)
- Did Haiku agents fail on complex tasks? (underpowered)
- Adjust roster defaults if pattern persists.

## 9. Anti-Patterns

- Spawning a subagent for a task you could do in 1-2 tool calls.
- Giving a subagent 3+ objectives (split into separate subagents).
- Omitting "Why" from the delegation prompt (subagent loses context).
- Sequential when parallel is possible (wastes time).
- Over-researching: 10 subagents for a simple question.
- Delegating user communication to subagents (main agent's job).
- Using general-purpose when a specialized agent exists (loses domain knowledge).
- Ignoring `maxTurns` enforcement — if agent hits limit, task was too broad.

## 10. Coder Workflow

```
research → plan → execute → verify → review
```

### Verification (mandatory before "done")
Every coder agent MUST before reporting completion:
1. Run the appropriate verification command (compile / test / runtime check)
2. Read the full output
3. Report results with evidence

### Two-Stage Review (post-task)
After each significant task (2+ files modified or new public API):
1. Orchestrator dispatches Stage 1 review (spec compliance) — Sonnet subagent, read-only
2. Orchestrator dispatches Stage 2 review (code quality) — Sonnet subagent, read-only
3. Critical issues → fix immediately. Important → fix before merge. Minor → note for later.

Single-file tweaks and config changes skip review.

Full review templates: see dmrzl-review skill.

### Spec Review Loop (post-dmrzl-spec)
After writing a specification (dmrzl-spec output), review is AUTOMATIC:
1. Orchestrator dispatches spec-reviewer subagent (Sonnet, read-only) immediately after spec is written
2. If gaps found — fix, re-dispatch
3. Max 3 iterations, then escalate to user
4. User confirms final version before implementation
This is not optional — every dmrzl-spec invocation that produces a written spec triggers the review loop.



## 11. Context Exhaustion Protocol

When a coder agent approaches context limits mid-task, do NOT compact or summarize in-place. Context reset is superior to compaction for maintaining coherence (source: Anthropic harness-design article).

### Detection

Signs of context exhaustion:
- Agent starts rushing or cutting corners on verification
- Output quality drops noticeably in later turns
- Agent hits maxTurns limit with work remaining
- Agent explicitly mentions context limits

### Recovery: Fresh Agent with File-Based Handoff

1. **Coder writes progress report** to a scratch file:
   ```
   vault/{{project_slug}}/management/plans/<feature>/progress-report.md
   ```
   Contents: what's done, what's remaining, files changed, current blockers, test status.

2. **Orchestrator spawns fresh coder** with:
   - Original brief (from file, not from context)
   - `git diff` of work so far (fresh state evidence)
   - Progress report (what's done, what remains)
   - Acceptance criteria (unchanged from original brief)

3. **Fresh coder reads files first**, does NOT rely on any "summary" of previous work.

### Rules

- Never ask the exhausted agent to "summarize what you've done" — it's unreliable at high context usage
- The git diff IS the source of truth for what was implemented
- If coder hits maxTurns 2x on the same feature → the brief is too broad. Split into smaller briefs.
- Progress report is written BY the coder agent (it knows what it did), read BY the orchestrator (who decides next steps)
