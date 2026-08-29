from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common import ValidationError, read_json, sha256_file


DEFAULT_MANIFEST = Path("governance/protected_files.json")


def _entries(document: Any) -> list[tuple[str, str]]:
    if isinstance(document, dict) and isinstance(document.get("files"), dict):
        raw = [{"path": path, "sha256": digest} for path, digest in document["files"].items()]
    elif isinstance(document, dict) and isinstance(document.get("protected_files"), list):
        raw = document["protected_files"]
    elif isinstance(document, list):
        raw = document
    else:
        raise ValidationError(
            "protected manifest must be a list, {'protected_files': [...]}, or {'files': {path: sha256}}"
        )

    entries: list[tuple[str, str]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValidationError(f"protected entry {index} must be an object")
        path = item.get("path")
        digest = item.get("sha256") or item.get("hash")
        if not isinstance(path, str) or not path:
            raise ValidationError(f"protected entry {index} has no path")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValidationError(f"protected entry {index} has invalid SHA-256")
        entries.append((path, digest.lower()))
    if not entries:
        raise ValidationError("protected manifest is empty")
    return entries


def verify(manifest_path: Path, repo_root: Path) -> list[str]:
    failures: list[str] = []
    for relative, expected in _entries(read_json(manifest_path)):
        candidate = (repo_root / relative).resolve()
        try:
            candidate.relative_to(repo_root.resolve())
        except ValueError:
            failures.append(f"path escapes repository: {relative}")
            continue
        if not candidate.is_file():
            failures.append(f"missing protected file: {relative}")
            continue
        actual = sha256_file(candidate)
        if actual != expected:
            failures.append(f"hash mismatch: {relative} expected={expected} actual={actual}")
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify immutable Starter Kit files by SHA-256.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        failures = verify(args.manifest.resolve(), args.repo_root.resolve())
    except ValidationError as exc:
        print(f"PROTECTED_FILES=FAIL\nERROR={exc}", file=sys.stderr)
        return 2
    if failures:
        print("PROTECTED_FILES=FAIL", file=sys.stderr)
        for failure in failures:
            print(f"ERROR={failure}", file=sys.stderr)
        return 1
    print("PROTECTED_FILES=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
