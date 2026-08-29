from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.common import ValidationError, read_json


REQUIRED_FIELDS = {
    "experiment-spec": (
        "exp_id", "base_commit", "hypothesis", "single_variable", "allowed_files",
        "forbidden_files", "data_mode", "seeds", "smoke_batches", "max_minutes", "success", "status",
    ),
    "feature-proposal": (
        "exp_id", "raw_columns", "time_boundary", "train_only_statistics", "missing_values",
        "dimension", "leakage_checks", "expected_impact", "code_commit",
    ),
    "model-proposal": (
        "exp_id", "objective", "sampling_unit", "inputs", "outputs", "hyperparameters",
        "resource_estimate", "failure_conditions", "fallback", "code_commit",
    ),
    "run-manifest": (
        "exp_id", "commit", "dirty", "config_hash", "data_hash", "seed", "started_at",
        "ended_at", "exit_code", "checkpoint_hash", "prediction_hash", "log_path", "manual_intervention",
        "command",
    ),
    "metrics": (
        "exp_id", "commit", "valid", "baseline_delta", "seed_summary", "prediction_checks",
        "protected_hashes", "compliance", "recommendation",
    ),
}

ALIASES = {
    "experiment_spec": "experiment-spec",
    "feature_proposal": "feature-proposal",
    "model_proposal": "model-proposal",
    "run_manifest": "run-manifest",
}


def validate_contract(contract_type: str, document: Any) -> None:
    contract_type = ALIASES.get(contract_type, contract_type)
    if contract_type not in REQUIRED_FIELDS:
        raise ValidationError(f"unknown contract type: {contract_type}")
    if not isinstance(document, dict):
        raise ValidationError("contract root must be a JSON object")
    missing = [field for field in REQUIRED_FIELDS[contract_type] if field not in document]
    if missing:
        raise ValidationError(f"missing required fields: {', '.join(missing)}")
    empty = [
        field for field in REQUIRED_FIELDS[contract_type]
        if document[field] is None or document[field] == "" or document[field] == []
    ]
    if empty:
        raise ValidationError(f"required fields are empty: {', '.join(empty)}")

    commit_fields = [name for name in ("base_commit", "code_commit", "commit") if name in document]
    for field in commit_fields:
        if not isinstance(document[field], str) or not re.fullmatch(r"[0-9a-fA-F]{40}", document[field]):
            raise ValidationError(f"{field} must be a full 40-character commit SHA")
    if "exp_id" in document and not re.fullmatch(r"exp_[A-Za-z0-9_-]+", str(document["exp_id"])):
        raise ValidationError("exp_id must start with 'exp_'")
    if contract_type == "experiment-spec":
        if document["data_mode"] != "train_valid_only":
            raise ValidationError("experiment data_mode must be train_valid_only")
        if not all(isinstance(seed, int) for seed in document["seeds"]):
            raise ValidationError("seeds must be an array of integers")
        if document["status"] not in {"PROPOSED", "APPROVED_FOR_IMPLEMENTATION"}:
            raise ValidationError("unsupported experiment status")
    if contract_type == "run-manifest":
        if not isinstance(document["dirty"], bool):
            raise ValidationError("dirty must be boolean")
        if not isinstance(document["exit_code"], int):
            raise ValidationError("exit_code must be integer")
        if not isinstance(document["command"], list) or not all(
            isinstance(part, str) and part for part in document["command"]
        ):
            raise ValidationError("command must be a non-empty array of strings")
    if contract_type == "metrics" and document["recommendation"] not in {"ACCEPT", "REJECT"}:
        raise ValidationError("metrics recommendation must be ACCEPT or REJECT")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate one of the five team JSON contracts.")
    parser.add_argument("--type", required=True, choices=tuple(REQUIRED_FIELDS) + tuple(ALIASES))
    parser.add_argument("--path", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_contract(args.type, read_json(args.path))
    except ValidationError as exc:
        print("CONTRACT=FAIL", file=sys.stderr)
        print(f"ERROR={exc}", file=sys.stderr)
        return 1
    print(f"CONTRACT_TYPE={ALIASES.get(args.type, args.type)}")
    print("CONTRACT=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
