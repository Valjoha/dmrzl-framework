---
name: dmrzl-ui-design
description: "Generate UI mockups via Stitch MCP and convert to Unity UXML/USS. Use when user says 'design UI', 'create screen', 'mockup', 'stitch screen', 'new UI element', 'UI for feature', or when a spec includes UI requirements. Covers full pipeline: prompt construction → Stitch generation → validation → HTML→UXML conversion → responsive rules."
user_invocable: true
audience: public
---

# Stitch UI Design Pipeline

Load protocol from vault: `read-note(filename: "STITCH.md", folder: "dmrzl/protocols")`
Load design system: `read-note(filename: "DESIGN.md", folder: "darwin/technical")`
Detailed pipeline reference: [REFERENCE.md](REFERENCE.md)

## Prerequisites

Before invoking:
1. An approved UI spec exists (from dmrzl-spec or explicit user request)
2. The screen's exact content is defined (elements, data, layout)
3. User has confirmed Stitch rate budget for this

## Workflow

### Phase 1: Prompt Construction
Read game state + DESIGN.md + STITCH.md protocol + existing screens via `mcp__stitch__list_screens`. Construct prompt using Max Context Template (system preamble · screen spec · content list · layout · REMOVALS · existing screens). **Show prompt to user for approval.** Full detail in REFERENCE.md.

### Phase 2: Generation
Portrait first (`deviceType: "MOBILE"`), download screenshot, run 8-check validation (hard edges, palette, count, typography, touch ≥44px, transparency, content accuracy, orientation), show result. User decides approve/iterate/reject. Max 3 iterations. Repeat for landscape (`DESKTOP`) after portrait approved. Full detail in REFERENCE.md.

### Phase 3: Conversion (HTML → UXML/USS)
After both orientations approved: download HTML, parse DOM, map CSS → USS tokens (colors → `var(--bg-*)`, sizes → `var(--fs-*)`, spacing → `var(--sp-*)`, border-radius → 0px), generate UXML + USS + responsive `.is-portrait` overrides, wire into GameUI.uxml, **show generated code for user review before writing**. Full detail in REFERENCE.md.

### Phase 4: Logging
Log to `vault/{{project_slug}}/technical/stitch-usage-log.md`: date, screen name, orientation, model, attempt, result, screen ID.

## Anti-Patterns (HARD RULES)

- **NEVER** generate without approved spec or explicit user request
- **NEVER** skip validation checklist
- **NEVER** hardcode colors/sizes (use CSS variable tokens)
- **NEVER** exceed 3 iterations per screen
- **NEVER** generate both orientations simultaneously
- **NEVER** trust Stitch content — verify against game state
- **NEVER** write UXML/USS without user reviewing generated code
