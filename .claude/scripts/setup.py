#!/usr/bin/env -S uv run --script --quiet
# AUDIENCE: public
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""DMRZL workspace setup — fills template placeholders with your values.

Workflow:
  setup.py init       Interactive prompts → writes setup.config.env
  setup.py dry-run    Preview substitutions without writing
  setup.py apply      Replace {{placeholders}} with your values
  setup.py reset      Replace your values back with {{placeholders}} (before re-publish)

Placeholders in shipped files use {{snake_case_lower}} format.
Config keys in setup.config.env use UPPER_SNAKE_CASE matching the placeholder.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Run from the repo root (script lives in .claude/scripts/, repo root is two up).
WORKSPACE = Path(__file__).resolve().parents[2]
CONFIG_FILE = WORKSPACE / "setup.config.env"
EXAMPLE_FILE = WORKSPACE / ".claude" / "scripts" / "setup.config.example.env"

# Extensions we substitute into
_WALK_EXTS = frozenset([".md", ".sh", ".py", ".json", ".yaml", ".yml", ".toml"])

# Paths to skip during walk
_SKIP_PREFIXES = (
    ".git",
    "_build",
    "node_modules",
    ".smart-env",
)

_SKIP_NAMES = frozenset([
    "setup.config.env",
    "setup.config.example.env",
    "setup.py",
    "setup.sh",
    "apply-config.py",
    "apply-config.sh",
])


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _placeholder_for(key: str) -> str:
    """USER_HANDLE → {{user_handle}}"""
    return "{{" + key.lower() + "}}"


def _load_config() -> dict[str, str]:
    """Parse CONFIG_FILE into {KEY: value} dict."""
    if not CONFIG_FILE.is_file():
        _die(f"missing {CONFIG_FILE} — run 'setup.py init' first")
    config: dict[str, str] = {}
    for line in CONFIG_FILE.read_text(encoding="utf-8").splitlines():
        m = re.match(r'^([A-Z_]+)="?(.*?)"?$', line.strip())
        if m:
            config[m.group(1)] = m.group(2)
    return config


def _walk_files() -> list[Path]:
    """Yield files we sanitize: code, docs, configs. Skip binaries and tooling."""
    results: list[Path] = []
    for root, dirs, files in os.walk(WORKSPACE):
        root_path = Path(root)
        rel_root = root_path.relative_to(WORKSPACE)

        # Prune skipped directory prefixes
        dirs[:] = [
            d for d in dirs
            if not any(str(rel_root / d).startswith(p) for p in _SKIP_PREFIXES)
            and not (rel_root == Path(".") and d.startswith(".") and d not in (".claude", ".gemini"))
        ]

        for fname in files:
            fp = root_path / fname
            if fp.suffix not in _WALK_EXTS:
                continue
            if fp.name in _SKIP_NAMES:
                continue
            rel = fp.relative_to(WORKSPACE)
            # Skip paths containing setup.config.* anywhere
            if "setup.config" in str(rel):
                continue
            results.append(fp)
    return results


def _smart_default(key: str, fallback: str) -> str:
    """Infer sensible defaults from the current environment."""
    match key:
        case "USER_HANDLE":
            return os.environ.get("USER", "") or (
                __import__("subprocess").run(
                    ["whoami"], capture_output=True, text=True
                ).stdout.strip()
            ) or fallback
        case "HOME":
            return str(Path.home())
        case "WORKSPACE_ROOT":
            return str(WORKSPACE)
        case "WORKSPACE_DIR":
            return WORKSPACE.name
        case _:
            return fallback


def cmd_init() -> int:
    if not EXAMPLE_FILE.is_file():
        _die(f"missing example: {EXAMPLE_FILE}")

    if CONFIG_FILE.is_file():
        print(f"Config exists at {CONFIG_FILE}.")
        # Read from /dev/tty so we don't conflict with stdin piping
        try:
            with open("/dev/tty") as tty:
                ans = tty.readline().strip()
        except OSError:
            ans = input("Overwrite? [y/N] ").strip()
        if ans.lower() not in ("y", "yes"):
            sys.exit(0)

    print(
        "Interactive setup. Defaults are derived from your environment\n"
        "(USER_HANDLE from `whoami`, paths from $HOME and $PWD).\n"
        "Press Enter to accept; type a value to override.\n"
    )

    tmp_file = CONFIG_FILE.with_suffix(".env.tmp")
    lines_out: list[str] = []
    description = ""
    section = ""

    example_text = EXAMPLE_FILE.read_text(encoding="utf-8")
    for line in example_text.splitlines():
        m = re.match(r'^([A-Z_]+)="?(.*?)"?$', line)
        if m:
            key = m.group(1)
            example_val = m.group(2)
            default = _smart_default(key, example_val)

            if section:
                print(f"\n  ── {section} ──\n")
                section = ""
            if description:
                print(description, end="")

            prompt = f"  {key} [{default}]: "
            try:
                with open("/dev/tty") as tty:
                    sys.stdout.write(prompt)
                    sys.stdout.flush()
                    value = tty.readline().rstrip("\n")
            except OSError:
                value = input(prompt)
            value = value if value.strip() else default
            lines_out.append(f'{key}="{value}"')
            description = ""
        elif not line.strip():
            description = ""
            lines_out.append(line)
        elif "──" in line:
            # Section divider — extract title
            section = re.sub(r"^#\s*", "", line)
            section = re.sub(r"─+", "", section).strip()
            description = ""
            lines_out.append(line)
        elif m2 := re.match(r"^#\s(.+)$", line):
            inner = m2.group(1)
            description += f"    {inner}\n"
            lines_out.append(line)
        else:
            lines_out.append(line)

    tmp_file.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    tmp_file.replace(CONFIG_FILE)
    print()
    print(f"Wrote {CONFIG_FILE}. Review it, then run: setup.py dry-run")
    return 0


def cmd_substitute(mode: str) -> int:
    config = _load_config()
    total = 0
    files_changed = 0

    for fp in _walk_files():
        file_changed = False
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        for key, value in config.items():
            ph = _placeholder_for(key)

            if mode == "dry-run":
                count = text.count(ph)
                if count:
                    print(f"  {fp.relative_to(WORKSPACE)}: {ph} -> {value}  (count: {count})")
                    total += count
                    file_changed = True

            elif mode == "apply":
                if ph in text:
                    text = text.replace(ph, value)
                    file_changed = True

            elif mode == "reset":
                if value and value in text:
                    text = text.replace(value, ph)
                    file_changed = True

        if mode in ("apply", "reset") and file_changed:
            fp.write_text(text, encoding="utf-8")

        if file_changed:
            files_changed += 1

    if mode == "dry-run":
        print()
        print(f"Would replace {total} placeholders across {files_changed} files.")
    elif mode == "apply":
        if files_changed == 0:
            print("Applied substitutions to 0 files.")
            print()
            print("⚠ No {{placeholders}} found. Possible causes:")
            print("   • This workspace was already applied with previous values.")
            print("     Run 'setup.py reset' first, then re-apply with the current config.")
            print("   • You're not in the workspace root (run setup.py from the clone root).")
            print("   • A 'git checkout -- .' to restore placeholders, then apply, also works.")
        else:
            print(f"Applied substitutions to {files_changed} files.")
    elif mode == "reset":
        print(f"Reset {files_changed} files back to placeholders.")

    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "init":
        return cmd_init()
    elif cmd == "dry-run":
        return cmd_substitute("dry-run")
    elif cmd == "apply":
        return cmd_substitute("apply")
    elif cmd == "reset":
        return cmd_substitute("reset")
    else:
        print(
            f"Usage: {os.path.basename(sys.argv[0])} {{init|dry-run|apply|reset}}\n\n"
            "  init      Interactive prompts to fill setup.config.env.\n"
            "  dry-run   Preview substitutions without writing.\n"
            "  apply     Replace {{placeholders}} with your values.\n"
            "  reset     Replace your values back with {{placeholders}} (before re-publish).",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
