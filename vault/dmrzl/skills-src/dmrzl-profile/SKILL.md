---
name: dmrzl-profile
description: "Analyze {{project_name}} profile artifacts produced by com.dmrzl.profiler-bridge. Use when the user says 'analyze profile', 'compare runs', 'profile diff', 'check perf regression', 'noise floor', 'aggregate runs', or asks about results from a behavior-mixed-full / phase1-smoke session. Reads JSONL under ~/Library/Application Support/Valjoha/{{project_name}}/Profiling/. Five commands: list, show, diff, agg, noise. Multi-run averaging is the gating tool — single-run comparisons are below noise floor for stochastic scenarios."
audience: public
category: profiling
platforms: [general]
cache_safe: true
tags: [profiling, profiler-bridge, perf, darwin]
related_skills: [dmrzl-dots, dmrzl-debug]
type: config
status: active
---

# dmrzl-profile

> Up: [[dmrzl/skills|Skills]]

Cross-session analysis of `com.dmrzl.profiler-bridge` artifacts. Reads from
`~/Library/Application Support/Valjoha/{{project_name}}/Profiling/`.

## When to use

- "show results of the last profile run"
- "diff sessions A vs B"
- "check perf regression in SwarmSteering"
- "noise floor across N runs of the same scenario"
- "average 5 post-Burst runs"

## When NOT to use

- Single-shot debugging — use `dmrzl-debug` (Unity console + Editor.log).
- Running a profile session — that's `DMRZL/Profiler/Run [xN] + Profile <scenario>`
  menu (single or batch x3/x5; see "Capturing batches" below), not this skill.
- Writing a brand-new analysis dimension — extend `dmrzl_profile.py` directly.

## Quick reference

Script lives at `vault/dmrzl/skills-src/dmrzl-profile/dmrzl_profile.py`.
PEP 723 inline metadata — runs via `uv run` or plain `python3` (stdlib only).

```bash
python3 vault/dmrzl/skills-src/dmrzl-profile/dmrzl_profile.py list 10
python3 .../dmrzl_profile.py show 20260511_090111_behavior-mixed-full
python3 .../dmrzl_profile.py diff <baseline_id> <treatment_id>
python3 .../dmrzl_profile.py agg <id1> <id2> <id3> <id4> <id5>
python3 .../dmrzl_profile.py noise <id1> <id2> <id3>
```

Session arg accepts: full path, or bare session-id (script looks under the
default profiling root).

## Capturing batches (S240)

`DMRZL/Profiler/Run x3 + Profile <scenario>` (and x5 variant) chains N runs of
the same scenario back-to-back. Each run writes its own session directory under
`Profiling/`. On batch completion, the Console logs the N session-ids plus a
ready-to-paste `dmrzl-profile agg` / `noise` command. Batch state survives
play-mode exit via EditorPrefs `DMRZL.Profiler.Batch*`; if a run fails to
produce an artifact, the batch halts and prefs are cleared.

## Operational rules

1. **Single-run diff is unreliable.** Stochastic GOAP + swarm formation
   produces ×10 variance on per-system markers in `behavior-mixed-full`
   (verified S239). Use `agg` over ≥3 runs and `noise` to establish CV%
   before claiming a treatment delta. Effect must exceed CV.

2. **Markers that always report 0 are not bugs in your run** — `cpu.jsonl`
   contains by-name registrations that may not bind to any real Unity
   marker (see S239 Addendum 2). The `show` and `diff` commands filter
   them out automatically; raw `cpu.jsonl` greps may surface them.

3. **PlayerLoop is the only frame-level signal** that always populates.
   Use it as a sanity check — if PlayerLoop reads 0, the session
   didn't actually capture anything (likely Mount() race; see RCA
   `2026-05-09-profiler-bridge-live-validation`).

4. **Trim noise before reporting.** When summarizing to user, drop the
   all-zero markers; show only meaningful diffs (Δ > 10% AND outside
   noise floor).

## Output discipline

- Tables align on monospace; trim to ~6-8 markers max in summary unless
  user asks for full dump.
- Lead with PlayerLoop (frame-level), then the top 3 per-system markers
  by absolute time cost, then the top 3 by Δ% (treatment effect).
- If the diff is below noise floor, **say so**. Don't invent significance.

## See also

- [[../../../darwin/research/2026-05-09-profiler-bridge-live-validation|Live validation RCA]]
- [[../../../darwin/management/plans/2026-05-09-profiler-bridge-package-spec|Profiler-bridge spec]]
