# Submission checklist

This checklist separates repository-verifiable work from human-controlled release
actions. Do not mark an item complete without evidence from the final merged commit.

## Repository package

- [x] README explains the product, five-agent architecture, quick start, verified
  trajectory, safety boundaries, limitations, and roadmap.
- [x] Architecture, demo, and Devpost draft documents exist.
- [ ] Packaging PR #56 is merged; confirm its four required Actions checks in the
  signed-in GitHub UI before submission.
- [x] Clean-clone quick start verified on a machine/environment that does not contain
  the development dataset.
- [ ] Final merged SHA recorded in the Devpost notes.

## Verification

- [ ] `python -m pytest -q` passes on the final merged commit.
- [ ] `python -m unittest discover -s tests -v` passes on the final merged commit.
- [ ] `python scripts/check_repository_contracts.py` passes.
- [ ] `python scripts/check_protected_files.py` passes.
- [ ] `python scripts/check_prediction_contract.py` passes.
- [ ] `python tools/run_agent_cycle.py --experiment exp_003 --action report` shows A
  as next receiver, exp_001 KEEP, exp_002 REJECT, and `test_access=false` without
  creating an experiment or formal metrics.
- [ ] `git diff -- starter/` is empty.
- [ ] Final tracked worktree is clean.

## Public-release safety

- [x] No tracked datasets, predictions, checkpoints, run artifacts, `.env` files,
  credentials, access tokens, or private keys.
- [x] Full Git history scanned for secret patterns; findings reviewed without printing
  secret values into logs.
- [x] Full Git history scanned for unexpectedly large blobs or committed artifacts.
- [x] `.gitignore` covers data, artifacts, checkpoints, predictions, environments, and
  credential files.
- [ ] PR #51 status manually confirmed. If it remains open and is superseded by the
  merged exp_002 decision and PR #54, close it with a clear superseded note.
- [x] Human-approved MIT License added in PR #58.
- [x] Repository owner explicitly authorized visibility change in the manual release
  record merged with PR #58.
- [ ] Public repository is accessible in a signed-out/private browser window.

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
  bounded campaign with fail-closed stop/resume; do not claim absolute unattended
  execution, unrestricted automatic public-valid, repository publication, or external
  submission.
- [ ] Submit before `2026-09-01 12:00 SGT`, leaving time for link verification.

## Non-negotiable boundary

- [x] Ordinary agent workflow reports `test_access=false`.
- [ ] Final submission is checked for format and hashes only, then sent to the external
  hidden-test evaluator without local hidden labels or metrics being exposed to agents.

## Human-only remaining actions

1. Confirm PR #51 is closed or clearly marked superseded.
2. Merge the final submission-readiness PR after all four checks pass.
3. Change the repository visibility to public, then verify the repository while signed
   out.
4. Record the final merged SHA in the Devpost notes.
5. Record and upload the public three-minute video, replace `[YOUTUBE_URL]`, and verify
   playback while signed out.
6. Submit the Devpost entry and, only through the external evaluator, the final hidden-
   test package.

## Release-candidate evidence

The `release/final-submission-readiness` candidate was checked before its final PR:

- pytest: 155 passed, 56 subtests passed;
- unittest: 155 of 155 passed;
- repository contracts: PASS, 45 JSON files plus JSONL/TOML;
- protected files: PASS, all seven canonical files;
- prediction contract: PASS, 9 of 9;
- clean clone without `data/dev`: unittest 155 of 155 and read-only report PASS;
- history secret-pattern findings: 0;
- unsafe tracked data/artifact/credential paths: 0;
- Git blobs at least 5 MB: 0;
- `starter/` diff: empty;
- report result: exp_001 KEEP, exp_002 REJECT, champion exp_001, next receiver A,
  gate CONSUMED_BLOCKED, `test_access=false`.

The unchecked Verification items above deliberately require the same commands to be
repeated on the final merged `main` SHA.
