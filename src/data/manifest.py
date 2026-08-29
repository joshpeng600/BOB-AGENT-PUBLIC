"""Deterministic source-data manifest and SHA-256 rules."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


MANIFEST_VERSION = 1


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_manifest(output_path: str | Path, files: list[dict]) -> None:
    payload = {"manifest_version": MANIFEST_VERSION, "hash_algorithm": "sha256", "files": files}
    Path(output_path).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
