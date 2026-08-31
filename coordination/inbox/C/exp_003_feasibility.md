# exp_003 data, leakage, and parameter-memory feasibility review — C

STATUS=DATA_FEASIBILITY_PASS_WITH_CONFIG_IMPLEMENTATION_PENDING
ROLE=C
EXPERIMENT_ID=exp_003
REVIEWED_AGAINST_MAIN_SHA=35a5cb112a01ada67243e19362ebc504f4f67953
APPROVED_AGAINST_COMMIT_SHA=4b0bea90b688cc064ddb8f08e572acd448826c87
DATA_HASH=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
DATA_HASH_MATCH=true
DATA_AND_FEATURE_DEFINITIONS_UNCHANGED=true
BASELINE_EMBEDDING_DIM=16
CANDIDATE_EMBEDDING_DIM=32
FEATURE_DIM=40260
BASELINE_TRAINABLE_SCALARS=684421
CANDIDATE_TRAINABLE_SCALARS=1328581
TRAINABLE_SCALAR_DELTA=644160
BASELINE_PERSISTENT_STATE_BYTES=8213052
CANDIDATE_PERSISTENT_STATE_BYTES=15942972
PERSISTENT_STATE_DELTA_BYTES=7729920
PAIR_COUNT=382579
ELIGIBLE_USERS=24290
TOTAL_USERS=26210
USER_COVERAGE=0.926745516978
TRAIN_ONLY_FITTING=true
TRAIN_ONLY_PAIR_SAMPLING=true
VALID_ONLY_EVALUATION=true
VALID_ROWS=124909
MAXIMUM_DEVELOPMENT_DATE=20220428
TEST_ROWS=0
CANDIDATE_CONFIG_PRESENT_ON_REVIEWED_MAIN=false
TRAINING_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
REAL_VALID_RUN_AUTHORIZED_BY_C=false
PR25_EVIDENCE_USED=false
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=A

## Scope and conclusion

This is C's read-only feasibility review for the single approved scientific
change `model.embedding_dim: 16 -> 32`. No data, feature, model, training,
runner, evaluator, protected, approved-config, or governance file was changed.
No model was trained, no predictions or checkpoints were produced, no formal
metric was calculated, and no hidden-test data or label was accessed.

The proposed capacity change is data- and feature-compatible. It leaves the
encoded rows, five feature fields, feature dimension, same-user train pairs,
and validation row contract unchanged. For the current feature dimension of
40,260, doubling the embedding dimension adds 644,160 trainable `float32`
values. The exact initialized model/optimizer state grows by 7,729,920 bytes
(7.37 MiB). This deterministic increase is feasible as a setup matter, but C
does not certify full-run wall time or peak memory and does not open a formal
run gate.

## Frozen data and unchanged feature contract

The authorized private development snapshot was inspected read-only at its
fixed local path. The SHA-256 of `dataset_manifest.json` is
`69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`,
exactly matching the exp_003 specification. Its six payload hashes also match
the accepted exp_001/exp_002 C evidence:

| File | SHA-256 |
| --- | --- |
| `log_random_4_22_to_5_08_pure.csv` | `ba0a5f106467848d90b28fc5015a2df7076bc108959abf1960595bce4cff492e` |
| `log_standard_4_08_to_4_21_pure.csv` | `5bb6eb0b3d9f47e5436cb5dc82ee1899b845ebf9750a5560b801e929e18bd41c` |
| `log_standard_4_22_to_5_08_pure.csv` | `60a464f485b39ee4edd954606ceb63e1d3dd006f81a0fa5e8da8f0aafa8cd2a8` |
| `user_features_pure.csv` | `dc729a656301b4c6d07f713fe41d05ec9bfaab670b90e531c70037caf033c011` |
| `video_features_basic_pure.csv` | `a6f7ee02684c5777422306cdc416e170302288aa89aca9dfea995edbd625bcc2` |
| `video_features_statistic_pure.csv` | `d5c9e237ef2c6c1fc0e7f27e952f215d6626ecd934b01a6c53ecfcc72540f6b6` |

The Git diff from the accepted exp_001 producing commit
`44fd36aa9b35b7fc9c01389e6dd453e972f16635` through reviewed main is empty for
`starter/data.py`, `src/data/`, and `configs/candidates/bpr_fm.json`. The
approved exp_003 contract is hyperparameter-only and forbids new features or
data/model/training source changes. The encoded contract therefore remains
five fields (`user_id`, `video_id`, `author_id`, `tab`, and train-derived
`dur_bucket`) with a train-derived feature dimension of 40,260.

The D-owned file `configs/candidates/bpr_fm_dim32.json` is not present on this
reviewed main. That is expected during asynchronous setup. A/B must verify
after D's PR merges that its only scientific difference from
`configs/approved/exp_001.json` is `model.embedding_dim: 16 -> 32` before any
later run authorization.

## Leakage review

- `starter.data.load` applies the fixed date windows: train through 20220421,
  validation from 20220422 through 20220428, and the protected later split
  from 20220429. The frozen development snapshot ends at 20220428 and produces
  zero later-split rows.
- `starter.data.encode` derives duration quantiles and every categorical
  vocabulary only from `splits["train"]`; validation values are only transformed
  with the frozen train mappings and unknown slots.
- `tools/run_experiment.py` builds the model from that train-derived feature
  dimension and passes only `X_train`, `y_train`, and `users_train` into the BPR
  trainer. Same-user pairs are sampled only from training labels. Validation is
  used only by the official validation evaluation route.
- Read-only encoding confirmed 1,141,112 train rows, 124,909 validation rows,
  382,579 seed-0 train pairs, 24,290 eligible users, 26,210 total users, and
  coverage 0.926745516978. These values match the accepted exp_001/exp_002 C
  evidence, so the embedding-only proposal does not alter data eligibility or
  sampling.

No leakage was found in the approved path. This review does not use or accept
quarantined PR #25 evidence.

## Parameter-memory estimate

The FM has an embedding matrix `V[feature_dim, embedding_dim]`, linear weights
`W[feature_dim]`, and one scalar bias. With `feature_dim=40,260`, exact counts
are:

| Quantity | dim 16 baseline | dim 32 candidate | Increase |
| --- | ---: | ---: | ---: |
| Trainable scalars (`V`, `W`, bias) | 684,421 | 1,328,581 | 644,160 |
| Trainable `float32` parameter bytes | 2,737,684 | 5,314,324 | 2,576,640 (2.46 MiB) |
| Persistent state bytes from `state_dict()` | 8,213,052 | 15,942,972 | 7,729,920 (7.37 MiB) |

Persistent state includes parameters plus Adam first/second moments for `V`
and `W` and the scalar step state. The pair indexes, encoded matrices, batch
size (8,192), epoch/patience budget, and row counts are unchanged. Batch
embedding temporaries scale with the dimension, so peak runtime memory will be
higher than the persistent-state delta; exact peak memory remains for B's
later bounded runtime checks. C performed initialization and byte accounting
only, not a training step.

## Commands and results

Every Python command used the repository's required virtual-environment
interpreter.

| Check | Result |
| --- | --- |
| `tools/validate_contract.py --type experiment-spec --path experiments/exp_003.json` | `CONTRACT=PASS` |
| `scripts/check_repository_contracts.py` | PASS; 52 JSON files plus JSONL/TOML validated |
| `tools/verify_protected_files.py --manifest protected_manifest.json --repo-root .` | `PROTECTED_FILES=PASS` |
| `tools/preflight.py --data-dir <LOCAL_DEV> --mode experiment --config configs/approved/exp_001.json` | `PREFLIGHT=PASS`; 1,266,021 rows; maximum date 20220428; zero later-split rows |
| Read-only manifest and six payload SHA-256 checks | PASS; all hashes exactly match frozen evidence |
| Read-only official encode and same-user sampler inspection | PASS; feature dimension 40,260 and unchanged seed-0 coverage |
| Read-only FM initialization/state byte accounting at dimensions 16 and 32 | PASS; persistent-state delta 7,729,920 bytes |
| Git identity check from accepted exp_001 producing commit | PASS; no diff in data/feature definitions or champion source candidate |

## Remaining gates

C's read-only setup review passes, but `REAL_VALID_RUN_ALLOWED` remains
blocked. D's config-only candidate must merge; B must then verify the exact
one-field diff and perform only the separately allowed synthetic preflight;
E must independently pre-review the integrated setup; and A must review every
merged prerequisite before recording any exact valid-only authorization.
Hidden-test access and final approval remain forbidden.
