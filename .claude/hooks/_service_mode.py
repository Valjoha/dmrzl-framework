#!/usr/bin/env python3
# AUDIENCE: public
"""Service-session mode helpers — single source of truth for hook gates.

Service mode = a session that writes no traces (no S{N}.md, no INDEX row,
no telemetry, no feedback-loop logs). Activated by `/dmrzl-service` skill
or by launching with `DMRZL_SERVICE=1 claude`.

Marker file: ~/.claude/state/service-session.lock (JSON)
Env-var fallback: DMRZL_SERVICE=1

The marker is keyed to a parent PID. Hooks check process ancestry — only
descendants of that PID see service mode. Other parallel sessions are
unaffected.

Stdlib-only by design (avoids dependency cascade across uv-run hooks).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

MARKER = Path.home() / ".claude" / "state" / "service-session.lock"
TMP_ROOT = Path("/tmp/dmrzl-service")


def _pid_alive(pid: int) -> bool:
    """True if pid is alive on this host. PermissionError implies it exists but isn't ours."""
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False


def _ppid(pid: int) -> int | None:
    """Return parent PID via `ps -o ppid=`. None on failure."""
    try:
        result = subprocess.run(
            ["ps", "-o", "ppid=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    out = result.stdout.strip()
    if not out:
        return None
    try:
        return int(out)
    except ValueError:
        return None


def _pid_in_ancestry(target_pid: int, start_pid: int | None = None) -> bool:
    """True iff target_pid is in the ancestry chain of start_pid (default: current process)."""
    if not _pid_alive(target_pid):
        return False
    current = start_pid if start_pid is not None else os.getpid()
    seen: set[int] = set()
    while current and current not in seen and current != 1:
        if current == target_pid:
            return True
        seen.add(current)
        current = _ppid(current) or 0
    return False


def _read_marker_data() -> dict | None:
    if not MARKER.exists():
        return None
    try:
        return json.loads(MARKER.read_text())
    except (json.JSONDecodeError, OSError):
        return None


def get_service_marker() -> dict | None:
    """Return marker dict if active for this process tree, else None.

    Active means: marker file present AND its PID is in current process ancestry.
    Env-var fallback: DMRZL_SERVICE=1 returns a synthetic marker (no PID gate).
    """
    if os.environ.get("DMRZL_SERVICE") == "1":
        return {
            "session_number": int(os.environ.get("DMRZL_SERVICE_N", "0") or 0),
            "pid": os.getpid(),
            "started_at": "",
            "allow_commits": os.environ.get("DMRZL_SERVICE_ALLOW_COMMITS") == "1",
            "platform": "claude-code",
            "tmp_dir": os.environ.get("DMRZL_SERVICE_TMP", ""),
            "source": "env",
        }
    data = _read_marker_data()
    if data is None:
        return None
    try:
        if not _pid_in_ancestry(int(data["pid"])):
            return None
    except (KeyError, ValueError, TypeError):
        return None
    data["source"] = "marker"
    return data


def is_service_session() -> bool:
    return get_service_marker() is not None


def cleanup_stale() -> bool:
    """Remove marker + tmp dir if marker's PID is dead (host-wide liveness, not ancestry).

    Returns True if cleanup happened. Idempotent. Safe to call from next-session.py.
    Refuses to remove if PID is alive — even if not in our ancestry — because
    that means another active service session exists.
    """
    if not MARKER.exists():
        return False
    data = _read_marker_data()
    if data is None:
        # Corrupt marker — remove.
        MARKER.unlink(missing_ok=True)
        return True
    try:
        pid = int(data["pid"])
    except (KeyError, ValueError, TypeError):
        MARKER.unlink(missing_ok=True)
        return True
    if _pid_alive(pid):
        return False
    MARKER.unlink(missing_ok=True)
    tmp = data.get("tmp_dir", "")
    if tmp and str(tmp).startswith(str(TMP_ROOT) + "/"):
        tmp_path = Path(tmp)
        if tmp_path.exists():
            shutil.rmtree(tmp_path, ignore_errors=True)
    return True


def write_marker(
    session_number: int,
    pid: int,
    started_at: str,
    *,
    allow_commits: bool = False,
    platform: str = "claude-code",
) -> Path:
    """Write the service marker. Caller is responsible for ensuring directory exists."""
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = TMP_ROOT / str(pid)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "session_number": session_number,
        "pid": pid,
        "started_at": started_at,
        "allow_commits": allow_commits,
        "platform": platform,
        "tmp_dir": str(tmp_dir),
    }
    MARKER.write_text(json.dumps(payload, indent=2))
    return MARKER


def clear_marker(*, remove_tmp: bool = True) -> bool:
    """Remove marker + tmp dir. Returns True if marker existed."""
    data = _read_marker_data()
    existed = MARKER.exists()
    MARKER.unlink(missing_ok=True)
    if remove_tmp and data:
        tmp = data.get("tmp_dir", "")
        if tmp and str(tmp).startswith(str(TMP_ROOT) + "/"):
            shutil.rmtree(tmp, ignore_errors=True)
    return existed


if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        marker = get_service_marker()
        if marker:
            print(json.dumps(marker, indent=2))
            sys.exit(0)
        print("no service session active")
        sys.exit(1)
    if cmd == "cleanup":
        sys.exit(0 if cleanup_stale() else 0)  # always 0 — idempotent
    if cmd == "is-active":
        sys.exit(0 if is_service_session() else 1)
    print(f"unknown command: {cmd}", file=sys.stderr)
    sys.exit(2)
