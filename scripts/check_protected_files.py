#!/usr/bin/env python3
"""Fail closed unless every protected file exists and matches its pinned SHA-256."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "governance" / "protected_files.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    failures: list[str] = []
    for entry in registry.get("files", []):
        relative = entry.get("path", "")
        expected = entry.get("sha256")
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"MISSING: {relative}")
            continue
        if not isinstance(expected, str) or len(expected) != 64:
            failures.append(f"UNPINNED: {relative}")
            continue
        actual = sha256(path)
        if actual != expected.lower():
            failures.append(f"HASH_MISMATCH: {relative} expected={expected} actual={actual}")
        else:
            print(f"OK {relative} sha256={actual}")

    if failures:
        print("Protected-file check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
