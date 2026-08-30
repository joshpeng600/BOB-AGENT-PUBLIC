# exp_002 independent pre-evaluation readiness review — E

STATUS=PRE_EVALUATION_READY
ROLE=E
PHASE=PRE_EVALUATION_REVIEW
REVIEWED_AT_UTC=2026-08-30T20:32:29Z
REVIEWED_MAIN_SHA=8d4a03c0c507d03321e51a1190b6038abe13ac0a
C_PR=45
C_MERGE_COMMIT_SHA=c5280a1b434f314420e7add028a67414166803f6
C_SOURCE_COMMIT_SHA=ad44dd81a54555d212eec827c49d4bc7455701cc
D_PR=46
D_MERGE_COMMIT_SHA=7bf6cdc188d952a56563a06662ffbbe9b1d4c720
D_IMPLEMENTATION_COMMIT_SHA=77e577675b9d6a04a56321ee0aab0d437d98dacf
B_PR=47
B_MERGE_COMMIT_SHA=8d4a03c0c507d03321e51a1190b6038abe13ac0a
B_IMPLEMENTATION_COMMIT_SHA=ce07ca636676e794d86641d2dede5bd840724f98
EXPERIMENT_SPEC_HASH=c3d1257751d2abf15d62a0638679efe892cc13a8ff3325630ab2acbbece5c8c9
BASELINE_CONFIG_HASH=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
CANDIDATE_CONFIG_HASH=4ae653c2a68c1dc461ff2149540920e009355637e22e557b70c68e41460d2b61
DATA_HASH_DECLARED_BY_C=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
DATA_HASH_REAUDITED_BY_E=false
SCIENTIFIC_DIFF=objective.negatives_per_positive:1->2
BASELINE_OBJECTIVE=same_user_bpr
BASELINE_NEGATIVES_PER_POSITIVE=1
CANDIDATE_OBJECTIVE=same_user_bpr
CANDIDATE_NEGATIVES_PER_POSITIVE=2
ROUTE_AND_CONFIG_FAIL_CLOSED=PASS
SYNTHETIC_FORMAL_ISOLATION=PASS
IMMUTABLE_PREDICTION_INGRESS=PASS
REAL_VALID_RUN_ALLOWED=false
FORMAL_B_PACKAGES_AVAILABLE=false
FORMAL_EVALUATION_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
PR25_EVIDENCE_READ=false
PR25_EVIDENCE_USED=false
PREDICTIONS_MODIFIED=false
TRAINING_PERFORMED=false
test_access=false
NEXT_RECEIVER=A

## Scope and conclusion

This is E's independent exp_002 pre-evaluation review of the merged repository
at the exact clean `origin/main` commit above. It reviews contracts, route
binding, audit behavior, and evaluation ingress only. E did not train a model,
read development data, consume or score a formal B prediction, calculate or
report a formal metric, modify any prediction, create a final approval, access
test, or read or use the isolated PR #25 evidence.

The integrated C, delegated D, and B setup evidence is sufficient for this
pre-evaluation stage. The approved exp_001 BPR champion is bound as the exp_002
baseline, and a structured comparison of all scientific configuration fields
found exactly one difference in the candidate:
`objective.negatives_per_positive: 1 -> 2`. Model, objective formula, skip
rules, training budget, seed, data mode, allowed splits, maximum development
date, and evaluation split are unchanged.

This readiness does not open a formal run or evaluation gate.
`REAL_VALID_RUN_ALLOWED` remains false, no formal B packages exist for E to
audit, and no formal metrics exist for exp_002. A separate exact authorization
is required before B may produce one fresh full-budget valid-only pair.

## Merged readiness evidence reviewed

- C: `coordination/inbox/C/exp_002_feasibility.md`, merged by PR #45. It
  declares unchanged data/features, development-data hash
  `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`,
  train-only fitting and same-user sampling, valid row-order preservation,
  maximum development date 20220428, and no test access. E did not read or
  independently hash the local development dataset in this pre-review.
- D delivery: `configs/candidates/bpr_fm_neg2.json` and
  `coordination/inbox/D/exp_002_setup_readiness.md`, merged by PR #46 under the
  recorded one-time A-for-D config-only authorization. E does not treat it as
  independent D review; E independently verified the resulting config bytes
  and scientific diff on main.
- B: `coordination/inbox/B/exp_002_setup_readiness.md` and the route/audit
  implementation merged by PR #47. The B implementation commit is an ancestor
  of reviewed main. The three raw SHA-256 values recorded by B for the spec,
  baseline config, and candidate config exactly match E's independent hashes.

## Independent security findings

- Baseline route: `experiments/exp_002.json` binds
  `configs/approved/exp_001.json`; the runner derives its expected baseline
  objective from that approved config. On reviewed main this resolves to
  `same_user_bpr` with exactly one negative per positive.
- Candidate route: the spec binds `configs/candidates/bpr_fm_neg2.json`, which
  resolves to `same_user_bpr` with exactly two negatives per positive.
- Route fail-closed behavior: baseline/candidate path swaps, candidate use of
  an approved baseline config, forged route identity, forged objective, seed or
  mode, raw spec/config byte drift, and rebuilt/resolved config drift are
  rejected. Config and spec hashes bind raw repository bytes; canonical
  `config_hash` binds the fully resolved config.
- Budget and evidence tier: formal `max_batches` must exactly equal the
  approved config value. Synthetic smoke requires `status=synthetic_smoke`,
  `evidence_tier=synthetic_only`, and a positive bound. The formal auditor
  rejects non-completed evidence, so synthetic manifests cannot become formal
  audit or metric evidence. E did not accept B's uncommitted synthetic outputs
  as formal artifacts.
- Split isolation: runner and completed-manifest contracts require
  `mode=valid-only`; ordinary prediction validation denies non-valid splits.
  Test scoring remains gated by a separate exact human final approval.
- Immutable evaluation ingress: `safe_evaluate` still snapshots one no-follow
  ordinary-file handle into a private read-only copy, binds source identity and
  hashes before and after evaluation, refuses overwrite/existing-output races,
  rechecks published evidence and Git state, and removes its own published
  evidence if a post-publication check fails.
- Protected evaluator: all seven protected files match their pinned hashes,
  including `starter/evaluate.py`.

## Independent verification results

- `python -m pytest -q -p no:cacheprovider`: PASS, 121 passed, 4 skipped, 39
  subtests passed.
- `python -m unittest discover -s tests -v`: PASS, 125 passed, 4 skipped.
- Focused runner/audit/safe-evaluate/prediction suite: PASS, 75 passed, 4
  skipped. It includes the exp_002 BPR baseline binding, exact candidate
  negatives=2, route/objective/config forgery rejection, synthetic/formal
  separation, valid-only denial, and immutable prediction replacement/race
  checks.
- The four skips are Windows symlink-creation privilege skips. The ordinary
  file, replacement, traversal, race, inode, hash, and post-publication
  fail-closed checks passed.
- `python scripts/check_repository_contracts.py`: PASS, 40 JSON files plus
  JSONL/TOML validated.
- `python scripts/check_protected_files.py`: PASS, all seven protected files.
- `python tools/verify_protected_files.py --manifest protected_manifest.json
  --repo-root .`: PASS.
- `python scripts/check_prediction_contract.py`: PASS, 9/9.
- `python tools/validate_contract.py --type experiment-spec --path
  experiments/exp_002.json`: PASS.
- `git diff --check`, `git diff -- starter/`, and final
  `git status --porcelain`: PASS/empty before this E-owned evidence write.

## Remaining formal gate

Before E can evaluate exp_002, A must record a later exact full-SHA
authorization and B must supply both immutable formal valid-only packages from
the same clean producing commit, data hash, feature set, seed, and full budget.
Each package must pass the protected-file, manifest, artifact-byte, route,
resolved-config, prediction, and audit contracts. E will reject rather than
repair any missing, mutable, mismatched, synthetic-only, dirty, timed-out, or
irreproducible package.
