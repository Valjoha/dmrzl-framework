---
tags: [dmrzl, protocol, tdd]
type: config
status: active
audience: public
maturity: stable
created: 2026-05-03
---
# TDD Protocol

> Up: [[CORE]]

**No production code without a failing test first.** Applies to new features, bug fixes, refactors, behavior changes.

## Cycle (RED → GREEN → REFACTOR)

1. **RED** — write minimal test for the behavior you want. ONE test, real code, no mocks unless unavoidable.
2. **Verify RED** — run the test. Confirm it fails for the right reason (feature missing, not typo). Mandatory, never skip.
3. **GREEN** — write simplest code that makes it pass. No extras, no YAGNI features.
4. **Verify GREEN** — run the test. Confirm pass. Confirm other tests still pass.
5. **REFACTOR** — clean up while green. Don't add behavior.

## Iron Law Violations (delete on sight)

- Code written before test → delete and start over
- Test written after code → tests-after answer "what does this do?", not "what should this do?"
- Test passes immediately → rewrite the test (testing existing behavior)
- "Just this once" rationalizations → ignore; that IS the rationalization

## Exceptions

Ask user first: throwaway prototypes, generated code, configs.

## Bug Fix Protocol

Reproduce bug as failing test FIRST. Fix is proven by test going green. Never fix bugs without a test.
