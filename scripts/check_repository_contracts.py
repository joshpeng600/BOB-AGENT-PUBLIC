#!/usr/bin/env python3
"""Validate static JSON/TOML, experiment safety, and artifact provenance."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tomllib
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
TEST_SCORE_KEYS = re.compile(
    r"(^|_)(test)(_|$).*(score|metric|eval)|(^|_)(score|metric|eval).*(test)(_|$)",
    re.IGNORECASE,
)
FORBIDDEN_CONTRACT_FIELDS = {"exp_id", "base_commit", "commit", "frozen_commit"}


def json_files(paths: Iterable[Path]) -> Iterable[Path]:
    for base in paths:
        if base.exists():
            yield from sorted(base.rglob("*.json"))


def walk(value: Any, path: str = "$") -> Iterable[tuple[str, str, Any]]:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            yield child_path, str(key), child
            yield from walk(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from walk(child, f"{path}[{index}]")


def experiment_violations(document: Any) -> list[str]:
    violations: list[str] = []
    for path, key, value in walk(document):
        if TEST_SCORE_KEYS.search(key):
            violations.append(f"{path}: test scoring/evaluation key is forbidden")
        if key.lower() in {"evaluation_split", "scoring_split", "metric_split"}:
            if isinstance(value, str) and value.lower() == "test":
                violations.append(f"{path}: ordinary experiments must use validation")
    return violations


def provenance_violations(document: Any, source: Path) -> list[str]:
    if not isinstance(document, dict):
        return []
    is_artifact_record = document.get("contract_type") in {"run_manifest", "metrics"}
    has_artifacts = bool(document.get("artifacts"))
    if not (is_artifact_record or has_artifacts):
        return []
    sha = document.get("commit_sha")
    if not isinstance(sha, str) or not FULL_SHA.fullmatch(sha) or sha == "0" * 40:
        return [f"{source}: artifact/metric record requires a full lowercase 40-character commit_sha"]
    return []


def contract_field_violations(document: Any) -> list[str]:
    violations: list[str] = []
    for path, key, _value in walk(document):
        if key in FORBIDDEN_CONTRACT_FIELDS:
            violations.append(f"{path}: deprecated contract field; use experiment_id/commit_sha")
    if isinstance(document, dict) and document.get("contract_type"):
        if not isinstance(document.get("experiment_id"), str):
            violations.append("$.experiment_id: required for every formal contract")
        if not isinstance(document.get("commit_sha"), str):
            violations.append("$.commit_sha: required for every formal contract")
    return violations


def main() -> int:
    failures: list[str] = []

    all_json = list(json_files([ROOT / "governance", ROOT / "coordination", ROOT / "configs", ROOT / "contracts", ROOT / "reports"]))
    for path in all_json:
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            failures.append(f"{path.relative_to(ROOT)}: invalid JSON: {exc}")
            continue

        if path.is_relative_to(ROOT / "configs"):
            failures.extend(f"{path.relative_to(ROOT)}: {item}" for item in experiment_violations(document))
        failures.extend(f"{path.relative_to(ROOT)}: {item}" for item in contract_field_violations(document))
        if not path.is_relative_to(ROOT / "contracts"):
            failures.extend(provenance_violations(document, path.relative_to(ROOT)))

    interventions = ROOT / "governance" / "manual_interventions.jsonl"
    if interventions.exists():
        for line_number, line in enumerate(interventions.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                failures.append(f"{interventions.relative_to(ROOT)}:{line_number}: invalid JSONL: {exc}")

    for path in sorted((ROOT / ".codex").rglob("*.toml")):
        try:
            with path.open("rb") as handle:
                tomllib.load(handle)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            failures.append(f"{path.relative_to(ROOT)}: invalid TOML: {exc}")

    if failures:
        print("Repository contract check failed:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1

    print(f"Repository contract check passed ({len(all_json)} JSON files plus JSONL/TOML validated).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
