# exp_001 B cycle precheck and synthetic smoke handoff

STATUS=WAITING_FOR_A_REAL_VALID_GATE
ROLE=B
PHASE=SYNTHETIC_SMOKE
BRANCH=B-cycle-exp001
BASE_MAIN_SHA=9174ef94c6e40beacb4f535a1be01a931c0b36ce
COMMIT_SHA=9174ef94c6e40beacb4f535a1be01a931c0b36ce
WORKTREE_CLEAN=true
EXPERIMENT_ID=exp_001
EXPERIMENT_SPEC_HASH=79e4ca963172b61d63aadf14fed5226090a26dc9c30f7cdadb1524bc3468dfe1
BASELINE_CONFIG_HASH=612d6478b0508a734f949129b839732a9088bb0fe75d7f5d5026446740f3cc4f
CANDIDATE_CONFIG_HASH=6356cc46d69f1e7efc7c4f0f1927516c26f5d25f4f248d4b505c5061db4c6ae6
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
SEED=0
MODE=valid-only
SMOKE_STATUS=PASS_BASELINE_AND_CANDIDATE
BASELINE_STATUS=NOT_STARTED_GATE_BLOCKED
CANDIDATE_STATUS=NOT_STARTED_GATE_BLOCKED
RETRY_COUNT=0
PR25_EVIDENCE_USED=false
FORMAL_METRICS_PRODUCED=false
test_access=false
NEXT_RECEIVER=A

## Gate result

The repository owner explicitly approved starting cycle, but authoritative
`origin/main` still records:

```text
REAL_VALID_RUN_ALLOWED=READY_PENDING_EXPLICIT_USER_CYCLE_APPROVAL
authorized_attempts_active=0
```

There was no open A gate PR at the time of this handoff. B therefore stopped
before any real-data training. A must record and merge an exact
`REAL_VALID_RUN_ALLOWED=ALLOWED` decision before B can run the formal baseline
or candidate.

## Real development-data precheck

The Git-ignored development data was inspected read-only at:

```text
C:\Users\asus-pc\Desktop\BOBAAA\BOB-AGENT\data\dev
```

Its manifest and aggregate data hash both equal
`69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`.
All source hashes matched C's merged readiness evidence.

`python tools/preflight.py --data-dir <DATA_DIR> --mode experiment --config configs/candidates/bpr_fm.json`
returned:

```text
ROWS=1266021
TEST_ROWS=0
MIN_DATE=20220409
MAX_DATE=20220428
LABEL_VALUES=[0, 1]
PREFLIGHT=PASS
```

C's same-user pair evidence remains:

```text
PAIR_COUNT=382579
ELIGIBLE_USERS=24290
TOTAL_USERS=26210
USER_COVERAGE=0.926745516978
```

## Contract and test verification

Executed on the clean commit above:

- `python -m pytest -q -p no:cacheprovider`: PASS, 117 passed, 4 Windows
  symlink-privilege skips, 39 subtests passed.
- `python -m unittest discover -s tests -v`: PASS, 121 passed, 4 Windows
  symlink-privilege skips.
- `python scripts/check_repository_contracts.py`: PASS, 27 JSON files plus
  JSONL/TOML.
- `python scripts/check_protected_files.py`: PASS, all seven protected files.
- `python scripts/check_prediction_contract.py`: PASS, 9 of 9.
- Python: 3.13.5.

## Explicit synthetic smoke

The smoke stage used a generated two-user synthetic fixture, not `data/dev`.
Both repository routes were exercised with `seed=0`, `mode=valid-only`, and an
explicit upper bound of five batches:

```text
python tools/run_experiment.py --experiment-spec experiments/exp_001.json \
  --config configs/approved/baseline_fm.json \
  --data-dir data/synthetic_exp001_9174ef9 \
  --output-dir artifacts/cycle_exp001_smoke_9174ef9_baseline \
  --seed 0 --max-batches 5 --synthetic-smoke --mode valid-only
EXIT=0

python tools/run_experiment.py --experiment-spec experiments/exp_001.json \
  --config configs/candidates/bpr_fm.json \
  --data-dir data/synthetic_exp001_9174ef9 \
  --output-dir artifacts/cycle_exp001_smoke_9174ef9_candidate \
  --seed 0 --max-batches 5 --synthetic-smoke --mode valid-only
EXIT=0
```

Both manifests report `status=synthetic_smoke`,
`evidence_tier=synthetic_only`, `max_batches=5`, `retry_count=0`, and
`test_access=false`. Each tiny fixture produced one actual batch, which is
within the five-batch bound.

Local ignored evidence:

| Variant | Manifest path | Manifest SHA-256 |
| --- | --- | --- |
| baseline | `artifacts/cycle_exp001_smoke_9174ef9_baseline/run_manifest.json` | `50b9df9dce8862033ba352216db821aa220372011489266e10dc6b2e5ea2f9a0` |
| candidate | `artifacts/cycle_exp001_smoke_9174ef9_candidate/run_manifest.json` | `d4657188ea83a3595059a946304fa4dec8ee593b483a555e3b2b60a4878dff4e` |

`validate_artifact_files(..., formal_evidence=False)` passed for both packages.
`python -m tools.audit_run` rejected both with
`only a completed formal run may be audited`, confirming that synthetic smoke
cannot be accepted as formal evidence.

No real model training was performed, no formal validation metric was
produced, no prediction or checkpoint was committed, and no test data was
accessed.
