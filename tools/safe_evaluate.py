"""Protected evaluation gate around the official KuaiRand evaluator."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from starter import evaluate as official_evaluator
from tools.final_approval import verify_final_approval
from tools.official_rows import load_splits
from tools.prediction_contract import (
    PredictionContractError,
    validate_evaluator_arrays,
    validate_prediction_file,
)
from tools.project_security import (
    SecurityError,
    git_head,
    git_is_dirty,
    sha256_file,
    verify_protected_files,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prediction", required=True, type=Path)
    parser.add_argument("--split", required=True, choices=["valid", "test"])
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--approval",
        type=Path,
        help="Human approval JSON; required for any test operation",
    )
    args = parser.parse_args()

    try:
        protected_hashes = verify_protected_files()
        evaluation_commit = git_head()
        if git_is_dirty():
            raise SecurityError("Worktree is dirty; evaluation denied")
        if args.output.resolve() == args.prediction.resolve():
            raise SecurityError("Output path must not overwrite the immutable prediction")
        if args.split == "test":
            if args.approval is None:
                raise SecurityError(
                    "Normal mode only permits valid; test requires --approval"
                )
            verify_final_approval(args.approval)

        prediction_hash = sha256_file(args.prediction)
        splits = load_splits(args.data_dir)
        rows = splits[args.split]
        scores = validate_prediction_file(args.prediction, rows)
        users, labels, scores = validate_evaluator_arrays(
            [row[1] for row in rows],
            [row[6] for row in rows],
            scores,
        )
        metrics = official_evaluator.evaluate(users, labels, scores)
        expected_primary = (
            float(metrics["GAUC"]) + float(metrics["nDCG@5"])
        ) / 2.0
        if not math.isclose(float(metrics["primary"]), expected_primary):
            raise SecurityError(
                "Official primary is not the arithmetic mean of GAUC and nDCG@5"
            )
        if sha256_file(args.prediction) != prediction_hash:
            raise SecurityError("Immutable prediction changed during evaluation")
        if git_head() != evaluation_commit or git_is_dirty():
            raise SecurityError("Git commit or worktree changed during evaluation")
    except (OSError, SecurityError, PredictionContractError, ValueError) as error:
        print(f"EVALUATION DENIED: {error}")
        return 1

    output = {
        "GAUC": metrics["GAUC"],
        "nDCG@5": metrics["nDCG@5"],
        "primary": metrics["primary"],
        "rows": metrics["rows"],
        "users": metrics["users"],
        "evaluator_hash": protected_hashes["starter/evaluate.py"],
        "evaluator_role": "E",
        "split": args.split,
        "prediction_hash": prediction_hash,
        "commit_sha": evaluation_commit,
        "worktree_clean": True,
        "test_access": args.split == "test",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
