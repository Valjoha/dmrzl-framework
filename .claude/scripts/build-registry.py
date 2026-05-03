#!/usr/bin/env python3
# AUDIENCE: public
"""Build a unified registry.json from .claude/skills/, .claude/commands/, .claude/agents/.

The registry is the single source of truth for skill/command/agent metadata.
Multi-platform sync scripts (sync-tiers.py, sync-platforms.py) read this
to derive .gemini/, .codex/, .openclaw/ equivalents.

Usage:
    python3 .claude/scripts/build-registry.py                # write .claude/registry.json
    python3 .claude/scripts/build-registry.py --check        # verify without writing
    python3 .claude/scripts/build-registry.py --output PATH  # custom output path

Frontmatter schema expected per skill (see vault/dmrzl/research/2026-05-01-hermes-agent-analysis.md):
    name: str               # canonical skill id (defaults to folder name)
    description: str        # primary trigger text
    audience: public|friends|private
    category: session|workflow|domain|tools|maintenance|engagement|design
    platforms: [unity, general, ...]
    cache_safe: bool        # false = mutates context (start, handoff)
    tags: [str]
    related_skills: [str]
    requires_tools: [str]   # obsidian-mcp-rs, unity-mcp, rider-mcp, etc.
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / ".claude" / "skills"
COMMANDS_DIR = ROOT / ".claude" / "commands"
AGENTS_DIR = ROOT / ".claude" / "agents"
DEFAULT_OUTPUT = ROOT / ".claude" / "registry.json"

ARCHIVE_DIR_NAMES = {"archive", "_archive", ".archive"}


def parse_frontmatter(text: str) -> dict | None:
    """Parse YAML frontmatter into a dict using minimal native parsing.

    Avoids PyYAML dependency. Handles:
      - simple `key: value` pairs
      - inline lists `[a, b, c]`
      - block scalar `>` (folds following indented lines into value)
      - quoted strings
    Skips dashes, comments, and empty lines.
    """
    if not text.startswith("---"):
        return None
    lines = text.split("\n")
    if lines[0].strip() != "---":
        return None
    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return None

    out: dict = {}
    i = 1
    while i < end:
        raw = lines[i]
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        m = re.match(r"^(\w[\w-]*)\s*:\s*(.*)$", line)
        if not m:
            i += 1
            continue
        key, value = m.group(1), m.group(2).strip()
        # Block scalar `>` → fold following indented lines
        if value == ">":
            collected = []
            j = i + 1
            while j < end and (lines[j].startswith("  ") or lines[j].strip() == ""):
                if lines[j].strip():
                    collected.append(lines[j].strip())
                j += 1
            out[key] = " ".join(collected)
            i = j
            continue
        # Inline list `[a, b, c]`
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if not inner:
                out[key] = []
            else:
                out[key] = [v.strip().strip('"').strip("'") for v in inner.split(",")]
            i += 1
            continue
        # Block list (next line starts with `  -`)
        if value == "":
            collected = []
            j = i + 1
            while j < end and re.match(r"^\s+-\s+", lines[j]):
                item = re.sub(r"^\s+-\s+", "", lines[j]).strip().strip('"').strip("'")
                collected.append(item)
                j += 1
            if collected:
                out[key] = collected
                i = j
                continue
            out[key] = ""
            i += 1
            continue
        # Boolean
        if value.lower() in ("true", "false"):
            out[key] = value.lower() == "true"
            i += 1
            continue
        # Strip quotes
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        out[key] = value
        i += 1
    return out


def collect_skills() -> list[dict]:
    skills = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir() or skill_dir.name in ARCHIVE_DIR_NAMES:
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        if fm is None:
            continue
        entry = {
            "id": fm.get("name") or skill_dir.name,
            "folder": skill_dir.name,
            "path": str(skill_md.relative_to(ROOT)),
            "description": fm.get("description", ""),
            "audience": fm.get("audience", "private"),
            "category": fm.get("category", "uncategorized"),
            "platforms": fm.get("platforms", []),
            "cache_safe": fm.get("cache_safe", True),
            "tags": fm.get("tags", []),
            "related_skills": fm.get("related_skills", []),
            "requires_tools": fm.get("requires_tools", []),
        }
        skills.append(entry)
    return skills


def collect_commands() -> list[dict]:
    if not COMMANDS_DIR.exists():
        return []
    commands = []
    for cmd_path in sorted(COMMANDS_DIR.glob("*.md")):
        fm = parse_frontmatter(cmd_path.read_text(encoding="utf-8")) or {}
        commands.append({
            "id": cmd_path.stem,
            "path": str(cmd_path.relative_to(ROOT)),
            "description": fm.get("description", ""),
            "audience": fm.get("audience", "public"),
            "category": fm.get("category", "uncategorized"),
        })
    return commands


def collect_agents() -> list[dict]:
    if not AGENTS_DIR.exists():
        return []
    agents = []
    for agent_path in sorted(AGENTS_DIR.glob("*.md")):
        fm = parse_frontmatter(agent_path.read_text(encoding="utf-8")) or {}
        agents.append({
            "id": agent_path.stem,
            "path": str(agent_path.relative_to(ROOT)),
            "description": fm.get("description", ""),
            "model": fm.get("model", ""),
            "tools": fm.get("tools", []),
            "audience": fm.get("audience", "private"),
        })
    return agents


def build_registry() -> dict:
    skills = collect_skills()
    commands = collect_commands()
    agents = collect_agents()
    return {
        "version": 1,
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "skills": skills,
        "commands": commands,
        "agents": agents,
        "stats": {
            "skills_total": len(skills),
            "skills_by_category": dict(Counter(s["category"] for s in skills)),
            "skills_by_audience": dict(Counter(s["audience"] for s in skills)),
            "skills_by_platform": dict(Counter(p for s in skills for p in (s["platforms"] or ["general"]))),
            "skills_cache_unsafe": [s["id"] for s in skills if not s["cache_safe"]],
            "commands_total": len(commands),
            "agents_total": len(agents),
        },
    }


def validate(registry: dict) -> list[str]:
    """Return a list of validation warnings/errors."""
    issues = []
    valid_categories = {"session", "workflow", "domain", "tools", "maintenance", "engagement", "design", "uncategorized"}
    valid_audiences = {"public", "friends", "private"}
    valid_platforms = {"general", "unity", "linux", "macos", "windows"}
    skill_ids = {s["id"] for s in registry["skills"]}

    for s in registry["skills"]:
        if s["category"] not in valid_categories:
            issues.append(f"WARN  {s['id']}: unknown category '{s['category']}'")
        if s["audience"] not in valid_audiences:
            issues.append(f"WARN  {s['id']}: unknown audience '{s['audience']}'")
        for p in s["platforms"]:
            if p not in valid_platforms:
                issues.append(f"WARN  {s['id']}: unknown platform '{p}'")
        for rel in s["related_skills"]:
            if rel not in skill_ids:
                issues.append(f"WARN  {s['id']}: related_skills refers to unknown '{rel}'")
        if not s["description"]:
            issues.append(f"ERROR {s['id']}: missing description")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate without writing")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output path (default: .claude/registry.json)")
    parser.add_argument("--quiet", action="store_true", help="Suppress stats output")
    args = parser.parse_args()

    registry = build_registry()
    issues = validate(registry)

    for issue in issues:
        print(issue, file=sys.stderr)
    errors = [i for i in issues if i.startswith("ERROR")]
    if errors:
        print(f"\nFAILED: {len(errors)} errors", file=sys.stderr)
        return 1

    if args.check:
        print(f"OK: {registry['stats']['skills_total']} skills, "
              f"{registry['stats']['commands_total']} commands, "
              f"{registry['stats']['agents_total']} agents")
        return 0

    args.output.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n")

    if not args.quiet:
        print(f"Wrote {args.output.relative_to(ROOT)}")
        print(f"  Skills: {registry['stats']['skills_total']} "
              f"({', '.join(f'{k}={v}' for k, v in registry['stats']['skills_by_category'].items())})")
        print(f"  Audiences: {registry['stats']['skills_by_audience']}")
        print(f"  Cache-unsafe: {registry['stats']['skills_cache_unsafe']}")
        print(f"  Commands: {registry['stats']['commands_total']}")
        print(f"  Agents: {registry['stats']['agents_total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
