"""Validate a prediction CSV against the official row order without scoring."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.final_approval import verify_final_approval
from tools.official_rows import load_splits
from tools.prediction_contract import PredictionContractError, validate_prediction_file
from tools.project_security import SecurityError, verify_protected_files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prediction", type=Path)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--split", default="valid", choices=["valid", "test"])
    parser.add_argument("--approval", type=Path)
    args = parser.parse_args()
    try:
        verify_protected_files()
        if args.split == "test":
            if args.approval is None:
                raise SecurityError("Test validation requires --approval")
            verify_final_approval(args.approval)
        rows = load_splits(args.data_dir)[args.split]
        scores = validate_prediction_file(args.prediction, rows)
    except (OSError, SecurityError, PredictionContractError, ValueError) as error:
        print(f"CHECK FAILED: {error}")
        return 1
    print(f"CHECK PASSED: {len(scores)} rows aligned for split={args.split}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
