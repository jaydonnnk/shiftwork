"""Read-only inspection of two recorded Slice 12 checkpoint images; no spawn, no inference."""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import hashlib
import json
import os
import posixpath
from pathlib import Path
import sys
import time
from typing import Any, TextIO

from contree_client.exceptions import APIStatusError
from contree_client.httpx import ContreeAsyncClient


IMAGES = (
    "c043c2cc-f830-4948-8296-1b5093376789",
    "9d3eb2d2-219f-4bf6-9ced-2ac495ccab38",
)
EXPECTED_FILE = "/tmp/slice12-large.bin"
EXPECTED_BYTES = 2_097_152
LIST_PATHS = ("/", "/tmp", "/work")
MAX_DOWNLOADS_PER_IMAGE = 8
SCRIPT_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def assert_clean(surface: object, secrets: tuple[str, str]) -> None:
    for secret in secrets:
        if secret not in json.dumps({"needle": secret}, ensure_ascii=False):
            raise RuntimeError("scanner_self_test_failed")
    serialized = json.dumps(surface, default=str, sort_keys=True, ensure_ascii=False)
    for secret in secrets:
        if secret in serialized:
            raise RuntimeError("secret_detected_in_record")


def write_record(handle: TextIO, record: dict[str, Any], secrets: tuple[str, str]) -> None:
    record["utc"] = utc_now()
    record["script_sha256"] = SCRIPT_SHA256
    assert_clean(record, secrets)
    line = json.dumps(record, default=str, sort_keys=True, ensure_ascii=False)
    handle.write(line + "\n")
    handle.flush()
    print(line, flush=True)


async def list_directory(
    client: ContreeAsyncClient, handle: TextIO, secrets: tuple[str, str], image: str, path: str
) -> dict[str, Any]:
    record: dict[str, Any] = {"record": "image_list", "image": image, "path": path}
    try:
        listing = await client.inspect_image_list(image, path)
        record["ok"] = True
        record["raw"] = [dataclasses.asdict(item) for item in listing.files]
    except APIStatusError as exc:
        record.update(ok=False, error="api_status", status=exc.status)
    except Exception as exc:
        record.update(ok=False, error="exception", error_type=type(exc).__name__)
    write_record(handle, record, secrets)
    return record


async def download_file(
    client: ContreeAsyncClient, handle: TextIO, secrets: tuple[str, str], image: str, path: str
) -> dict[str, Any]:
    record: dict[str, Any] = {"record": "image_download", "image": image, "path": path}
    try:
        data = await client.inspect_image_download(image, path)
        record.update(
            ok=True,
            bytes=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
            head_hex=data[:32].hex(),
        )
    except APIStatusError as exc:
        record.update(ok=False, error="api_status", status=exc.status)
    except Exception as exc:
        record.update(ok=False, error="exception", error_type=type(exc).__name__)
    write_record(handle, record, secrets)
    return record


def download_candidates(listings: list[dict[str, Any]]) -> list[str]:
    found: list[str] = [EXPECTED_FILE]
    for record in listings:
        if not record.get("ok"):
            continue
        base = str(record.get("path", ""))
        for item in record.get("raw", []):
            if item.get("is_dir") or not item.get("is_regular"):
                continue
            full = posixpath.join(base, str(item.get("path")))
            if full.startswith("/tmp/") and full not in found:
                found.append(full)
    return found[:MAX_DOWNLOADS_PER_IMAGE]


def listed_sizes(listings: list[dict[str, Any]]) -> dict[str, Any]:
    sizes: dict[str, Any] = {}
    for record in listings:
        if not record.get("ok"):
            continue
        base = str(record.get("path", ""))
        for item in record.get("raw", []):
            sizes[posixpath.join(base, str(item.get("path")))] = item.get("size")
    return sizes


def verdict_for(expected: dict[str, Any] | None) -> str:
    if expected is None or not expected.get("ok"):
        return "NOT_DOWNLOADED"
    size = expected.get("bytes")
    if size == EXPECTED_BYTES:
        return "INTACT_EXPECTED_BYTES"
    if size == 0:
        return "ZERO_BYTES"
    return "OTHER_BYTES"


async def run(out_path: Path, token: str, project: str) -> int:
    secrets = (token, project)
    if out_path.exists():
        print(json.dumps({"record": "reinspection_refused", "reason": "output_file_exists"}))
        return 2
    client = ContreeAsyncClient(token, project=project, timeout=20)
    try:
        with out_path.open("x", encoding="utf-8") as handle:
            write_record(
                handle,
                {
                    "record": "reinspection_header",
                    "scope": "read-only inspect_image_list and inspect_image_download only",
                    "images": list(IMAGES),
                    "list_paths": list(LIST_PATHS),
                    "expected_file": EXPECTED_FILE,
                    "expected_bytes": EXPECTED_BYTES,
                },
                secrets,
            )
            for image in IMAGES:
                listings = []
                for path in LIST_PATHS:
                    listings.append(await list_directory(client, handle, secrets, image, path))
                sizes = listed_sizes(listings)
                downloads = []
                for path in download_candidates(listings):
                    downloads.append(await download_file(client, handle, secrets, image, path))
                expected = next((r for r in downloads if r["path"] == EXPECTED_FILE), None)
                write_record(
                    handle,
                    {
                        "record": "image_verdict",
                        "image": image,
                        "expected_file": EXPECTED_FILE,
                        "listed_bytes": sizes.get(EXPECTED_FILE),
                        "download_ok": expected.get("ok") if expected else None,
                        "downloaded_bytes": expected.get("bytes") if expected else None,
                        "sha256": expected.get("sha256") if expected else None,
                        "result": verdict_for(expected),
                    },
                    secrets,
                )
        return 0
    finally:
        await client.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    token = os.environ.get("NEBIUS_API_KEY", "")
    project = os.environ.get("NEBIUS_PROJECT_ID", "")
    if not token or not project or token != token.strip() or project != project.strip():
        print(json.dumps({"record": "reinspection_header", "result": "missing_or_whitespace_environment"}))
        return 3
    return asyncio.run(run(Path(args.out), token, project))


if __name__ == "__main__":
    sys.exit(main())
