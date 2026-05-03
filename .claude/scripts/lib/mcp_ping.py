#!/usr/bin/env -S uv run --script --quiet
# AUDIENCE: public
# MATURITY: stable
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Live ping for an Obsidian MCP server.

Spawns a fresh `npx -y obsidian-mcp-rs <vault_path>` and exchanges JSON-RPC
initialize + tools/list. Exits 0 if the response advertises the read-note
tool within the timeout, 1 otherwise. Replaces the bash mcp-ping.sh
(see vault/dmrzl/research/2026-05-02-obsidian-mcp-broken-pipe-diagnosis.md
for background — this script is the Python pilot for migrating off bash).

CLI:
    mcp_ping.py <vault_path> [--timeout SECONDS]
    mcp_ping.py --help
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import sys
from pathlib import Path
from typing import Any, cast

INIT_FRAME = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "mcp-ping", "version": "1.0"},
    },
}
INITIALIZED_FRAME = {
    "jsonrpc": "2.0",
    "method": "notifications/initialized",
    "params": {},
}
TOOLS_LIST_FRAME = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list",
    "params": {},
}


async def ping_obsidian_mcp(vault_path: Path, timeout: float = 8.0) -> bool:
    """Return True iff a fresh obsidian-mcp-rs returns read-note in tools/list.

    Uses incremental readline with a per-read timeout instead of
    proc.communicate(). communicate() drains stdout to EOF, but obsidian-mcp-rs
    keeps stdout open after responding, so communicate() blocks even when
    we already have the answer. Reading line-by-line lets us return as soon
    as the read-note frame arrives, then kill the child in `finally`.
    """
    if not vault_path.is_dir():
        return False

    proc = await asyncio.create_subprocess_exec(
        "npx", "-y", "obsidian-mcp-rs", str(vault_path),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )

    try:
        request = b"\n".join(
            json.dumps(f).encode()
            for f in (INIT_FRAME, INITIALIZED_FRAME, TOOLS_LIST_FRAME)
        ) + b"\n"
        assert proc.stdin is not None
        proc.stdin.write(request)
        await proc.stdin.drain()

        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        assert proc.stdout is not None

        while loop.time() < deadline:
            remaining = deadline - loop.time()
            try:
                line = await asyncio.wait_for(
                    proc.stdout.readline(), timeout=remaining
                )
            except TimeoutError:
                return False
            if not line:
                return False
            if not line.startswith(b"{"):
                continue
            try:
                frame = json.loads(line)
            except json.JSONDecodeError:
                continue
            tools = frame.get("result", {}).get("tools", [])
            if any(t.get("name") == "read-note" for t in tools):
                return True
        return False
    finally:
        if proc.returncode is None:
            proc.kill()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(proc.wait(), timeout=2.0)


def _silence_loop_closed(args: object) -> None:
    """Silence asyncio's "Event loop is closed" cleanup noise on macOS.

    BaseSubprocessTransport.__del__ runs at GC time, after asyncio.run() has
    closed the event loop, and tries to schedule a final write_eof — which
    fails harmlessly. The error is cosmetic but pollutes script stderr.
    """
    exc_type = getattr(args, "exc_type", None)
    exc_value = getattr(args, "exc_value", None)
    if exc_type is RuntimeError and "Event loop is closed" in str(exc_value):
        return
    sys.__unraisablehook__(cast(Any, args))


def main() -> int:
    sys.unraisablehook = _silence_loop_closed  # type: ignore[assignment]
    parser = argparse.ArgumentParser(
        description="Live ping for an Obsidian MCP server.",
    )
    parser.add_argument("vault_path", type=Path, help="Absolute path to vault root")
    parser.add_argument(
        "--timeout", type=float, default=8.0,
        help="Seconds to wait for response (default: 8)",
    )
    args = parser.parse_args()

    ok = asyncio.run(ping_obsidian_mcp(args.vault_path, args.timeout))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
