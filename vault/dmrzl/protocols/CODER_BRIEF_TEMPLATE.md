---
tags: [dmrzl, protocol]
type: config
status: active
audience: public
---
# Coder/Secretary Brief Template

> Up: [[dmrzl/protocols/DELEGATION]]

Every coder or secretary agent prompt MUST include ALL of these sections. Missing any section = reject the brief and add it before spawning.

## Required Sections

### 1. WHY (Context)
- What problem does this solve?
- How does this fit in the current session's goal?

### 2. OBJECTIVE (One sentence)
- Exactly ONE deliverable per agent
- Bad: "Fix bugs and add tests and refactor"
- Good: "Add Pipeline Tracing phase to dmrzl-debug skill"

### 3. SPECIFICATION (Exact details)
- **Files to create**: exact paths
- **Files to modify**: exact paths + line ranges if known
- **Expected behavior**: what the code should do after changes
- **Edge cases**: known gotchas

### 4. CONTEXT (Code + Research)
- Relevant code snippets (paste, don't reference)
- Research findings from explorer/researcher agents
- Related systems that must NOT be broken

### 5. CONSTRAINTS (Hard rules)
- [ ] Vault operations: include explicit vault root path (`{{workspace_root}}/vault/`)
- [ ] Append-only files: "READ file first, APPEND new section, PRESERVE all existing content"
- [ ] FQN rule: `UnityEngine.Camera`, `UnityEngine.Debug` etc. in {{project_name}} code
- [ ] No scope creep: only touch files listed in Specification
- [ ] Compile check: run `dotnet build` after C# changes

### 6. ACCEPTANCE CRITERIA (Sprint Contract)

Pre-agreed "done" conditions. Each criterion MUST be verifiable by a specific command, test, or observable output. The coder and orchestrator agree on these BEFORE implementation starts.

Format:
```
- [ ] [Criterion]: [verification command or method]
```

Example:
```
- [ ] WaveSystem pauses within 1 frame of pause_waves command: EditMode test `WaveSystemTests.PauseWaves_StopsAllSpawners`
- [ ] Resume restores previous wave count: EditMode test `WaveSystemTests.ResumeWaves_RestoresCount`
- [ ] No compilation warnings in changed files: `dotnet build ... -v q` output clean
- [ ] Existing 282 EditMode tests still pass: `bash .claude/scripts/run-unity-tests.sh --platform EditMode`
```

Rules:
- Minimum 3 criteria per brief (the task + regression + compilation)
- Every criterion must name a command, test, or file to check
- "It works" is NOT a criterion. "Test X passes" IS.
- Coder must verify ALL criteria before reporting done and include evidence (command output) in the report

### 7. VERIFICATION (Proof of done)
- What command proves success?
- What does passing output look like?

> Note: §7 covers the verification commands themselves. §6 covers what those commands must prove. Both are required.

### 8. NON-GOALS (What NOT to do)
- Explicit list of tempting-but-wrong side tasks

## Secretary-Specific Additions

When delegating to secretary agent, ALWAYS include:
- **Vault root path**: `{{workspace_root}}/vault/`
- **Append-only rule**: "Read the target file FIRST. Append new content at the end. NEVER truncate or overwrite existing content."
- **English-only rule**: no Ukrainian in vault files (except direct user quotes)