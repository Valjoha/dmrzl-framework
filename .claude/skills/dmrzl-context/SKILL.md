---
description: "Smart vault context retrieval. Expands topic query via GLOSSARY.md, searches vault, returns ranked results. Use when: 'what do we know about X?', 'context for Y', 'load context on Z', or before starting domain work. Do NOT use for: simple file reads, git history, code-only questions."
audience: public
name: dmrzl-context
category: tools
platforms: [general]
cache_safe: true
tags: [vault, context-retrieval, search]
related_skills: [dmrzl-spec, dmrzl-research]
requires_tools: [obsidian-mcp-rs]
type: config
status: active
---
<!-- GENERATED FROM vault/dmrzl/skills-src/dmrzl-context/SKILL.md -- DO NOT EDIT. Run sync-skills.py to refresh. -->
# /dmrzl-context — Smart Vault Retrieval

Transform a topic query into a ranked list of the most relevant vault notes. No external deps — GLOSSARY.md + Obsidian MCP only.

## Algorithm

### 1. Parse Query
Extract key terms. Examples:
- "GOAP gatherers not moving" → `GOAP`, `gatherers`, `movement`
- "how does the wave system work?" → `WaveSystem`, `waves`, `spawn`
- "fix combat damage" → `combat`, `DamageBufferElement`, `DamageSystem`

### 2. Expand via GLOSSARY
`read-note(vault: "vault", filename: "GLOSSARY.md", folder: "darwin/technical")`. For each extracted term: find matching entry (exact or substring), collect `Related:` terms, collect `Files:` paths. Expands 2-3 → 8-15 concepts.

### 3. Search Vault
Via `search-vault`:
1. Primary terms (from query) — weight HIGH
2. Related terms (glossary expansion) — weight MEDIUM
3. Glossary `Files:` paths — search by filename, weight HIGH

**Search rules:**
- **One term per query** — Obsidian MCP treats multi-word as exact phrase, NOT boolean AND. Search each separately.
- **Skip high-frequency terms** — generic words (`wave`, `architecture`, `system`, `component`) flood with 100s of matches. Use domain-specific glossary expansion (e.g., `WaveSystem`, not `wave`).
- **Scope broad searches** — use `path:` parameter (`path: "darwin/adr"`) to limit. Prevents 300+ floods.
- **Glossary `Files:` → filename stem** — extract bare filename (`vault/{{project_slug}}/adr/008-Spawn-Network-Ownership.md` → `008-Spawn-Network-Ownership`), use `searchType: "filename"`. Strip folder prefixes.
- **Max 5 search queries** — 2 primary + 1-2 related + 1 filename. Don't over-search.

### 4. Rank Results

| Signal | Weight |
|--------|--------|
| Direct glossary `Files:` ref | +3 |
| Primary term in title | +3 |
| Primary term in content | +2 |
| Related term match | +1 |
| ADR (decision record) | +1 bonus |
| Recency (modified <7d) | +1 bonus |
| Plan (management/plans/) | +0.5 bonus |

### 5. Return Context

```
## Context for: [query]
**Expanded terms:** [list]

### Top Results (ranked, max 7)
1. **[title]** (score: X) — [1-line summary]
   Path: `vault/path/to/note.md`

### Suggested Reads (priority order)
1. `read-note(vault: "vault", filename: "X.md", folder: "Y")`
```

## Usage

```
/dmrzl-context GOAP gatherers not moving
/dmrzl-context wave system architecture
/dmrzl-context how does genetics work
```

Other skills/agents can invoke mentally (follow algorithm) or request orchestrator to run `/dmrzl-context` before starting work. Glossary always at `vault/{{project_slug}}/technical/GLOSSARY.md`.

## Auto-File Substantial Results (Karpathy Wiki Discipline)

When a context query produces a synthesis of **500+ words** (not just a link list):

1. Prompt user: "Зберегти цей аналіз у vault?" — default YES for research, NO for status/debug
2. If yes: create doc in `darwin/technical/` (or appropriate subdir) with full frontmatter (`type: query`, `status: active`, `tags:`, `sources:`, `created:`)
3. Cascade: search 3-5 related pages, add bidirectional wikilinks
4. Update relevant INDEX.md
5. Ops log: append to `vault/dmrzl/session/ops-log.md`: `YYYY-MM-DD | S### | QUERY | path | summary`

## Rules

1. GLOSSARY.md is the expansion source — if a term isn't there, search directly without expansion
2. Max 5 search queries — don't burn context
3. Progressive loading — return paths first, caller decides what to read in full
4. Never fabricate summaries — only summarize content actually read
5. Recency matters — recent HANDOFF and plans often have freshest context
6. ADRs are authoritative — rank high (decisions > descriptions)
