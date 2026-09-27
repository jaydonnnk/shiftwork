"""Slice 12 Sandbox entitlement preflight.

The full capability matrix must not run until this preflight grants spawning.
Credentials come from the process environment; this module never reads .env.
"""

from __future__ import annotations

import asyncio
import argparse
import dataclasses
import json
import os
from pathlib import Path
import sys
import time

from contree_client.exceptions import APIStatusError
from contree_client.httpx import ContreeAsyncClient


async def _preflight(token: str, project: str) -> tuple[dict[str, object], int]:
    client = ContreeAsyncClient(token, project=project, timeout=20)
    started = time.monotonic()
    try:
        response = dataclasses.asdict(await client.whoami())
        permissions = response.get("permissions", {})
        allowed = isinstance(permissions, dict) and permissions.get("spawn") is True
        return {
            "probe": "sandbox_whoami",
            "result": "ready_for_capability_probes" if allowed else "blocked_no_spawn_permission",
            "elapsed_ms": round((time.monotonic() - started) * 1000),
            "permissions": permissions,
            "limits": response.get("limits"),
            "operations_stat": response.get("operations_stat"),
        }, 0 if allowed else 2
    except APIStatusError as exc:
        return {
            "probe": "sandbox_whoami",
            "result": "api_error",
            "status": exc.status,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        }, 3
    except Exception as exc:
        return {
            "probe": "sandbox_whoami",
            "result": "transport_or_decode_error",
            "error_type": type(exc).__name__,
            "elapsed_ms": round((time.monotonic() - started) * 1000),
        }, 4
    finally:
        await client.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("preflight", "judge", "service", "controls", "pair",
                                            "outage", "escape", "reuse", "trials",
                                            "reset", "readback"), default="service")
    args = parser.parse_args()
    if args.phase == "judge":
        from demos.gateway_spike_live import judge_route_probe

        return judge_route_probe(Path.cwd())
    token = os.environ.get("NEBIUS_API_KEY", "")
    project = os.environ.get("NEBIUS_PROJECT_ID", "")
    if not token or not project:
        print(json.dumps({"probe": "sandbox_whoami", "result": "missing_environment"}))
        return 3
    if token != token.strip() or project != project.strip():
        print(json.dumps({"probe": "sandbox_whoami", "result": "environment_whitespace"}))
        return 3
    if args.phase == "preflight":
        observation, exit_code = asyncio.run(_preflight(token, project))
        print(json.dumps(observation, default=str, sort_keys=True))
        return exit_code
    from demos.gateway_spike_live import run

    try:
        return asyncio.run(run(args.phase, token, project))
    except APIStatusError as exc:
        print(json.dumps({"probe": "api_error", "status": exc.status}))
        return 3
    except Exception as exc:
        print(json.dumps({"probe": "spike_error", "error_type": type(exc).__name__}))
        return 4


if __name__ == "__main__":
    sys.exit(main())
