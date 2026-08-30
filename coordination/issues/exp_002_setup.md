# Plan exp_002: two same-user negatives per positive

## Decision

Start asynchronous implementation setup for `exp_002`. The accepted `exp_001` Same-user BPR configuration remains the baseline. The only scientific variable is `objective.negatives_per_positive: 1 -> 2`.

## Hypothesis

Two same-user negatives per positive may reduce the variance of the BPR objective estimate and improve within-user validation ranking without changing the FM model, features, seed, evaluator, or training budget.

A failure remains informative: it would rule out additional BPR negative exposure as a sufficient mechanism at the current capacity and budget, favoring a later listwise or strictly time-safe sequential-interest proposal.

## Fixed controls

- Baseline: `configs/approved/exp_001.json`
- Baseline primary: `0.603871007132627`
- Strict success rule: `candidate_primary - baseline_primary > 0.002`
- Candidate primary must be strictly greater than `0.605871007132627`
- Seed: `0`
- Data mode: `train_valid_only`
- Maximum development date: `20220428`
- Synthetic smoke limit: one batch
- Formal time budget: 3600 seconds
- Test access: forbidden

## Async setup

- B: generalize the baseline objective route contract and run contract/unit checks plus at most one one-batch synthetic smoke.
- C: read-only unchanged-data and doubled-pair feasibility review.
- D: add only `configs/candidates/bpr_fm_neg2.json`; no model/training source changes.
- E: wait for merged B/D evidence, then perform contract-only pre-evaluation review.

No real-data training or formal metrics are authorized by this issue. A must later review merged B/C/D/E evidence and create a separate exact gate before any valid-only run.

PR #25 and all of its metrics and artifacts remain permanently excluded. Test remains forbidden.
