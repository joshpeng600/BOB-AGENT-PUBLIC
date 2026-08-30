# exp_002 B baseline-route and synthetic setup readiness

STATUS=READY_FOR_INDEPENDENT_E_PRE_EVALUATION_REVIEW
ROLE=B
EXPERIMENT_ID=exp_002
BRANCH=B-Part
BASE_MAIN_SHA=7bf6cdc188d952a56563a06662ffbbe9b1d4c720
B_PART_SYNC_MERGE_SHA=4cafa30c2969ac923623514bd6059965f8818ed7
SYNC_PRESERVATION_SHA=e904c2840dc31aceb335935b9bb6973fdeeb5a52
SOURCE_REVIEWED_COMMIT_SHA=faccd1a9c4cee07949f2787090285cca5807eae7
IMPLEMENTATION_COMMIT_SHA=ce07ca636676e794d86641d2dede5bd840724f98
EXPERIMENT_SPEC_HASH=c3d1257751d2abf15d62a0638679efe892cc13a8ff3325630ab2acbbece5c8c9
BASELINE_CONFIG_HASH=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
CANDIDATE_CONFIG_HASH=4ae653c2a68c1dc461ff2149540920e009355637e22e557b70c68e41460d2b61
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
SEED=0
MODE=valid-only
SMOKE_BATCHES=1
BASELINE_SMOKE=PASS
CANDIDATE_SMOKE=PASS
BASELINE_OBJECTIVE=same_user_bpr
BASELINE_NEGATIVES_PER_POSITIVE=1
CANDIDATE_OBJECTIVE=same_user_bpr
CANDIDATE_NEGATIVES_PER_POSITIVE=2
RETRY_COUNT=0
REAL_VALID_RUN_ALLOWED=false
REAL_DATA_TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
PR25_EVIDENCE_USED=false
test_access=false
NEXT_RECEIVER=E,A

## B-Part synchronization

The existing remote `B-Part` diverged from `main` at
`28d4d7480c0a76d5076dc10e694898188af99473`. B synchronized it without force
push or history rewriting by creating a normal merge whose parents include
both current main and the existing B-Part history. Five conflicts were old
versions of B-owned runner, validator, and tests; the current main versions
were preserved. One obsolete validator call carried through as a non-conflict
and was removed in the explicit follow-up commit above, restoring the exact
current-main tree before the exp_002 repair was applied.

## Approved baseline-route repair

The implementation reproduces A's reviewed source commit
`faccd1a9c4cee07949f2787090285cca5807eae7` on the synchronized B-Part history.

- The baseline objective is derived from the exact approved baseline config
  selected by `experiments/exp_002.json`, instead of being hardcoded to
  pointwise BCE.
- The exp_002 baseline is therefore the approved exp_001 champion using
  `same_user_bpr` with one negative per positive.
- The exp_002 candidate remains `same_user_bpr` with exactly two negatives per
  positive.
- Candidate routes reject approved baseline configs, and baseline/candidate
  path or objective forgeries remain fail-closed.

The original exp_002 `allowed_files` list omitted `tools/run_experiment.py`,
although the B role deliverable explicitly requires generalizing the runtime
baseline route. The later, more specific A review in
`coordination/inbox/A/exp_002_setup_delivery_review_20260831.md` identifies
the complete source commit and explicitly directs B to integrate or reproduce
that reviewed change on B-Part. This handoff applies only that exact reviewed
six-line runtime change and does not expand the file scope further.

Changed implementation/test files relative to current main:

- `tools/run_experiment.py`
- `tools/validate_contract.py`
- `tests/test_run_experiment.py`
- `tests/test_audit.py`

No model, training source, data, feature, evaluator, protected, or `starter/`
file changed.

## Verification

Executed on the clean implementation commit:

- `python -m pytest -q -p no:cacheprovider`: PASS, 121 passed, 4 Windows
  symlink-privilege skips, 39 subtests passed.
- `python -m unittest discover -s tests -v`: PASS, 125 passed, 4 Windows
  symlink-privilege skips.
- `python scripts/check_repository_contracts.py`: PASS, 40 JSON files plus
  JSONL/TOML.
- `python scripts/check_protected_files.py`: PASS, all seven protected files.
- `python scripts/check_prediction_contract.py`: PASS, 9 of 9.
- `git diff --check`: PASS.
- `git diff -- starter/`: empty.

## One-batch explicit synthetic smoke

Both approved repository routes used the same generated two-user synthetic
fixture, seed 0, valid-only mode, and exactly one bounded batch. The real
`data/dev` snapshot was not used for training.

```text
python tools/run_experiment.py --experiment-spec experiments/exp_002.json \
  --config configs/approved/exp_001.json \
  --data-dir data/synthetic_exp002_ce07ca6 \
  --output-dir artifacts/exp002_smoke_ce07ca6_baseline \
  --seed 0 --max-batches 1 --synthetic-smoke --mode valid-only
EXIT=0

python tools/run_experiment.py --experiment-spec experiments/exp_002.json \
  --config configs/candidates/bpr_fm_neg2.json \
  --data-dir data/synthetic_exp002_ce07ca6 \
  --output-dir artifacts/exp002_smoke_ce07ca6_candidate \
  --seed 0 --max-batches 1 --synthetic-smoke --mode valid-only
EXIT=0
```

| Variant | Run ID | Manifest SHA-256 | Route binding |
| --- | --- | --- | --- |
| baseline | `run-20260830T201953275473Z-exp_002-ce07ca63` | `de91e0f03560baa13afef3fbfe8eca0b286de0b3753cb120c97a522f27a27406` | BPR, negatives=1 |
| candidate | `run-20260830T201953782358Z-exp_002-ce07ca63` | `7bdbf13e68c7a06fd1baaf44c88da28d2931dfb53ef086cc8a17acec1009961c` | BPR, negatives=2 |

Both manifests report `status=synthetic_smoke`,
`evidence_tier=synthetic_only`, `max_batches=1`, `batches_seen=1`,
`retry_count=0`, and `test_access=false`. Non-formal artifact validation
passed for both packages. The formal auditor rejected each package with
`only a completed formal run may be audited`, as required.

Current main keeps exp_002 `REAL_VALID_RUN_ALLOWED` blocked. This readiness
does not authorize real-data training or formal metric production. E must
independently pre-review the merged B and D setup evidence before A may decide
whether to open a later one-pair formal gate.
