# Submission checklist

This checklist separates repository-verifiable work from human-controlled release
actions. Do not mark an item complete without evidence from the final merged commit.

## Repository package

- [x] README explains the product, five-agent architecture, quick start, verified
  trajectory, safety boundaries, limitations, and roadmap.
- [x] Architecture, demo, and Devpost draft documents exist.
- [x] Public packaging and migration are merged through public PR #3; public PRs
  #1, #4, and #6 also passed all four required Actions checks.
- [x] Clean-clone quick start verified on a machine/environment that does not contain
  the development dataset.
- [ ] Final merged SHA recorded in the Devpost notes.

## Verification

- [x] `python -m pytest -q` passes on the final merged code commit.
- [x] `python -m unittest discover -s tests -v` passes on the final merged code commit.
- [x] `python scripts/check_repository_contracts.py` passes.
- [x] `python scripts/check_protected_files.py` passes.
- [x] `python scripts/check_prediction_contract.py` passes.
- [x] `python tools/run_agent_cycle.py --experiment exp_002 --action report` shows A
  as next receiver, exp_001 KEEP, exp_002 REJECT, and `test_access=false` without
  creating an experiment or formal metrics.
- [x] `git diff -- starter/` is empty.
- [x] Final tracked worktree is clean before this documentation-only polish.

## Public-release safety

- [x] No tracked datasets, predictions, checkpoints, run artifacts, `.env` files,
  credentials, access tokens, or private keys.
- [x] Full Git history scanned for secret patterns; findings reviewed without printing
  secret values into logs.
- [x] Full Git history scanned for unexpectedly large blobs or committed artifacts.
- [x] `.gitignore` covers data, artifacts, checkpoints, predictions, environments, and
  credential files.
- [x] Legacy private-repository PR tracking is not required for the public release;
  the public migration and verification chain is recorded in public PRs #3, #1, #4,
  and #6.
- [x] Human-approved MIT License is present on public `main`.
- [x] Repository owner explicitly authorized publication in the manual release record
  carried into public `main`.
- [x] Public repository is accessible without authentication at
  https://github.com/joshpeng600/BOB-AGENT-PUBLIC.

## Video

- [ ] Record the workflow from [DEMO.md](DEMO.md) without real data or test access.
- [ ] Video is under three minutes and terminal text is readable.
- [ ] Video distinguishes live tests/reporting from historical valid-only evidence.
- [ ] No personal paths, credentials, private artifact locations, or quarantined PR #25
  metrics are visible.
- [ ] Upload to YouTube as public and verify playback while signed out.

## Devpost

- [x] Replace `[REPOSITORY_URL]` with the canonical repository URL.
- [ ] Replace `[YOUTUBE_URL]` after the public demo video is uploaded and verified.
- [x] Review the final text for technical execution, innovation/problem insight,
  impact/relevance, feasibility/practicality, and presentation.
- [x] Describe `--action run --max-iterations 3` as an implemented, A-authorized
  bounded campaign with automatic same-host A-E handoffs and fail-closed stop/resume;
  do not claim unrestricted public-valid, cross-host artifact automation, repository
  publication, or organizer upload.
- [ ] Submit before `2026-09-01 12:00 SGT`, leaving time for link verification.

## Non-negotiable boundary

- [x] Ordinary agent workflow reports `test_access=false`.
- [x] Final submission is checked for format and hashes only, then sent to the external
  hidden-test evaluator without local hidden labels or metrics being exposed to agents.

## Human-only remaining actions

1. Record the final merged SHA in the Devpost notes after this documentation polish is
   merged.
2. Record and upload the public three-minute video, replace `[YOUTUBE_URL]`, and verify
   playback while signed out.
3. Submit the Devpost entry and, only through the external evaluator, the final hidden-
   test package.

## Final public-main evidence

Public `main` at `6fbd1ec2d7dcaf15852dc058946088d4fb8bf547` was checked before
this documentation-only polish:

- pytest: 165 passed, 70 subtests passed;
- unittest: 165 of 165 passed;
- repository contracts: PASS, 45 JSON files plus JSONL/TOML;
- protected files: PASS, all seven canonical files;
- prediction contract: PASS, 9 of 9;
- historical release-candidate clean clone without `data/dev`: unittest 155 of 155
  and read-only report PASS;
- history secret-pattern findings: 0;
- unsafe tracked data/artifact/credential paths: 0;
- Git blobs at least 5 MB: 0;
- `starter/` diff: empty;
- report result: exp_001 KEEP, exp_002 REJECT, champion exp_001, next receiver A,
  gate CONSUMED_BLOCKED, `test_access=false`.

The remaining unchecked items are human-controlled final-SHA, video, and Devpost
submission actions.
