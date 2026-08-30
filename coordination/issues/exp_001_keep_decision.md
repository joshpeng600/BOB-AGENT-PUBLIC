# Issue draft: accept exp_001 same-user BPR validation improvement

## Decision

`KEEP` — promote the reviewed `exp_001` same-user BPR configuration to `configs/approved/exp_001.json`.

## Evidence

- Producing clean commit: `44fd36aa9b35b7fc9c01389e6dd453e972f16635`
- Data hash: `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`
- Unique research variable: pointwise binary cross-entropy → same-user BPR
- Baseline primary: `0.601468756352959`
- Candidate primary: `0.603871007132627`
- Delta: `0.0024022507796679`
- Required rule: strict delta `> 0.002`
- Candidate absolute threshold: strict primary `> 0.6036`
- Same commit, data, FM features, seed `0`, and full training budget
- E artifact audit, immutable prediction evaluation, and 124,909-row alignment: PASS
- Authorized formal attempt consumed; no additional run is authorized
- PR #25 evidence used: false
- Test access: false

## Process disclosure

The repository owner accepted the fresh result with permanent disclosure after the coordinating session opened quarantined PR #25 metrics only after both fresh runs and prediction hashes were frozen. That session was excluded from scoring; an isolated E evaluator did not read or use PR #25. The old evidence remains permanently quarantined.

## Follow-up

- Record `exp_001` as the current validation champion.
- Reset consecutive non-improvement count to `0`.
- Do not start another formal run automatically.
- A may later prepare a separate single-variable experiment proposal.
- Final test/release remains blocked unless the repository owner gives a new exact approval bound to a clean release commit.
