# exp_002 data and feature feasibility review — C

STATUS=DATA_FEASIBILITY_PASS_WITH_IMPLEMENTATION_PENDING
ROLE=C
EXPERIMENT_ID=exp_002
BASE_MAIN_SHA=5e97be077b248db587b64c067a86fb1a1cc35d81
APPROVED_AGAINST_COMMIT_SHA=8eb5bad5d1ce24ee8d68451dddd45a10414119c5
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
DATA_HASH_MATCH=true
DATA_AND_FEATURE_DEFINITIONS_UNCHANGED=true
BASELINE_NEGATIVES_PER_POSITIVE=1
CANDIDATE_NEGATIVES_PER_POSITIVE=2
BASELINE_PAIR_COUNT=382579
CANDIDATE_PAIR_COUNT=765158
PAIR_COUNT_MULTIPLIER=2.0
ELIGIBLE_USERS=24290
TOTAL_USERS=26210
USER_COVERAGE=0.926745516978
SAME_USER_PAIR_CHECK=true
BASELINE_BATCHES_PER_EPOCH=47
CANDIDATE_BATCHES_PER_EPOCH=94
BATCH_COUNT_MULTIPLIER=2.0
BASELINE_PAIR_INDEX_BYTES=6121264
CANDIDATE_PAIR_INDEX_BYTES=12242528
PAIR_INDEX_MEMORY_DELTA_BYTES=6121264
TRAIN_ONLY_FITTING=true
TRAIN_ONLY_PAIR_SAMPLING=true
VALID_ROW_ORDER_PRESERVED=true
VALID_ROWS=124909
MAXIMUM_DEVELOPMENT_DATE=20220428
TEST_ROWS=0
CANDIDATE_CONFIG_PRESENT_ON_BASE_MAIN=false
TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
REAL_VALID_RUN_AUTHORIZED_BY_C=false
test_access=false
NEXT_RECEIVER=A

## Scope and conclusion

This is C's read-only feasibility review for the single approved scientific
change `objective.negatives_per_positive: 1 -> 2`. No data, feature, model,
training, runner, evaluator, or governance file was changed. No model was
trained, no predictions were produced, no formal metric was calculated, and
no held-out test data was accessed.

The proposed change is feasible with the current development data and
same-user sampler. On the unchanged official train split, increasing the
number of sampled negatives from one to two exactly doubles the sampled pair
count from 382,579 to 765,158 while preserving the same 24,290 eligible users,
26,210 total users, and same-user pairing rule.

## Data and feature identity

The local Git-ignored development snapshot was checked read-only. Its
`dataset_manifest.json` SHA-256 is
`69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`,
which exactly matches the accepted exp_001 C evidence and the exp_002 A
handoff. The six payload hashes also match the accepted exp_001 evidence:

| File | SHA-256 |
| --- | --- |
| `log_random_4_22_to_5_08_pure.csv` | `ba0a5f106467848d90b28fc5015a2df7076bc108959abf1960595bce4cff492e` |
| `log_standard_4_08_to_4_21_pure.csv` | `5bb6eb0b3d9f47e5436cb5dc82ee1899b845ebf9750a5560b801e929e18bd41c` |
| `log_standard_4_22_to_5_08_pure.csv` | `60a464f485b39ee4edd954606ceb63e1d3dd006f81a0fa5e8da8f0aafa8cd2a8` |
| `user_features_pure.csv` | `dc729a656301b4c6d07f713fe41d05ec9bfaab670b90e531c70037caf033c011` |
| `video_features_basic_pure.csv` | `a6f7ee02684c5777422306cdc416e170302288aa89aca9dfea995edbd625bcc2` |
| `video_features_statistic_pure.csv` | `d5c9e237ef2c6c1fc0e7f27e952f215d6626ecd934b01a6c53ecfcc72540f6b6` |

The Git diff from the accepted exp_001 producing commit
`44fd36aa9b35b7fc9c01389e6dd453e972f16635` through this review base is empty
for `starter/data.py`, `src/data/`, and `configs/candidates/bpr_fm.json`.
The exp_002 contract is `hyperparameter_only`, forbids new features, and
forbids model/training source changes. Therefore the data and feature
definitions are unchanged from the accepted champion.

The D-owned file `configs/candidates/bpr_fm_neg2.json` is not yet present on
this base main. This is expected during parallel setup, but A/B must verify
after D's implementation merges that its only scientific difference from the
approved champion is `negatives_per_positive: 1 -> 2` before any later formal
run can be authorized.

## Leakage and row-order checks

- `starter.data.encode` derives duration bucket edges and every categorical
  vocabulary only from `splits["train"]`, then applies them to other splits.
- `tools/run_experiment.py` passes only `users_train` and `y_train` to
  `sample_same_user_pairs`; valid labels are not used for fitting or sampling.
- The sampler groups rows by user and draws negatives only from the same
  user's negative train rows, with replacement. Duplicate sampled negatives
  are permitted and do not change row identity.
- A direct ordered comparison of the official valid CSV rows against
  `starter.data.load(...)["valid"]` passed for all 124,909 rows. No sorting or
  deduplication was observed.
- Preflight reported 1,266,021 official standard-log rows, maximum date
  20220428, both binary labels, and zero test rows.

## Pair count, memory, and runtime estimate

The exact train-only sampling results at seed 0 are:

| Quantity | exp_001 baseline | exp_002 candidate | Effect |
| --- | ---: | ---: | ---: |
| Sampled pairs | 382,579 | 765,158 | 2.0x |
| Batches per epoch at batch size 8192 | 47 | 94 | 2.0x |
| Positive + negative `int64` index arrays | 6,121,264 bytes (5.84 MiB) | 12,242,528 bytes (11.68 MiB) | +5.84 MiB |
| Maximum batches across 40 epochs before early stopping | 1,880 | 3,760 | 2.0x |

The model parameters, encoded feature matrix, feature dimension, and per-batch
tensor shapes are unchanged. Thus the deterministic persistent increase is
the additional 5.84 MiB of pair-index arrays; temporary Python sampling lists
also scale with the number of sampled indexes. Because the batch size remains
8192, peak per-batch model memory should remain approximately unchanged.

Training work for the pairwise update approximately doubles because the batch
count doubles. End-to-end wall time is not guaranteed to be exactly 2x because
data loading and validation are fixed costs and early stopping may select a
different epoch. The 3600-second formal limit therefore remains a real B/A
gate consideration; C has not run training and does not certify a full-run
duration. A bounded synthetic smoke is the next permitted runtime check after
B and D implementation is integrated.

## Commands and results

| Check | Result |
| --- | --- |
| `python tools/validate_contract.py --type experiment-spec --path experiments/exp_002.json` | `CONTRACT=PASS` |
| `python scripts/check_repository_contracts.py` | PASS; 38 JSON files plus JSONL/TOML validated |
| `python tools/verify_protected_files.py --manifest protected_manifest.json --repo-root .` | `PROTECTED_FILES=PASS` |
| `python tools/preflight.py --data-dir <LOCAL_DEV> --mode experiment --config configs/approved/exp_001.json` | `PREFLIGHT=PASS`; rows 1,266,021; max date 20220428; test rows 0 |
| C data/leakage/official-row/BPR unit-test subset | PASS; 14/14 tests |
| Read-only official valid row-order comparison | PASS; 124,909/124,909 rows preserved |
| Read-only same-user sampling at seed 0 with one and two negatives | PASS; 382,579 and 765,158 pairs respectively |

## Remaining gates and blockers

C's data and feature feasibility review passes. This does not open the formal
run gate. `REAL_VALID_RUN_ALLOWED` remains blocked until at least:

1. B's baseline-route contract generalization is merged and passes its
   fail-closed regressions.
2. D's candidate config is merged and verified as the one-field approved
   scientific change.
3. B's bounded synthetic smoke records the resolved value 2 and runtime
   operability without formal evidence.
4. E completes the integrated valid-only pre-evaluation review.
5. A records a separate exact full-SHA formal valid-run authorization.

Test evaluation remains forbidden and requires a separate human-approved
release-only gate.
