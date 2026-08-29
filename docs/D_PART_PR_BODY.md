# D: model and training contracts

## Scope

- Add a reproducible NumPy Factorization Machine with `step`, `pairwise_step`, and order-preserving `predict_scores`.
- Add a resolved training configuration supporting seed, batch size, epochs, patience, and smoke-test batch limits.
- Add pointwise training with validation-only model selection and complete optimizer checkpoints.
- Add a minimal same-user BPR candidate without claiming a metric improvement.

## BPR definition and risk

The candidate minimizes `mean(-log(sigmoid(score_positive-score_negative)))`.
Each positive and sampled negative must belong to the same user. All-positive and
all-negative users are skipped. Runs must record pair count, eligible users, total
users, and eligible-user coverage. Uniform sampling may overweight users with many
positives, and alignment with nDCG@5 remains unverified.

## Tests

- Working FM pointwise update matches the official FM.
- Prediction row count and order are stable across batch sizes.
- Fixed seeds reproduce initialization, training, and pair sampling.
- Checkpoints restore model parameters, Adam state, step, and predictions.
- BPR increases a controlled positive-negative score gap.
- Missing valid pairs fail with a readable error.

## Resource estimate

The implementation depends only on NumPy. `max_batches=5` is the required smoke
mode. Exact wall time and peak memory depend on the encoded feature dimension and
pair count and must be measured by B on the target machine rather than guessed by D.

## Handoff contract for B

- Model: `src.models.FactorizationMachine`
- Pointwise trainer: `src.training.fit_pointwise`
- BPR epoch: `src.training.bpr.fit_bpr_epoch`
- Pointwise config: `configs/candidates/pointwise_fm.json`
- BPR candidate: `configs/candidates/bpr_fm.json`
- Output: exactly one finite score per input row, preserving input order
- Checkpoint: pickle-free NPZ containing parameters, complete Adam state, step,
  resolved config, epoch, and best validation metric

B owns the valid-only runner, execution manifest, measured resource use, and
prediction artifact. E alone confirms validation metrics. No test score is used.
