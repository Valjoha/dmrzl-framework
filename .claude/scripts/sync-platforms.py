#!/usr/bin/env python3
# AUDIENCE: public
"""Mirror skills/commands/agents from .claude/ to other platform dirs (.gemini/, .codex/).

Reads .claude/registry.json (build via build-registry.py first) and copies
each skill's folder into the target platform's `skills/` directory.

Audience filter: only public + friends skills are mirrored to other platforms
by default. Use --include-private to override.

Platform-specific transformations are minimal in v1 — the assumption is that
SKILL.md format is portable. Add per-platform adapters here as Gemini/Codex
diverge.

Usage:
    python3 .claude/scripts/sync-platforms.py --platform gemini             # dry-run
    python3 .claude/scripts/sync-platforms.py --platform gemini --apply
    python3 .claude/scripts/sync-platforms.py --platform gemini --apply --include-private
    python3 .claude/scripts/sync-platforms.py --check                       # verify registry only

Output structure:
    .gemini/skills/<skill-id>/SKILL.md
    .codex/skills/<skill-id>/SKILL.md   (when implemented)

Phase 2 (Gemini parity) target: skills + custom commands TOML.
Phase 3 target: subagents → .gemini/agents/*.md.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / ".claude" / "registry.json"
SOURCE_SKILLS = ROOT / ".claude" / "skills"

PLATFORM_TARGETS = {
    "gemini": ROOT / ".gemini",
    "codex": ROOT / ".codex",
    "openclaw": ROOT / ".openclaw",
}


def load_registry() -> dict:
    if not REGISTRY_PATH.exists():
        print(f"FAIL: registry.json not found at {REGISTRY_PATH}", file=sys.stderr)
        print("Run: python3 .claude/scripts/build-registry.py", file=sys.stderr)
        sys.exit(1)
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def filter_skills(skills: list[dict], include_private: bool) -> list[dict]:
    keep = []
    for s in skills:
        if s["audience"] == "private" and not include_private:
            continue
        keep.append(s)
    return keep


def sync_skill(skill: dict, target_root: Path, apply: bool) -> str:
    src_folder = SOURCE_SKILLS / skill["folder"]
    if not src_folder.exists():
        return f"MISS {skill['id']}: source folder not found"
    dst_folder = target_root / "skills" / skill["folder"]
    if apply:
        dst_folder.mkdir(parents=True, exist_ok=True)
        for item in src_folder.iterdir():
            if item.is_file():
                shutil.copy2(item, dst_folder / item.name)
            elif item.is_dir():
                if (dst_folder / item.name).exists():
                    shutil.rmtree(dst_folder / item.name)
                shutil.copytree(item, dst_folder / item.name)
    return f"OK   {skill['id']} → {dst_folder.relative_to(ROOT)}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=list(PLATFORM_TARGETS.keys()), help="Target platform")
    parser.add_argument("--apply", action="store_true", help="Actually copy files (default: dry-run)")
    parser.add_argument("--include-private", action="store_true", help="Also mirror private-tier skills")
    parser.add_argument("--check", action="store_true", help="Verify registry validity without writing")
    parser.add_argument("--rebuild-registry", action="store_true", help="Run build-registry.py before sync")
    args = parser.parse_args()

    if args.rebuild_registry:
        import subprocess
        rc = subprocess.call([sys.executable, str(ROOT / ".claude" / "scripts" / "build-registry.py"), "--quiet"])
        if rc != 0:
            return rc

    registry = load_registry()

    if args.check:
        print(f"Registry version: {registry['version']}")
        print(f"Generated: {registry['generated_at']}")
        print(f"Skills: {registry['stats']['skills_total']}")
        print(f"By audience: {registry['stats']['skills_by_audience']}")
        return 0

    if not args.platform:
        print("FAIL: --platform required (or use --check)", file=sys.stderr)
        return 1

    target = PLATFORM_TARGETS[args.platform]
    skills = filter_skills(registry["skills"], args.include_private)

    print(f"Target: {target.relative_to(ROOT)}/skills/")
    print(f"Skills to sync: {len(skills)} ({'apply' if args.apply else 'DRY-RUN'})")
    if not args.include_private:
        excluded = registry["stats"]["skills_total"] - len(skills)
        if excluded:
            print(f"Excluded (private): {excluded} — use --include-private to include")
    print()

    for s in skills:
        print(sync_skill(s, target, args.apply))

    if args.apply:
        print(f"\nSynced {len(skills)} skills to {target.relative_to(ROOT)}/skills/")
        print("Note: SKILL.md format assumed portable. Per-platform tuning may be needed.")
    else:
        print("\nDry-run complete. Re-run with --apply to write files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
