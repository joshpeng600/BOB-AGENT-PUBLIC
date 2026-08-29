# Track 2 repository operating rules

This repository is a five-member, five-agent workspace. The bootstrap phase builds a safe and reproducible experiment system; it does not authorize new-model research.

## Fixed task contract

- Task: rank items within each user.
- Label: `long_view`.
- Metrics: GAUC and nDCG@5.
- Primary metric: arithmetic mean of GAUC and nDCG@5.
- Data split: train `20220408–20220421`, validation `20220422–20220428`, test `20220429–20220508`, as implemented by `starter/data.py`.
- Reference baseline: FM validation primary score `0.6016`.
- The canonical task evidence is the protected seven-file `starter/` kit. Agents must not replace the date split with random, user, or row splits.

## Hard safety rules

1. Never modify files under `starter/` during ordinary work. Canonical restoration is allowed only with explicit human authorization, a matching record in `governance/manual_interventions.jsonl`, exact source/hash verification, and A-reviewed protected-hash updates.
2. `starter/evaluate.py`, `starter/data.py`, `starter/submit.py`, and `starter/baseline_scores.json` are protected by SHA-256 pins in both `governance/protected_files.json` and `protected_manifest.json`. Preserve `.gitattributes`; protected text uses canonical LF across platforms.
3. Never read, score, tune on, select from, or report test labels or test metrics during an ordinary experiment. Test evaluation requires `tools/final_approval.py` to verify a frozen full commit SHA, a clean worktree, matching protected hashes, and explicit recorded human approval through the release-only final-approval workflow.
4. Validation is the only split used for feature, model, threshold, or hyperparameter decisions.
5. Every artifact and reported metric must bind to the complete 40-character Git commit SHA that produced it. The canonical field is `commit_sha`; `base_commit`, abbreviated SHAs, branch names, and tags are forbidden substitutes.
6. The canonical experiment identifier field is `experiment_id`; `exp_id` is not accepted.
7. Do not commit data, credentials, predictions, checkpoints, virtual environments, or generated artifacts.
8. Do not weaken prediction/audit checks merely to make tests pass, and never claim PASS when required evidence is absent.
9. Run `python3 -m unittest discover -s tests -v` before requesting review.

## Roles and write authority

- A — controller and integrator. Owns `AGENTS.md`, `governance/`, `.github/`, `.codex/`, approved-config promotion, and repository integration. A may review all areas but may not silently rewrite another role's result.
- B — validation and contracts. Owns `tests/` and validator implementation under `scripts/`; confirms task semantics, date split, baseline reproduction, prediction schema, and CI behavior. B does not propose research changes.
- C — feature proposals. Writes feature proposals and candidate feature configs only; no model-family changes, protected-file edits, or approval/promotion.
- D — model proposals. Writes model proposals and candidate model configs only; no feature-definition changes, protected-file edits, or approval/promotion.
- E — execution and reproducibility. Runs approved experiments and writes manifests, metrics, and run reports; does not change evaluation logic or approve its own run.

Model, training, and feature work belongs outside E's evaluation tooling.

Agents write only in their owned area unless A records an exception in `governance/manual_interventions.jsonl`. All proposals enter through `coordination/inbox/<ROLE>/` and retain author, `experiment_id`, full `commit_sha`, and decision state.

## Git rules

- Work on role branches; do not commit directly to `main`.
- `main` accepts changes only through reviewed pull requests with required status checks. Repository administrators must enable GitHub branch protection/rulesets; workflow files alone cannot prevent an already accepted direct push.
- Keep commits scoped and reproducible. Never force-push shared branches or rewrite shared history without a recorded human instruction.
- Pull requests changing protected hashes require human approval and a matching manual-intervention record.
- Candidate configs live in `configs/candidates/`. Only A may promote a reviewed candidate to `configs/approved/`.

## Improvement and escalation

An improvement must exceed the current approved primary score by `epsilon` from `governance/policy.json`. After the configured number of consecutive non-improving completed trials, stop automatic iteration and request a human decision. One automatic repair attempt is allowed for an infrastructure-only failure; scientific or policy failures are never auto-repaired.

Escalate to a human immediately when a protected file is missing or changed, test access is requested or detected, results are irreproducible, the commit SHA is missing or dirty, role permissions conflict, data leakage is suspected, a run exceeds its time limit, baseline/task evidence conflicts with this contract, or a change would require force-push/history rewrite. Record the decision in `governance/manual_interventions.jsonl` before resuming.
