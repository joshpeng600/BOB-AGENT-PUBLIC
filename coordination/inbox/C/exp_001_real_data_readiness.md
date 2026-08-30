# exp_001 real development-data readiness — C

STATUS=REAL_DEV_DATA_READY_FOR_B_SETUP
ROLE=C
EXPERIMENT_ID=exp_001
B_COMMIT_SHA=11756451fd6e6f7ea744ed79a355c037fe9fedf0
DATA_AVAILABLE=true
MANIFEST_SHA256=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
HASH_MATCH=true
MAX_DATE=20220428
TEST_ROWS=0
PREFLIGHT=PASS
TRAIN_ONLY_PAIR_SAMPLING=true
PAIR_FEASIBILITY_VERIFIED=true
PAIR_COUNT=382579
ELIGIBLE_USERS=24290
TOTAL_USERS=26210
USER_COVERAGE=0.926745516978
SAME_USER_PAIR_CHECK=true
VALID_ROW_ORDER_PRESERVED=true
NEW_FEATURES_ADDED=false
TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
test_access=false
REAL_VALID_RUN_AUTHORIZED_BY_C=false

## Scope

This is real-data readiness evidence only.  The local, Git-ignored `data/dev`
directory was checked read-only.  No model was trained, no prediction was
created, no formal metric was calculated, and no test data was accessed.

## Integrity and data boundary evidence

All seven supplied SHA-256 values matched the transferred development data:

| File | SHA-256 |
| --- | --- |
| `dataset_manifest.json` | `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002` |
| `log_random_4_22_to_5_08_pure.csv` | `ba0a5f106467848d90b28fc5015a2df7076bc108959abf1960595bce4cff492e` |
| `log_standard_4_08_to_4_21_pure.csv` | `5bb6eb0b3d9f47e5436cb5dc82ee1899b845ebf9750a5560b801e929e18bd41c` |
| `log_standard_4_22_to_5_08_pure.csv` | `60a464f485b39ee4edd954606ceb63e1d3dd006f81a0fa5e8da8f0aafa8cd2a8` |
| `user_features_pure.csv` | `dc729a656301b4c6d07f713fe41d05ec9bfaab670b90e531c70037caf033c011` |
| `video_features_basic_pure.csv` | `a6f7ee02684c5777422306cdc416e170302288aa89aca9dfea995edbd625bcc2` |
| `video_features_statistic_pure.csv` | `d5c9e237ef2c6c1fc0e7f27e952f215d6626ecd934b01a6c53ecfcc72540f6b6` |

The manifest records `ROWS=1554359`, `MIN_DATE=20220409`,
`MAX_DATE=20220428`, and `TEST_ROWS=0`.  All logs have headers; the read-only
scan found `POST_CUTOFF_ROWS=0`.  `data/dev` is ignored by `.gitignore` and
does not appear in Git status.

The complete builder preserves source-file and source-row order without sorting
or deduplication; matching hashes bind this local handoff to B's approved
builder output.  The official split loader preserved the valid-file order
exactly (`VALID_ROW_ORDER_PRESERVED=true`).

## Preflight

`tools/preflight.py --data-dir data/dev --mode experiment --config
configs/candidates/bpr_fm.json` returned:

```text
ROWS=1266021
TEST_ROWS=0
MIN_DATE=20220409
MAX_DATE=20220428
LABEL_VALUES=[0, 1]
PREFLIGHT=PASS
```

The lower preflight row count is expected because the official runner reads
the two standard logs only; the complete manifest also retains the filtered
random log.

## Train-only same-user pair feasibility

Only train dates `20220408–20220421` were supplied to
`src.training.bpr.sample_same_user_pairs` with `seed=0` and
`negatives_per_positive=1`.  No training function was invoked.

```text
TRAIN_ROWS=1141112
POSITIVE_ROWS=384121
NEGATIVE_ROWS=756991
PAIR_COUNT=382579
ELIGIBLE_USERS=24290
TOTAL_USERS=26210
USER_COVERAGE=0.926745516978
ALL_POSITIVE_USERS=591
ALL_NEGATIVE_USERS=1329
SAME_USER_PAIR_CHECK=true
SAMPLING_SEED=0
NEGATIVES_PER_POSITIVE=1
```

`pair_count > 0`, `eligible_users > 0`, and `0 < user_coverage <= 1` hold.
Valid is reserved for later independent validation; no vocabularies, buckets,
or aggregate statistics were fitted on valid.  The existing feature registry
requires train-only fitting, and exp_001 remains loss-only with no new
features.

## Final contract checks

- `tests.test_build_dev_dataset`: PASS (2 tests)
- `tests.test_build_and_preflight`: PASS (4 tests)
- `tests.test_leakage_rules`: PASS (3 tests)
- `tests.test_official_rows`: PASS (1 test)
- Protected-file verification: `PROTECTED_FILES=PASS`

This report does not authorize a real validation run.  A must apply the full
stage gate and update approval state after B/D/E prerequisites are satisfied.
