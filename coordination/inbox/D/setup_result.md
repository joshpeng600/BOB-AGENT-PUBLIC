STATUS=SETUP_READY

BASE_MAIN_SHA=c6703454c2a0030c7bdb0ee6bf2af5a3019ca497

## Scope and setup constraints

- This was a setup interface audit only.
- Only synthetic matrices and synthetic same-user positive/negative rows were used.
- No real candidate or baseline training was run.
- No validation or test metric was used for model or hyperparameter selection.
- The approved `exp_001` hypothesis and hyperparameters were not changed.

## FM construction interface

Canonical entry: `src.models.FactorizationMachine`

```text
FactorizationMachine(
    feature_dim,
    embedding_dim=16,
    learning_rate=0.001,
    l2=1e-6,
    seed=0,
)
```

The read-only official `starter.baseline.FM` interface is
`FM(dim, k=16, lr=0.001, l2=1e-6, seed=0)` with `logits`, `step`, and `predict`.
The working implementation maps those semantics to canonical field names and exposes
`step`, `pairwise_step`, and `predict_scores`. The synthetic parity test confirms the
pointwise update matches the official FM. `predict_scores` returns one finite score per
input row and preserves input order.

## Objective APIs

- Pointwise BCE: `src.training.fit_pointwise`
- Same-user BPR: `src.training.bpr.fit_bpr_epoch`
- Pair sampler: `src.training.bpr.sample_same_user_pairs`

BPR samples positive and negative rows only within the same user, skips all-positive
and all-negative users, and uses `config.seed + epoch` for reproducible sampling and
batch order. No setup hyperparameter or experiment hypothesis was changed.

## Pair coverage fields

`PairCoverage` now exposes the required canonical fields:

- `pair_count`
- `eligible_users`
- `total_users`
- `user_coverage`

The pre-existing `pairs` name remains as a read-only compatibility alias so the B-owned
runner does not require a D-side interface change.

## Checkpoint contract

The pickle-free NPZ checkpoint saves:

- Model: `V`, `W`, `b`
- Adam/resume state: `mV`, `vV`, `mW`, `vW`, `t`
- JSON metadata: `format_version`, `model_class`, `feature_dim`, `embedding_dim`,
  `learning_rate`, `l2`, `config`, `epoch`, `best_metric`

`load_checkpoint` uses `numpy.load(..., allow_pickle=False)`. The synthetic restore test
confirms all parameters, all Adam state, `t`, metadata, and predictions are identical.

## Reproducibility test result

PASS. Fixed seeds reproduce FM initialization/update/prediction and same-user BPR pair
sampling. Prediction order and batch-size independence tests pass.

## B runner interface audit

PASS for the requested B interface review; no B-owned file was modified.

- Constructs `src.models.FactorizationMachine` directly; no runner FM factory is required.
- Uses canonical model fields `embedding_dim`, `learning_rate`, and `l2`, with runtime
  `feature_dim` and approved `seed`.
- Uses canonical training fields `seed`, `batch_size`, `epochs`, `patience`, and
  `max_batches`.
- Recursively rejects legacy `k`, `lr`, `batch`, and `max_epochs` fields.
- Routes `pointwise_binary_cross_entropy` to `src.training.fit_pointwise`.
- Routes `same_user_bpr` to `src.training.bpr.fit_bpr_epoch`.
- Resolves candidate and approved baseline paths from the approved experiment spec.
- Uses the validated experiment spec as the execution source of `experiment_id`.
- Does not install dependencies.
- Allows only `experiment`/`valid-only`, rejects a non-empty held-out split, and records
  `test_access=false`.
- Imports but does not modify the protected official evaluator.
- Runner setup tests use generated synthetic fixtures only.

## Modified files

- `src/training/bpr.py`
- `tests/training/test_bpr.py`
- `tests/training/test_checkpoint.py`
- `coordination/inbox/D/setup_result.md`

## Required test commands and results

The bundled workspace Python executable was used because `python` is not available on
this host PATH; it ran the same modules and arguments required by the setup contract.

```text
python -m unittest discover -s tests/models -v
PASS: 3/3

python -m unittest discover -s tests/training -v
PASS: 7/7

python -m unittest tests.test_run_experiment -v
PASS: 5/5

python -m unittest discover -s tests -v
PASS: 65/65

python tools/verify_protected_files.py --manifest protected_manifest.json --repo-root .
FAIL: raw SHA mismatch for starter/evaluate.py, starter/data.py, and starter/submit.py
on this Windows checkout.
```

The protected files have no Git diff, and the full repository tests (including normalized
LF/CRLF equivalence checks) pass. D did not modify, restore, or repin protected files.
GitHub PR #14 independently ran `verify-protected-files` on a clean checkout and passed,
along with the contracts, prediction-contract, and full tests checks. The remaining local
raw-hash difference is therefore recorded as a Windows checkout environment note, not a
D model/training readiness gap. D did not weaken or modify the verifier.

## Not yet verified

- A direct PASS from the standalone protected-file command on this Windows working tree;
  the corresponding GitHub required check passes on PR #14.
- Real KuaiRand data compatibility, pair coverage, runtime, and memory consumption.
- Any real baseline or candidate validation metric.
- Any test-set behavior or metric.

DATA_REQUIRED_FOR_SETUP=false

REAL_TRAINING_PERFORMED=false

test_access=false
