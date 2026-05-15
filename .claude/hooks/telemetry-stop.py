#!/usr/bin/env python3
# AUDIENCE: public
"""telemetry-stop.py — Stop hook that aggregates today's session JSONL and appends
a ## Token Economy block to the current session's handoff S{N}.md.

Reads Claude Code conversation JSONL (not OTel spans — those appear after
CLAUDE_CODE_ENABLE_TELEMETRY=1 takes effect in a NEW session).
Falls back gracefully if no telemetry data found.

Exit 0 always — telemetry is advisory, never blocks the Stop hook.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# --- Paths ---
HOOKS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HOOKS_DIR))
from _paths import workspace_root
from _service_mode import is_service_session

WORKSPACE = workspace_root()
VAULT_ROOT = WORKSPACE / "vault"
FEEDBACK_DIR = WORKSPACE / ".claude" / "feedback-loops"
SESSION_FILE = FEEDBACK_DIR / ".current-session"
LAST_BASELINE_FILE = FEEDBACK_DIR / "last-baseline.json"
MEASURE_SCRIPT = WORKSPACE / "scripts" / "measure-token-baseline.py"

PROJECT_KEY = "-Users-{{user_handle}}-Projects-{{workspace_dir}}"
PROJECTS_DIR = Path.home() / ".claude" / "projects" / PROJECT_KEY
HOOK_EVENTS_FILE = FEEDBACK_DIR / "hook-events.jsonl"

# Codex CLI session storage. Layout: ~/.codex/sessions/YYYY/MM/DD/rollout-*-<uuid>.jsonl
CODEX_SESSIONS_DIR = Path.home() / ".codex" / "sessions"
CODEX_WORKSPACE = "{{workspace_root}}"


# --- Helpers ---

def read_session_number() -> str:
    """Read current session number from .current-session."""
    if SESSION_FILE.exists():
        return SESSION_FILE.read_text(encoding="utf-8").strip()
    return "?"


def resolve_handoff_path(session_num: str) -> Path | None:
    """Resolve path to current session's handoff file."""
    if session_num == "?":
        return None
    path = VAULT_ROOT / "dmrzl" / "session" / "handoffs" / f"S{session_num}.md"
    return path if path.exists() else None


def today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def find_today_jsonl() -> list[Path]:
    """Find JSONL session files modified today (UTC)."""
    if not PROJECTS_DIR.exists():
        return []
    today = today_utc()
    result = []
    for f in PROJECTS_DIR.glob("*.jsonl"):
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
            if mtime.strftime("%Y-%m-%d") == today:
                result.append(f)
        except OSError:
            continue
    return result


def parse_jsonl_files(paths: list[Path]) -> dict:
    """
    Parse conversation JSONL files and aggregate token stats.

    Returns a dict with:
      totals: {input_tokens, output_tokens, cache_read_tokens, cache_creation_tokens}
      per_model: {model: {in, out, cache_r, cache_c}}
      skill_counts: {skill_name: invocation_count}
      agent_counts: {subagent_type: dispatch_count}
      tool_counts: {tool_name: count}
    """
    totals: dict[str, int] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_creation_tokens": 0,
    }
    per_model: dict[str, dict] = defaultdict(lambda: {"in": 0, "out": 0, "cache_r": 0, "cache_c": 0})
    skill_counts: dict[str, int] = defaultdict(int)
    agent_counts: dict[str, int] = defaultdict(int)
    tool_counts: dict[str, int] = defaultdict(int)

    for path in paths:
        try:
            _parse_single(path, totals, per_model, skill_counts, agent_counts, tool_counts)
        except Exception as e:
            print(f"[telemetry-stop] Warning: failed to parse {path.name}: {e}", file=sys.stderr)

    return {
        "totals": totals,
        "per_model": dict(per_model),
        "skill_counts": dict(skill_counts),
        "agent_counts": dict(agent_counts),
        "tool_counts": dict(tool_counts),
    }


def _parse_single(
    path: Path,
    totals: dict,
    per_model: dict,
    skill_counts: dict,
    agent_counts: dict,
    tool_counts: dict,
) -> None:
    """Parse one JSONL file, accumulating into shared dicts."""
    with open(path, encoding="utf-8", errors="replace") as f:
        for raw_line in f:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                obj = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            msg_type = obj.get("type")

            # --- Token counts from assistant messages ---
            if msg_type == "assistant":
                msg = obj.get("message", {})
                if not isinstance(msg, dict):
                    continue
                usage = msg.get("usage", {})
                if not isinstance(usage, dict):
                    continue
                model = msg.get("model", "unknown")

                inp = int(usage.get("input_tokens") or 0)
                out = int(usage.get("output_tokens") or 0)
                cache_r = int(usage.get("cache_read_input_tokens") or 0)
                cache_c = int(usage.get("cache_creation_input_tokens") or 0)

                totals["input_tokens"] += inp
                totals["output_tokens"] += out
                totals["cache_read_tokens"] += cache_r
                totals["cache_creation_tokens"] += cache_c

                m = per_model[model]
                m["in"] += inp
                m["out"] += out
                m["cache_r"] += cache_r
                m["cache_c"] += cache_c

                # --- Skill/Agent/Task tool use tracking ---
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if not isinstance(block, dict):
                            continue
                        if block.get("type") != "tool_use":
                            continue
                        tool_name = block.get("name", "")
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
                        inp_data = block.get("input", {})
                        if not isinstance(inp_data, dict):
                            continue
                        if tool_name == "Skill":
                            skill = inp_data.get("skill", "unknown")
                            skill_counts[skill] = skill_counts.get(skill, 0) + 1
                        elif tool_name in ("Agent", "Task"):
                            agent_type = inp_data.get("subagent_type", "")
                            if not agent_type:
                                # Fall back to first word of description
                                desc = inp_data.get("description", "agent")
                                agent_type = desc.split()[0][:20] if desc.split() else "agent"
                            agent_counts[agent_type] = agent_counts.get(agent_type, 0) + 1


def run_baseline() -> dict | None:
    """Run measure-token-baseline.py, return parsed JSON or None."""
    if not MEASURE_SCRIPT.exists():
        return None
    try:
        result = subprocess.run(
            [sys.executable, str(MEASURE_SCRIPT)],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
    except Exception as e:
        print(f"[telemetry-stop] Baseline script failed: {e}", file=sys.stderr)
    return None


def load_last_baseline() -> dict | None:
    if LAST_BASELINE_FILE.exists():
        try:
            return json.loads(LAST_BASELINE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def save_current_baseline(data: dict) -> None:
    try:
        FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
        LAST_BASELINE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[telemetry-stop] Could not save baseline: {e}", file=sys.stderr)


def build_token_economy_block(
    session_num: str,
    stats: dict,
    current_baseline: dict | None,
    previous_baseline: dict | None,
) -> str:
    """Build the ## Token Economy markdown block."""
    totals = stats["totals"]
    per_model = stats["per_model"]
    skill_counts = stats["skill_counts"]
    agent_counts = stats["agent_counts"]

    inp = totals["input_tokens"]
    out = totals["output_tokens"]
    cache_r = totals["cache_read_tokens"]
    cache_c = totals["cache_creation_tokens"]
    total_all = inp + out + cache_r + cache_c

    # Per-model breakdown — sort by total tokens descending
    model_totals: list[tuple[str, int]] = []
    for model, m in per_model.items():
        mt = m["in"] + m["out"] + m["cache_r"] + m["cache_c"]
        model_totals.append((model, mt))
    model_totals.sort(key=lambda x: x[1], reverse=True)
    model_lines = []
    for model, mt in model_totals[:3]:
        pct = round(100 * mt / total_all, 1) if total_all else 0
        model_lines.append(f"  - {model}: {mt:,} tokens ({pct}%)")

    # Top skills
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    skills_str = ", ".join(f"{s} ({n}×)" for s, n in top_skills) if top_skills else "none"

    # Top agents/subagents
    top_agents = sorted(agent_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    agents_str = ", ".join(f"{a} ({n}×)" for a, n in top_agents) if top_agents else "none"
    n_dispatches = sum(agent_counts.values())

    # Subagent total: tokens from non-opus models (rough attribution)
    subagent_total = sum(
        m["in"] + m["out"]
        for model, m in per_model.items()
        if "sonnet" in model.lower() or "haiku" in model.lower()
    )

    # Cache hit rate
    total_input = inp + cache_r + cache_c
    cache_hit_pct = round(100 * cache_r / total_input, 1) if total_input else 0

    # Baseline drift
    if current_baseline and previous_baseline:
        curr_tok = current_baseline.get("startup_tokens_total", 0)
        prev_tok = previous_baseline.get("startup_tokens_total", 0)
        delta = curr_tok - prev_tok
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        drift_alert = "YES (>200 tokens)" if abs(delta) > 200 else "NO"
        baseline_line = f"- Static baseline: {prev_tok:,} → {curr_tok:,} ({delta_str})"
        drift_line = f"- Drift alert: {drift_alert}"
    elif current_baseline:
        curr_tok = current_baseline.get("startup_tokens_total", 0)
        baseline_line = f"- Static baseline: — → {curr_tok:,} (first measurement)"
        drift_line = "- Drift alert: NO (no previous baseline)"
    else:
        baseline_line = "- Static baseline: unavailable (measure-token-baseline.py not found)"
        drift_line = "- Drift alert: NO"

    lines = [
        "",
        "## Token Economy",
        "",
        f"- Session: S{session_num}",
        f"- Orchestrator: {inp:,} in / {out:,} out / {cache_r:,} cached / {cache_c:,} cache_creation",
        f"- Subagents (total): ~{subagent_total:,} tokens across {n_dispatches} dispatches",
        "- Top model usage:",
    ]
    lines.extend(model_lines if model_lines else ["  - (no model data)"])
    lines.extend([
        f"- Top skills used: {skills_str}",
        f"- Top subagents: {agents_str}",
        f"- Cache hit rate (cached / total input): {cache_hit_pct}%",
        baseline_line,
        drift_line,
    ])

    # Hook events block (cross-platform — Codex/Gemini sessions populate this even when
    # the conversation JSONL above is empty, since hook telemetry is self-emitted).
    hook_events = read_hook_events(session_num)
    lines.extend(format_hook_events(hook_events))

    return "\n".join(lines) + "\n"


def _detect_platform_by_freshness(window_min: int = 10) -> str | None:
    """Auto-detect active platform by which transcript is youngest.

    Used when PLATFORM env var is missing — e.g., when a skill invokes
    telemetry-stop directly without preserving environment prefix.
    """
    cutoff = datetime.now(timezone.utc).timestamp() - window_min * 60
    candidates: list[tuple[float, str]] = []

    # Codex: ~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
    if CODEX_SESSIONS_DIR.exists():
        for p in CODEX_SESSIONS_DIR.rglob("rollout-*.jsonl"):
            try:
                mt = p.stat().st_mtime
                if mt >= cutoff:
                    candidates.append((mt, "codex"))
            except OSError:
                continue

    # Gemini: ~/.gemini/tmp/<workspace>/chats/session-*.jsonl
    gem_base = Path.home() / ".gemini" / "tmp"
    if gem_base.exists():
        for p in gem_base.glob("**/chats/session-*.jsonl"):
            if "claudeworkspace" not in str(p).lower():
                continue
            try:
                mt = p.stat().st_mtime
                if mt >= cutoff:
                    candidates.append((mt, "gemini-cli"))
            except OSError:
                continue

    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def parse_gemini_transcript(transcript_path: Path) -> dict | None:
    """Sum per-event token usage across a Gemini CLI session transcript JSONL.

    Gemini emits one record per LLM response with a `tokens` dict
    `{input, output, cached, thoughts, tool, total}`. These are PER-EVENT (not
    cumulative), so we sum across all `type=gemini` records.

    Returns: {input, output, cached, thoughts, total, model, session_id} or None.
    """
    if not transcript_path.is_file():
        return None
    totals = {"input": 0, "output": 0, "cached": 0, "thoughts": 0, "tool": 0, "total": 0}
    model = None
    sid = None
    try:
        with transcript_path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("kind") and rec.get("sessionId"):
                    sid = rec.get("sessionId")
                if rec.get("type") != "gemini":
                    continue
                tk = rec.get("tokens") or {}
                for k in totals:
                    totals[k] += int(tk.get(k, 0) or 0)
                if rec.get("model") and not model:
                    model = rec.get("model")
    except OSError:
        return None
    if totals["total"] == 0:
        return None
    return {**totals, "model": model or "gemini-unknown", "session_id": sid or "unknown",
            "transcript": str(transcript_path)}


def find_latest_gemini_transcript(workspace_hash_hint: str | None = None, max_age_min: int = 60) -> Path | None:
    """Find newest Gemini chats JSONL under ~/.gemini/tmp/<workspace>/chats/.
    workspace_hash_hint: substring to match in path (e.g. 'claudeworkspace').
    """
    base = Path.home() / ".gemini" / "tmp"
    if not base.exists():
        return None
    pattern = "**/chats/session-*.jsonl"
    candidates = sorted(base.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_min * 60
    for p in candidates[:10]:
        try:
            if p.stat().st_mtime < cutoff:
                continue
            if workspace_hash_hint and workspace_hash_hint.lower() not in str(p).lower():
                continue
            return p
        except OSError:
            continue
    return None


def build_gemini_token_block(session_num: str, stats: dict, current_baseline, previous_baseline) -> str:
    """Gemini-native Token Economy block."""
    inp, out, cached, thoughts, tot = stats["input"], stats["output"], stats["cached"], stats["thoughts"], stats["total"]
    cache_hit = round(100 * cached / inp, 1) if inp else 0

    if current_baseline and previous_baseline:
        curr_tok = current_baseline.get("startup_tokens_total", 0)
        prev_tok = previous_baseline.get("startup_tokens_total", 0)
        delta = curr_tok - prev_tok
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        drift_alert = "YES (>200 tokens)" if abs(delta) > 200 else "NO"
        baseline_line = f"- Static baseline: {prev_tok:,} → {curr_tok:,} ({delta_str})"
        drift_line = f"- Drift alert: {drift_alert}"
    else:
        baseline_line = "- Static baseline: unavailable"
        drift_line = "- Drift alert: NO"

    lines = [
        "",
        "## Token Economy",
        "",
        f"- Session: S{session_num} (gemini-cli)",
        f"- Gemini session id: `{stats['session_id']}`",
        f"- Model: {stats['model']}",
        f"- Total: {tot:,} tokens (input {inp:,} / output {out:,} / thoughts {thoughts:,})",
        f"- Cached input: {cached:,} ({cache_hit}% cache hit on input)",
        baseline_line,
        drift_line,
    ]
    hook_events = read_hook_events(session_num)
    lines.extend(format_hook_events(hook_events))
    return "\n".join(lines) + "\n"


def find_latest_codex_rollout(workspace: str = CODEX_WORKSPACE, max_age_min: int = 60) -> Path | None:
    """Return the most recently modified Codex rollout JSONL whose session_meta.cwd matches workspace.

    Walks ~/.codex/sessions/YYYY/MM/DD/rollout-*-<uuid>.jsonl, sorted newest first by mtime.
    Skips files older than max_age_min minutes (avoids picking up an unrelated stale session).
    Returns None if no matching rollout is found.
    """
    if not CODEX_SESSIONS_DIR.exists():
        return None
    candidates = sorted(
        CODEX_SESSIONS_DIR.rglob("rollout-*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_min * 60
    for path in candidates[:5]:  # cap scan to 5 newest
        try:
            if path.stat().st_mtime < cutoff:
                continue
            with path.open(encoding="utf-8") as f:
                first_line = f.readline().strip()
                if not first_line:
                    continue
                meta = json.loads(first_line)
                if meta.get("type") != "session_meta":
                    continue
                payload = meta.get("payload", {})
                if payload.get("cwd") == workspace:
                    return path
        except (OSError, json.JSONDecodeError):
            continue
    return None


def parse_codex_session(rollout_path: Path) -> dict | None:
    """Extract token totals + model + UUID from a Codex rollout JSONL.

    Returns: {input, cached, output, reasoning, total, model, uuid, last_token_usage} or None.
    Reads the LAST token_count event in the file — Codex emits cumulative totals per turn.
    """
    last_token_count = None
    meta = None
    try:
        with rollout_path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                t = rec.get("type")
                p = rec.get("payload", {}) or {}
                if t == "session_meta" and meta is None:
                    meta = p
                elif t == "event_msg" and p.get("type") == "token_count":
                    info = p.get("info")
                    if info and info.get("total_token_usage"):
                        last_token_count = info
    except OSError:
        return None
    if not last_token_count:
        return None
    totals = last_token_count.get("total_token_usage", {}) or {}
    return {
        "input": int(totals.get("input_tokens", 0)),
        "cached": int(totals.get("cached_input_tokens", 0)),
        "output": int(totals.get("output_tokens", 0)),
        "reasoning": int(totals.get("reasoning_output_tokens", 0)),
        "total": int(totals.get("total_tokens", 0)),
        "context_window": int(last_token_count.get("model_context_window", 0)),
        "model": (meta or {}).get("model_provider", "unknown"),
        "uuid": (meta or {}).get("id", "unknown"),
    }


def build_codex_token_block(session_num: str, codex_stats: dict, current_baseline, previous_baseline) -> str:
    """Codex-native Token Economy block. Smaller than Claude's — Codex doesn't expose
    per-skill / per-agent breakdowns in the rollout JSONL."""
    inp = codex_stats["input"]
    cached = codex_stats["cached"]
    out = codex_stats["output"]
    reasoning = codex_stats["reasoning"]
    total = codex_stats["total"]
    cache_hit = round(100 * cached / inp, 1) if inp else 0

    if current_baseline and previous_baseline:
        curr_tok = current_baseline.get("startup_tokens_total", 0)
        prev_tok = previous_baseline.get("startup_tokens_total", 0)
        delta = curr_tok - prev_tok
        delta_str = f"+{delta}" if delta >= 0 else str(delta)
        drift_alert = "YES (>200 tokens)" if abs(delta) > 200 else "NO"
        baseline_line = f"- Static baseline: {prev_tok:,} → {curr_tok:,} ({delta_str})"
        drift_line = f"- Drift alert: {drift_alert}"
    else:
        baseline_line = "- Static baseline: unavailable"
        drift_line = "- Drift alert: NO"

    lines = [
        "",
        "## Token Economy",
        "",
        f"- Session: S{session_num} (codex)",
        f"- Codex UUID: `{codex_stats['uuid']}`",
        f"- Codex provider: {codex_stats['model']}",
        f"- Total: {total:,} tokens (input {inp:,} / output {out:,} / reasoning {reasoning:,})",
        f"- Cached input: {cached:,} ({cache_hit}% cache hit on input)",
        f"- Context window: {codex_stats['context_window']:,}",
        baseline_line,
        drift_line,
    ]

    hook_events = read_hook_events(session_num)
    lines.extend(format_hook_events(hook_events))

    return "\n".join(lines) + "\n"


def read_hook_events(session_num: str) -> dict[str, dict[str, int]]:
    """Aggregate hook fires for the current session: {hook_name: {decision: count}}.

    Reads .claude/feedback-loops/hook-events.jsonl and filters by session_id.
    Codex/Gemini sessions store the session number directly in session_id;
    Claude Code stores a UUID, but our shared `.current-session` file pins the
    short S{N} number which `_hook_telemetry.py` resolves into session_id.
    """
    if not HOOK_EVENTS_FILE.exists():
        return {}
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    try:
        with HOOK_EVENTS_FILE.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if str(rec.get("session_id", "")) != str(session_num):
                    continue
                hook = rec.get("hook") or "unknown"
                decision = rec.get("decision") or "noop"
                counts[hook][decision] += 1
    except OSError:
        return {}
    return {h: dict(d) for h, d in counts.items()}


def format_hook_events(events: dict[str, dict[str, int]]) -> list[str]:
    """Return markdown lines for a Hook Events sub-block. Empty list if no events."""
    if not events:
        return []
    lines = ["- Hook fires:"]
    items = sorted(events.items(), key=lambda kv: -sum(kv[1].values()))
    for hook, decisions in items[:8]:
        parts = [f"{dec}={n}" for dec, n in sorted(decisions.items())]
        total = sum(decisions.values())
        lines.append(f"  - `{hook}`: {total} ({', '.join(parts)})")
    return lines


def no_data_block(session_num: str) -> str:
    return (
        "\n## Token Economy\n"
        "_OTel telemetry not yet active for this session. "
        "`CLAUDE_CODE_ENABLE_TELEMETRY=1` is set — data will appear from next session onward._\n"
    )


def append_to_handoff(handoff_path: Path, block: str) -> None:
    """Append Token Economy block to handoff, replacing any prior block."""
    content = handoff_path.read_text(encoding="utf-8")
    if "## Token Economy" in content:
        idx = content.find("\n## Token Economy")
        if idx >= 0:
            content = content[:idx]
    content = content.rstrip("\n") + "\n" + block
    handoff_path.write_text(content, encoding="utf-8")


def patch_frontmatter_models(handoff_path: Path, model_name: str) -> None:
    """Replace YAML `models: [...]` frontmatter line with API-reported model.

    S205 finding: Gemini self-reports `gemini-2.0-flash` regardless of actual
    runtime model — LLMs can't reliably introspect their config. Source of truth
    is the transcript JSONL `model` field (per-event from API metadata).

    Idempotent — no-op if already correct. Only patches the FIRST `models:`
    line within the leading `---`-bounded frontmatter block.
    """
    if not model_name or model_name == "unknown":
        return
    try:
        content = handoff_path.read_text(encoding="utf-8")
    except OSError:
        return
    if not content.startswith("---\n"):
        return
    end = content.find("\n---\n", 4)
    if end < 0:
        return
    head = content[:end]
    rest = content[end:]
    new_line = f"models: [{model_name}]"
    new_head, n = re.subn(
        r"^models:\s*\[.*?\]\s*$",
        new_line,
        head,
        count=1,
        flags=re.MULTILINE,
    )
    if n == 0 or new_head == head:
        return
    handoff_path.write_text(new_head + rest, encoding="utf-8")


UUID_MAP_FILE = FEEDBACK_DIR / ".session-uuid-map"


def lookup_session_by_uuid(uuid: str) -> str | None:
    """Resolve UUID → numeric session number from the mapping written at SessionStart.
    S207-tail fix: prefers UUID-mapped session over `.current-session` (which may
    have advanced before SessionEnd fires under concurrent sessions).
    """
    if not uuid or not UUID_MAP_FILE.exists():
        return None
    try:
        for line in UUID_MAP_FILE.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0] == uuid:
                return parts[1]
    except OSError:
        return None
    return None


def main() -> int:
    if is_service_session():
        return 0  # service mode: no telemetry rollup
    # Capture stdin payload for UUID resolution before any side-effects.
    payload: dict = {}
    try:
        raw = sys.stdin.read()
        if raw:
            payload = json.loads(raw)
    except (json.JSONDecodeError, Exception):
        payload = {}

    sid_uuid = payload.get("session_id") if isinstance(payload, dict) else None
    mapped = lookup_session_by_uuid(sid_uuid) if sid_uuid else None

    session_num = mapped or read_session_number()
    handoff_path = resolve_handoff_path(session_num)

    if handoff_path is None:
        print(
            f"[telemetry-stop] Handoff S{session_num}.md not found — skipping token economy block.",
            file=sys.stderr,
        )
        return 0

    # Run baseline (non-blocking; errors are logged)
    current_baseline = run_baseline()
    previous_baseline = load_last_baseline()
    if current_baseline:
        save_current_baseline(current_baseline)

    # Platform branch: Codex parses ~/.codex/sessions/, Gemini parses
    # ~/.gemini/tmp/<workspace>/chats/, Claude falls through to ~/.claude/projects/.
    # Auto-detect when PLATFORM env unset (S205 finding: dmrzl-handoff skill on
    # Gemini called telemetry-stop without env prefix, defaulted to claude-code,
    # wrote Claude transcript stats into a Gemini handoff).
    platform = os.environ.get("PLATFORM")
    if not platform:
        platform = _detect_platform_by_freshness()
    if not platform:
        platform = "claude-code"
    block = None
    if platform == "codex":
        rollout = find_latest_codex_rollout()
        if rollout is not None:
            codex_stats = parse_codex_session(rollout)
            if codex_stats:
                block = build_codex_token_block(
                    session_num, codex_stats, current_baseline, previous_baseline
                )
    elif platform == "gemini-cli":
        transcript = find_latest_gemini_transcript("claudeworkspace")
        if transcript is not None:
            gem_stats = parse_gemini_transcript(transcript)
            if gem_stats:
                # S208/S210 race fix: derive session number from the transcript's
                # own sessionId (UUID), not from `.current-session` which races
                # with parallel SessionStart calls. Transcript header is the
                # primary source of truth for "which session just ended".
                transcript_uuid = gem_stats.get("session_id")
                mapped_from_transcript = lookup_session_by_uuid(transcript_uuid) if transcript_uuid else None
                if mapped_from_transcript:
                    session_num = mapped_from_transcript
                    handoff_path = resolve_handoff_path(session_num)
                block = build_gemini_token_block(
                    session_num, gem_stats, current_baseline, previous_baseline
                )
                if handoff_path is not None:
                    patch_frontmatter_models(handoff_path, gem_stats.get("model", ""))

    if block is None:
        # Default path: Claude conversation JSONL
        jsonl_files = find_today_jsonl()
        if not jsonl_files:
            block = no_data_block(session_num)
        else:
            stats = parse_jsonl_files(jsonl_files)
            total_tokens = sum(stats["totals"].values())
            if total_tokens == 0:
                block = no_data_block(session_num)
            else:
                block = build_token_economy_block(
                    session_num, stats, current_baseline, previous_baseline
                )

    try:
        append_to_handoff(handoff_path, block)
        print(f"[telemetry-stop] Token Economy block written to S{session_num}.md", file=sys.stderr)
    except Exception as e:
        print(f"[telemetry-stop] Failed to write handoff: {e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
