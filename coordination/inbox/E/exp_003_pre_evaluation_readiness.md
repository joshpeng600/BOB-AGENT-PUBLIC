# exp_003 independent pre-evaluation readiness review — E

STATUS=PRE_EVALUATION_READY
ROLE=E
PHASE=PRE_EVALUATION_REVIEW
REVIEWED_AT_UTC=2026-08-31T13:00:38Z
REVIEWED_MAIN_SHA=d3951cde8dee6478729c143cc9a66964827cba4b
APPROVED_AGAINST_COMMIT_SHA=0b0ab600d835c32c2bfa49c74863048b66e5bd5a
C_PR=13
C_MERGE_COMMIT_SHA=5444bcdc24ad1d587b7dbcfe375b90d3f238ddd6
C_SOURCE_COMMIT_SHA=ccaa4a670ca853e4e96f9c383f12679164605611
D_PR=15
D_MERGE_COMMIT_SHA=1dc25ed52430df9291f74697c843e1d7d9eb81e0
D_IMPLEMENTATION_COMMIT_SHA=76c7f2ec2ae3867ed33b66f2209090edded0b60a
D_READINESS_COMMIT_SHA=7575140a1d5c5cb7ead5c0e767177087a2052dce
B_PR=17
B_MERGE_COMMIT_SHA=0b0ab600d835c32c2bfa49c74863048b66e5bd5a
B_PRODUCING_COMMIT_SHA=b0abb6215186d53bc54f7baa8761f2e515ff6b4d
B_EVIDENCE_COMMIT_SHA=a3ec225ecd82bbc96fdad68b776da666b540304d
A_ROUTING_PR=18
A_ROUTING_MERGE_COMMIT_SHA=d3951cde8dee6478729c143cc9a66964827cba4b
EXPERIMENT_SPEC_HASH=79c0e54f962c84213c0150474894ff695d5d6acfed85aa2955abb173b425f20c
BASELINE_CONFIG_HASH=5221e0efdaace6f0aaa196da3cfdf51a4fdb154cf3043cd6b71252a62cf0823c
CANDIDATE_CONFIG_HASH=e185476e13a0976ac227e84c486bd798ce0e6ae8753f98ead4d48a24036ac1a2
DATA_HASH_DECLARED_BY_C=69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002
DATA_HASH_REAUDITED_BY_E=false
SCIENTIFIC_DIFF=model.embedding_dim:16->32
BASELINE_MODEL=factorization_machine
BASELINE_EMBEDDING_DIM=16
CANDIDATE_MODEL=factorization_machine
CANDIDATE_EMBEDDING_DIM=32
ROUTE_AND_CONFIG_FAIL_CLOSED=PASS
FULL_BUDGET_BINDING=PASS
SYNTHETIC_FORMAL_ISOLATION=PASS
IMMUTABLE_PREDICTION_INGRESS=PASS
VALID_ONLY_AND_TEST_ISOLATION=PASS
REAL_VALID_RUN_ALLOWED=false
FORMAL_B_PACKAGES_AVAILABLE=false
FORMAL_EVALUATION_PERFORMED=false
FORMAL_METRICS_PRODUCED=false
PR25_EVIDENCE_READ=false
PR25_EVIDENCE_USED=false
PREDICTIONS_MODIFIED=false
TRAINING_PERFORMED=false
FINAL_APPROVAL_CREATED=false
test_access=false
NEXT_RECEIVER=A

## Scope and conclusion

This is E's independent exp_003 pre-evaluation review of the merged repository
at the exact clean `origin/main` commit above. It reviews merged setup evidence,
repository route binding, audit behavior, and evaluation ingress only. E did
not read or hash the private development dataset, train a model, inspect B's
private synthetic package, consume or score a formal prediction, calculate or
report a formal metric, modify a prediction, create a final approval, access
test, or read or use the quarantined PR #25 evidence.

The merged C, D, B, and A routing evidence is sufficient for this setup stage.
The approved exp_001 same-user BPR champion is bound as the baseline. An
independent recursive comparison of every scientific configuration field found
exactly one candidate difference: `model.embedding_dim: 16 -> 32`. Model
family, learning rate, L2, objective, sampling rules, seed, batch size, epochs,
patience, full `max_batches=null` budget, data mode, allowed splits, development
cutoff, and evaluation split are unchanged.

This readiness does not open a formal run or evaluation gate.
`REAL_VALID_RUN_ALLOWED` remains false, no formal B packages are available,
and no exp_003 formal metric exists. A must separately review this merged E
record and bind any later valid-only authorization to an exact clean full SHA
before B may use the private development data.

## Merged setup evidence reviewed

- C: `coordination/inbox/C/exp_003_feasibility.md`, source commit
  `ccaa4a670ca853e4e96f9c383f12679164605611`, merged by PR #13. It declares
  unchanged data/features, development manifest hash
  `69e5a6f656356832f7e1fa6a9774bc404030f32874e18e57e0f38b6a309a1002`,
  train-only fitting and pair sampling, valid-only evaluation, maximum
  development date 20220428, zero later-split rows, and no test access. E did
  not independently access or hash the local dataset.
- D: `configs/candidates/bpr_fm_dim32.json` and
  `coordination/inbox/D/exp_003_setup_readiness.md`, implementation commit
  `76c7f2ec2ae3867ed33b66f2209090edded0b60a`, merged by PR #15. E independently
  hashed the merged spec/config bytes and verified the exact one-field
  scientific diff.
- B: `coordination/inbox/B/exp_003_setup_readiness.md`, evidence commit
  `a3ec225ecd82bbc96fdad68b776da666b540304d`, merged by PR #17. Its one-batch
  package is explicitly synthetic-only and remained outside Git. E did not
  inspect or accept that package as formal evidence.
- A: `coordination/inbox/A/exp_003_b_setup_integration_20260831.md`, merged by
  PR #18. It routes only the integrated setup to E and explicitly keeps real
  training, formal metrics, test access, and final approval closed.

All cited source and merge commits are ancestors of the reviewed main commit.

## Independent fail-closed findings

- Route and config binding: the exp_003 spec resolves the baseline only to
  `configs/approved/exp_001.json` and the candidate only to
  `configs/candidates/bpr_fm_dim32.json`. Both actual routes passed the
  repository route validator using their raw byte hashes and rebuilt resolved
  configurations.
- Full budget: formal `max_batches` must exactly equal the approved config's
  `null` value. Any CLI truncation or resolved-config drift is rejected before
  formal evidence can complete.
- Evidence tier: a bounded smoke must identify itself as `synthetic_smoke` and
  `synthetic_only`; the independent auditor accepts only completed formal
  evidence. Synthetic setup output cannot become formal audit or metric
  evidence.
- Artifact ingress: completed packages must bind the spec, config bytes,
  resolved config, prediction, checkpoint, and complete artifact inventory.
  Missing, replaced, tampered, symlinked, duplicate, traversal, or semantically
  drifted inputs fail closed.
- Immutable evaluation: `safe_evaluate` snapshots one no-follow ordinary-file
  handle into a private read-only copy, rechecks the source identity and bytes,
  denies existing or replacement outputs, and removes its own publication if
  a post-publication hash or Git check fails.
- Split isolation: runner, completed-manifest, prediction-validation, and safe
  evaluation contracts are valid-only. The hidden-test scoring route remains
  permanently disabled in ordinary evaluation.
- Protected evaluator: all seven protected files match their pinned hashes,
  including `starter/evaluate.py`.

## Independent verification results

Every Python command used
`/Users/pengrenzhong/Documents/GitHub/BOB-AGENT/.venv/bin/python`.

- Structured scientific config comparison: PASS, exactly
  `model.embedding_dim: 16 -> 32`.
- Actual exp_003 baseline and candidate route validation: PASS for both routes.
- Focused runner/audit/safe-evaluate/prediction/security suite: PASS, 80/80
  synthetic tests.
- Required repository unit suite: PASS, 175/175 tests.
- `scripts/check_repository_contracts.py`: PASS, 53 JSON files plus JSONL/TOML.
- `scripts/check_protected_files.py`: PASS, all seven protected files.
- `tools/verify_protected_files.py --manifest protected_manifest.json
  --repo-root .`: PASS.
- `scripts/check_prediction_contract.py`: PASS, 9/9 synthetic tests.
- `tools/validate_contract.py --type experiment-spec --path
  experiments/exp_003.json`: PASS.
- Source/merge ancestry checks, `git diff --check`, `git diff -- starter/`, and
  the pre-write `git status --porcelain`: PASS/empty.

All test fixtures were synthetic. No formal score or generated run artifact was
created or published by E.

## Remaining formal gate

Before E can evaluate exp_003, A must merge this readiness and record a later
exact full-SHA authorization. B must then supply baseline and candidate formal
valid-only packages from the same clean producing commit, development-data
hash, feature set, seed, and full training budget. Each package must pass the
protected-file, manifest, artifact-byte, route, resolved-config, prediction,
and audit contracts. E will reject rather than repair any missing, mutable,
mismatched, synthetic-only, dirty, timed-out, irreproducible, or unauthorized
package.
