---
tags: [dmrzl, protocol]
type: config
status: active
audience: public
---
# VERIFICATION.md — Runtime Verification Protocol

> Up: [[dmrzl/identity/CORE|CORE]]

Establishes the 3-tier evidence chain for implementation verification. Phase deliverables land with proof, not assertions.

## Rule

**No phase is "done" without Tier 1 + (Tier 2 OR Tier 3) evidence.** Pick based on what the phase changes:

| Phase changes | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|---|
| Data model / pure logic | ✓ required | skip | spot-check |
| Systems / behavior | ✓ required | ✓ required | on gaps |
| UI / user flow | ✓ required | skip (manual) | ✓ required |

## Tier 1 — EditMode tests (unit layer)

**Fastest path to evidence.** Covers: structs, static methods, pure logic, serialization, migration paths.

- Location: `{{project_root}}/Assets/Tests/EditMode/`
- Asmdef: `{{project_name}}.Tests.EditMode.asmdef`
- Run: `bash .claude/scripts/run-unity-tests.sh --platform EditMode`
- **Caveat: requires Unity Editor CLOSED** (batch mode conflict). CI on `darwin-mac` runs them on every push.
- Patterns in scope: NUnit `[Test]`, `[SetUp]`/`[TearDown]`, `Category("Data")` or similar.
- Backup/restore real save files in `[SetUp]`/`[TearDown]` when tests touch `persistentDataPath` (MetaSaveData.SavePath is hardcoded — no path indirection).

Minimum for a new phase: 2-5 tests covering the new data shape + any migration path.

## Tier 2 — Scenario (integration layer)

**Proves runtime behavior in a controlled session.** Covers: spawning, waves, combat, economy flow, tier gates, UI signals.

- Scenarios live in `{{project_root}}/Assets/StreamingAssets/Scenarios/` (35+ files, JSONL, one `GameCommand` per line)
- Override: `persistentDataPath/Scenarios/<name>.json` checked first
- Command schema: `{"action":"<name>","int_value":N,"float_value":N,"string_value":"S"}`
- Supported commands (via `CommandExecutorSystem`): `set_wave`, `set_biomass`, `set_colony_health`, `set_essence`, `spawn_alpha`, `spawn_enemies`, `kill_all_beta`, `pause`, `resume`, `trigger_game_over`, `scenario_mode`, `scenario_done`, `assert`, `wait`, `batch_start/end`, `snapshot`, `goap_dump`, etc.
- `assert` evaluator metrics: `alpha_count`, `beta_count`, `biomass`, `essence`, `colony_health`, `wave`, `game_over`, `idle_count`, `goal_any/none/pct` — extend `EvaluateAssertion` when new state needs assertion support

**Launch order (CRITICAL):** write `commands.jsonl` BEFORE entering Play mode. Order reversal silently fails.

Run: `bash .claude/scripts/run-scenario.sh <name>` OR `run-all-scenarios.sh` for CI sweep. Telemetry writes PASS/FAIL via `SCENARIO_DONE` event to `telemetry.jsonl`.

## Tier 3 — Runtime inspection (gap filler)

**One-shot runtime query when Tier 1/2 don't cover a specific check.** Covers: reflection on struct shapes, `Resources.LoadAll` counts, ECS singleton field values, save-file content on disk.

Strategy: write a temporary editor menu item → invoke via `mcp__anklebreaker-unity__unity_execute_menu_item` → read output → **delete the menu file**. Do not leave verification scaffolding in the repo.

Template: `Tools/Darwin/<PhaseN> Verify Runtime` with reflection + file reads, writes report to `persistentDataPath/<phaseN>_verify.txt` for retrieval via `Read` tool.

**Why not `unity_execute_code`:** Roslyn not available in this Unity version (`Microsoft.CodeAnalysis` missing). Menu-item pattern is the workaround.

## Autonomous Debug Loop

For behavior bugs (Phase 1+), the loop from `CLAUDE.md § Unity Debug Flow` applies:

1. Stop Play mode before edit
2. Edit ONE thing
3. `Assets/Refresh` → `unity_get_compilation_errors` (must be zero)
4. `unity_play_mode` (enter) → wait 8s init delay
5. Write commands to `commands.jsonl` (or use scenario)
6. Dump state via `Tools/GOAP Debug Dump` or similar
7. Screenshot via `{"action":"screenshot"}` → Read image
8. Analyze. If wrong, back to step 1. **Never tweak parameters — trace the pipeline.**

## Phase 0 reference application (tier-progression)

Real example of this protocol in use:

- **Tier 1**: 5 EditMode tests in `MetaSaveDataTests` (2) + `MetaSaveSystemMigrationTests` (3) — cover SchemaVersion roundtrip, v1 JSON deserialization, v1→v2 migration seeding, idempotent re-migration, v2 no-op.
- **Tier 3**: temp menu `Tools/Darwin/Phase0 Verify Runtime` — listed 18 SOs, dumped MetaSaveData/MetaProgressionSingleton field shapes via reflection, read current save file, deserialized fabricated v1 JSON. Deleted after evidence captured.
- **Tier 2 skipped**: Phase 0 is pure data layer, no runtime behavior to scenario-test. Phase 1+ (essence pipeline, tier gate) will add scenario coverage.

## Anti-patterns (banned)

- "Compiles clean → ship it" — compile is necessary not sufficient
- "Tests compile → tests pass" — trust but verify, run them
- Leaving temp verify menus / Editor scripts in repo after session
- Batch-mode tests while Editor is open (silent hang)
- Writing `commands.jsonl` AFTER Play mode (commands never consumed)
- Using `Debug.Log` instead of `TelemetryWriter` for scenario assertions (wrong channel — telemetry is single source for PASS/FAIL)
