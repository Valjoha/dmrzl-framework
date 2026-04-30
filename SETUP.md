# Setup — DMRZL Framework

Set up an agent workspace from this demo repo on your own project.

## Prerequisites

- **[Claude Code](https://claude.com/claude-code)** — the runtime. Install: `npm install -g @anthropic-ai/claude-code` (or the platform-native installer).
- **[Obsidian](https://obsidian.md)** — for browsing the vault as a knowledge graph. Optional but strongly recommended.
- **A target project directory** — any code project you want the agent to work on. The framework is project-agnostic (the demo originated on a Unity ECS game, but works just as well for web apps, Python, infra, etc.).

## 1. Clone

```sh
git clone https://github.com/Valjoha/dmrzl-framework.git my-agent-workspace
cd my-agent-workspace
```

`my-agent-workspace` is your name — pick anything.

## 2. Configure your values

The framework ships with `{{placeholder}}` tokens for user-specific values (your name, project name, paths). Fill them in:

```sh
./.claude/scripts/setup.sh init
```

Interactive prompts will ask for 10 values:

| Key | Example | What it is |
|-----|---------|------------|
| `USER_HANDLE` | `"alice"` | Your local OS username (output of `whoami`). Appears in `~/.claude/projects/-Users-<handle>-...` memory paths. Not your GitHub handle. |
| `LANGUAGE` | `"en"` (default) | Response language. Suggested: `en`, `ukr`, `es`, ... — any language code or name works. Substituted into `PERSONA.md` so the agent replies in this language. |
| `GITHUB_OWNER` | `"your-handle"` | GitHub user/org that owns the project repo. Used in CI commands (`gh run list --repo <owner>/<project>`). Leave default if you don't push to GitHub. |
| `PROJECT_NAME` | `"MyGame"` | Display name of your target project. Used in agent rules, CI commands, docs. |
| `PROJECT_SLUG` | `"mygame"` | Lowercase URL-safe form. Used as `vault/<slug>/` folder name. |
| `SRC_DIR` | `"src"` or `"Sources"` | Source folder name inside your target project. |
| `HOME` | `"/Users/alice"` | Your home directory. |
| `WORKSPACE_ROOT` | `"/Users/alice/Projects/my-agent-workspace"` | Absolute path to this clone. |
| `WORKSPACE_DIR` | `"my-agent-workspace"` | Folder name only — last segment of WORKSPACE_ROOT. |
| `PROJECT_ROOT` | `"/Users/alice/Projects/MyGame"` | Absolute path to your target project. |

This writes `setup.config.env` (gitignored). Review and edit if needed.

Preview substitutions before applying:

```sh
./.claude/scripts/setup.sh dry-run
```

Apply:

```sh
./.claude/scripts/setup.sh apply
```

If you ever need to reverse (e.g. before contributing back upstream):

```sh
./.claude/scripts/setup.sh reset
```

## 3. Open the vault in Obsidian

1. Launch Obsidian.
2. **Open folder as vault** → select the `vault/` directory inside your clone.
3. Accept default config.

You should see four top-level folders: `dmrzl/`, `<your-project-slug>/`, `personal/`, `archive/`.

## 4. Configure Obsidian MCP (important — read this carefully)

The framework's `dmrzl-start` skill and most workflows call `mcp__obsidian__read-note` to load context from `vault/`. You need an Obsidian MCP server pointing at **this clone's vault**, not some other one.

**One-vault user (most people):**

```sh
# 1. Open Obsidian, "Open folder as vault" → select the vault/ subfolder of this clone.
# 2. Install the MCP server (project-scoped, lives in this repo's .mcp.json):
claude mcp add obsidian -s project -- npx -y mcp-obsidian
```

Project scope means the MCP server only activates when Claude Code runs from this directory — no contamination of your other Claude Code projects.

**Multi-vault user (if you already have Obsidian vaults open elsewhere):**

The MCP server resolves vaults by name. If you already have a vault named `"vault"` open in Obsidian, it will use that one — even when running Claude Code from this clone. Two options:

- **Rename this vault**: in Obsidian, right-click the vault → "Manage vault" → rename to e.g. `"my-agent-vault"`. Then update the MCP call: `claude mcp add obsidian -s project -- npx -y mcp-obsidian --vault my-agent-vault`.
- **Or run Obsidian with only this vault open** when you're working in this clone.

If the MCP returns content that looks unrelated (mentions a project you're not working on), that's the cross-vault contamination signal — fix the config.

**(Optional) IDE integration:**

```sh
# JetBrains IDEs
claude mcp add rider -s project -- npx -y @rider/mcp-server
```

Other MCP servers are optional — install per their docs as needed.

## 5. Open in Claude Code and start a session

```sh
cd my-agent-workspace
claude
```

When the session starts, the **`dmrzl-start` skill** auto-loads:

- `vault/dmrzl/session/HANDOFF.md` (your session state — empty on first run)
- `vault/dmrzl/identity/CORE.md` (the discipline rules)
- `vault/dmrzl/tooling/CLAUDE_CODE.md` (Claude Code specifics)

The agent reports its current state and asks what to work on.

## 6. First session — try the workflow

| What you say | What happens |
|--------------|--------------|
| `/dmrzl-spec add user authentication` | Enters design dialogue mode. ~20 clarifying questions before any code. Hard gate: no implementation until you approve the design. |
| `Delegate research on JWT vs session cookies to the researcher agent` | Agent spawns the `researcher` subagent with a structured brief. |
| `/dmrzl-write-a-skill` | Walks you through authoring a new domain skill following framework conventions (≤100 lines, LANGUAGE.md companion if needed, trigger predicate). |
| `/dmrzl-handoff` | End-of-session distillation. Writes decisions/patterns/HANDOFF.md so the next session resumes cleanly. |

## 7. Customize PERSONA + USER

Two files that personalize the agent:

- **`vault/dmrzl/identity/PERSONA.md`** — the agent's voice, language, identity boundaries. The public version ships a generic English-default professional persona. Edit it freely — change the language, add domain-specific guidance, or rewrite the voice rules entirely.
- **`vault/personal/USER.md`** — your role, expertise, preferences. The agent loads this on demand for context-sensitive responses (career questions, off-domain redirects).

To switch language after initial setup: edit `LANGUAGE` in `setup.config.env`, run `./setup.sh reset` then `./setup.sh apply`. The persona's `language: <value>` line will be re-substituted.

The friends-tier distribution ships a richer persona (literary coloring, voice phrasebook, ~160 sessions of accumulated discipline notes). The public version intentionally keeps things generic — yours to evolve.

## 8. Add your own skills

```sh
mkdir .claude/skills/dmrzl-mything
cat > .claude/skills/dmrzl-mything/SKILL.md <<'EOF'
---
description: "Use when X. Do NOT use for Y. Trigger on: keywords here."
audience: public
---
# My Thing
Body ≤100 lines. Workflow steps. Where to look.
EOF
```

The `dmrzl-write-a-skill` skill walks you through this with all the conventions.

## Troubleshooting

- **Skill doesn't trigger** — check the `description` field. It's the trigger predicate. Make it specific: "Use when X. Do NOT use for Y." Keywords in the description get matched.
- **Hooks not firing** — `.claude/settings.json` may not be configured. The demo ships safety hooks but doesn't auto-enable them. See `.claude/settings.example.json` for the wire-up.
- **Vault tree empty in Obsidian** — make sure you opened the `vault/` subfolder, not the workspace root.
- **`{{placeholder}}` text still in files** — `setup.sh apply` didn't run, or `setup.config.env` is missing keys. Run `setup.sh dry-run` to see what's left.

## Next

- **Like it?** Star the repo. Open issues with feedback.
- **Want the full system** (self-improvement layer, autonomous research loops, monitoring, multi-platform Codex integration)? See the README — friends-tier distribution is invitation-only.
- **Want to extend?** Read `vault/dmrzl/skills/` for skill examples, `vault/dmrzl/protocols/` for delegation/agent rules, `vault/dmrzl/identity/CORE.md` for the discipline rules.
