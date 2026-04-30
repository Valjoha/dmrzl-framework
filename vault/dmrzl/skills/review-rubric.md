---
tags: [dmrzl, skill, review]
type: reference
status: active
created: 2026-03-26
audience: public
---
# Code Review Rubric

> Up: [[dmrzl/skills/dmrzl-review|dmrzl-review]]

Concrete pass/fail criteria for Stage 2 code quality review. Each criterion has a severity, a pass condition, and a fail condition. The reviewer MUST evaluate every applicable criterion and report PASS or FAIL — never skip silently.

## Reviewer Stance

**Default: skeptical.** Assume code has issues until you prove otherwise. If you find zero issues in a diff touching 100+ lines, re-examine — you likely missed something. Your job is to catch what the generator missed, not to validate their work.

Read the diff twice: once for understanding, once for issues.

---

## Domain 1: ECS Safety (Critical)

| # | Criterion | PASS | FAIL |
|---|-----------|------|------|
| E1 | Structural changes via ECB | All `CreateEntity`, `DestroyEntity`, `AddComponent`, `RemoveComponent` use `EntityCommandBuffer` (or `ECB` from `SystemState`) | Any structural change via `EntityManager` inside a job or query iteration |
| E2 | Collect-first pattern | Entities/components collected into `NativeList` before ECB playback | ECB operations interleaved with query iteration that reads the same archetypes |
| E3 | Singleton reset ordering | `SetSingleton`/singleton writes happen BEFORE `ECB.Playback` in same `OnUpdate` | `SetSingleton` after `CreateEntity`/`DestroyEntity` in same system update |
| E4 | System ordering | `[UpdateInGroup]`, `[UpdateBefore]`, `[UpdateAfter]` attributes present and correct for data dependencies | Missing ordering attributes when system reads data written by another system in same group |
| E5 | IEnableableComponent | Boolean-state components use `SetComponentEnabled` instead of add/remove | ECB add/remove for toggling a boolean state (e.g., `IsActive`, `IsDead`) when `IEnableableComponent` would suffice |

## Domain 2: Burst/Jobs (Critical)

| # | Criterion | PASS | FAIL |
|---|-----------|------|------|
| B1 | BurstCompile attribute | Every `ISystem` and every `IJobEntity`/`IJobChunk` struct has `[BurstCompile]` | Missing `[BurstCompile]` on any system or job struct |
| B2 | No managed types in jobs | Job structs contain only blittable types, `NativeContainer`, `ComponentLookup`, `BufferLookup` | `string`, `class`, `List<>`, `Dictionary<>`, managed arrays, or boxing inside Burst-compiled code |
| B3 | NativeContainer disposal | Every `NativeList`/`NativeArray` allocated in `OnUpdate` is disposed by end of method or via `Allocator.Temp` | `NativeContainer` with `Allocator.Persistent`/`TempJob` without corresponding `Dispose` |
| B4 | No Debug.Log in Burst | Logging uses `Helpers.Log` (managed, outside Burst) | `UnityEngine.Debug.Log` called from Burst-compiled code path |

## Domain 3: Performance (Important)

| # | Criterion | PASS | FAIL |
|---|-----------|------|------|
| P1 | No per-frame allocations | Hot-path code uses `NativeContainer` or stack allocation. No `new List<>()`, `ToArray()`, `ToString()` per frame | Managed allocation in `OnUpdate` that runs every frame (GC pressure) |
| P2 | Query filters | `EntityQuery` uses `WithAll`/`WithNone`/`WithAny` to minimize iteration | Query iterates all entities and filters with `if` statements inside the loop |
| P3 | ComponentLookup caching | `ComponentLookup<T>` obtained in `OnCreate` or as system field, updated via `.Update(ref state)` in `OnUpdate` | `GetComponentLookup<T>` called every frame inside `OnUpdate` |
| P4 | No CreateEntityQuery per frame | `EntityQuery` created in `OnCreate` and cached | `CreateEntityQuery`/`GetEntityQuery` called inside `OnUpdate` |

## Domain 4: Project Conventions (Important)

| # | Criterion | PASS | FAIL |
|---|-----------|------|------|
| C1 | FQN for shadowed types | `UnityEngine.Camera`, `UnityEngine.Debug`, `UnityEngine.Physics` used with full namespace | Bare `Camera`, `Debug`, `Physics` in files under `Core.*` namespace |
| C2 | Helpers.Log only | All runtime logging uses `Helpers.Log` | `Debug.Log`, `Debug.LogWarning`, `Debug.LogError` in runtime code (test code exempt) |
| C3 | Extract-to-Static | Testable math/logic in `public static` methods | Complex calculations inline in `OnUpdate` with no static extraction |
| C4 | Namespace matches path | Class namespace matches folder structure under `Assets/Codebase/` | Namespace doesn't match folder (e.g., class in `Core/Waves/` but namespace is `Core.Colony`) |
| C5 | Components in Data/ | New `IComponentData`/`IBufferElementData` defined in `Assets/Codebase/Core/Data/` | Component defined in system file or random location |

## Domain 5: CI Readiness (Gate)

| # | Criterion | PASS | FAIL |
|---|-----------|------|------|
| G1 | Compiles clean | `dotnet build` exits 0 with no warnings relevant to changed files | Build errors or warnings in changed files |
| G2 | Meta files | Every new `.cs` file has a corresponding `.meta` file | `.cs` file without `.meta` (Unity will regenerate with random GUID, breaking references) |
| G3 | No BSD grep | Shell scripts use `python3` or `grep -E` for regex, never `grep -P` | `grep -P` in any `.sh` file (fails on macOS) |

---

## How to Use This Rubric

1. For each changed file, identify which domains apply (e.g., a new ISystem → E1-E5, B1-B4, P1-P4, C1-C5, G1-G2)
2. Evaluate each applicable criterion as PASS or FAIL
3. Report:
   - **All FAILs** with file:line and explanation
   - **Summary**: X criteria checked, Y passed, Z failed
   - **Severity**: Critical FAILs block merge. Important FAILs fix before merge. Gate FAILs block push.
4. If all criteria PASS and diff is >100 lines, state explicitly: "Re-examined: confirmed clean after second pass."
