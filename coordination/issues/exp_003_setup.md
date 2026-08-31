# Plan exp_003: increase FM embedding dimension to 32

## Decision

Start asynchronous implementation setup for `exp_003`. The accepted `exp_001`
same-user BPR configuration remains the baseline. The only scientific variable
is `model.embedding_dim: 16 -> 32`.

## Fixed controls

- Baseline: `configs/approved/exp_001.json`
- Baseline primary: `0.603871007132627`
- Strict success rule: `candidate_primary - baseline_primary > 0.002`
- Candidate primary must be strictly greater than `0.605871007132627`
- Seed: `0`
- Data mode: `train_valid_only`
- Maximum development date: `20220428`
- Frozen development-manifest SHA-256: `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`
- Synthetic smoke limit: one batch
- Formal time budget: 3600 seconds
- Test access: forbidden

## Async setup

- C and D act first and return separate merged evidence.
- B waits for merged C/D evidence, then performs contract preflight and only a
  bounded synthetic smoke.
- E waits for merged B/C/D evidence, then performs an independent setup review
  without scoring.
- A must review every merged prerequisite before opening any valid-only gate.

No real-data training, formal metrics, final approval, or test access is
authorized by this issue. Quarantined evidence is excluded.
