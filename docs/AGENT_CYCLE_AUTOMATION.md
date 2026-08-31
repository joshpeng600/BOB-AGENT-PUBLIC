# Agent cycle automation

`tools/run_agent_cycle.py` is the safe entry point for asynchronous Track 2
cycles. It coordinates the five existing roles; it does not collapse their
write authority or independence into one role.

## What it automates

1. Reads `coordination/current_state.json` and
   `coordination/current_experiment.json`, then selects only the legal next
   receiver. A terminal `exp_009` plus `--experiment exp_010` routes first to A.
2. Invokes the local Codex CLI in a dedicated role worktree and saves the Codex
   session identifier. A stopped session can be continued after quota recovery
   with `--resume-session`.
3. Monitors a pull request and the four required GitHub checks. Automatic merge
   is opt-in, and protected paths always stop it for human review.
4. Keeps small evidence in the role PR. For large predictions, checkpoints, or
   other artifacts it produces a byte-level SHA-256 manifest and requires a
   private manual transfer.
5. Generates ignored runtime files containing cycle status, the experiment
   comparison table, and a compact demo summary.
6. Runs a bounded multi-experiment campaign when A has recorded an explicit
   valid-only authorization. Every role remains a separate Codex invocation,
   worktree, commit, PR, and CI decision.

Runtime files are written below `artifacts/agent_cycle/<experiment>/`, which is
already excluded from Git.

## Safe defaults

The shortest command is read-only:

```powershell
python tools/run_agent_cycle.py --experiment exp_010
```

It shows the current legal receiver and creates the ignored status/demo files.
It does not invoke Codex or change GitHub.

To let the currently legal role perform one step:

```powershell
python tools/run_agent_cycle.py --experiment exp_010 --action step --execute
```

For five computers with different token-reset times, each member can run the
same command with their role. A non-matching worker exits safely and says which
role is currently needed:

```powershell
python tools/run_agent_cycle.py --experiment exp_010 --action step --execute --worker-role C
```

The process does not assume that A, B, C, D, and E are online together. Invoke
it again after the previous role's PR is merged and the local clone has the
latest main.

## Bounded continuous campaign

The continuous entry point is:

```powershell
python tools/run_agent_cycle.py --experiment exp_010 --action run --max-iterations 3
```

`--max-iterations` counts newly completed experiments, not individual role
calls. The runner also enforces A's role-step ceiling; an operator may request a
smaller ceiling with `--max-role-steps`, but cannot widen it.

The command executes only from a clean `main` checkout and only after A has
committed a `bounded_campaign_authorization` in
`coordination/current_state.json`. The required shape is:

```json
{
  "bounded_campaign_authorization": {
    "status": "ALLOWED",
    "experiment_ids": ["exp_010", "exp_011", "exp_012"],
    "max_completed_experiments": 3,
    "max_role_steps": 30,
    "data_mode": "train_valid_only",
    "automatic_public_valid": true,
    "test_access": false,
    "final_approval_allowed": false
  }
}
```

The runner validates this record but never creates, edits, or extends it. For
every role step it requires a clean full commit SHA, a PR whose head is exactly
that SHA, changed paths inside that role's AGENTS.md ownership, all four required
checks, a conflict-free merge, and a fresh fast-forward of local `main`.
Reusing a role in the same experiment is safe only when its clean worktree can
fast-forward to the newly merged `origin/main`; divergence stops the campaign
without rebase, reset, or force-push.

Continuous mode queues composite C/D receivers and automatically sends completed
non-A evidence through A for canonical state integration. On one host, B's private
artifacts remain outside Git and are passed to E through a byte-reverified read-only
manifest. It stops and records `campaign_state.json` when a role waits, blocks, or
fails; a PR is missing, conflicting, unsafe, or fails CI; artifact bytes change; a
cross-host transfer is required; A fails to advance state; authorization changes; or
a role-step/consecutive-no-improvement limit is reached. Repeat the same command to
resume after an external failure is resolved.

## PR and CI monitoring

Check a PR without merging it:

```powershell
python tools/run_agent_cycle.py --experiment exp_010 --action watch-pr --pr 54
```

Wait for the exact four checks and merge an ordinary safe PR:

```powershell
python tools/run_agent_cycle.py --experiment exp_010 --action watch-pr --pr 54 --timeout-seconds 1800 --auto-merge
```

The merge is refused if the PR touches `starter/`, `.gitattributes`,
`protected_manifest.json`, or `governance/protected_files.json`, is conflicted,
or lacks a required successful check.

Add `--wait-pr --auto-merge` to an executed role step to monitor the PR returned
by that role.

## Formal validation gate

For a one-step invocation, real validation remains double locked. The
repository must record `REAL_VALID_RUN_ALLOWED.status=ALLOWED`, the next
receiver must be B, and the operator must add the explicit flag:

```powershell
python tools/run_agent_cycle.py --experiment exp_010 --action step --execute --worker-role B --allow-real-valid
```

Without all three conditions the role prompt forbids real-data training and
formal validation metrics.

In continuous mode the explicit operator flag is replaced by the A-recorded
bounded campaign authorization above. B receives public-validation permission
only when both that campaign record and the current experiment's
`REAL_VALID_RUN_ALLOWED.status=ALLOWED` are present. Other roles never receive
training permission. No ordinary or continuous cycle command authorizes hidden-test
access or final approval. Local hidden-test scoring does not exist; release-only
approval can only freeze a label-free organizer-scored submission, and release paths
cannot be auto-merged by this coordinator.

## Large artifact handoff

During a same-host continuous campaign this handoff is automatic: the manifest
records every byte hash, the runner re-verifies it immediately before dispatching E,
and E receives read-only paths in its prompt. For different computers, the runner
stops truthfully until the exact hashed package is privately transferred.

Create a transfer manifest without copying or modifying the artifacts:

```powershell
python tools/run_agent_cycle.py --experiment exp_010 --action handoff --recipient E `
  --artifact-path C:\private\exp010_baseline `
  --artifact-path C:\private\exp010_candidate
```

Send the listed folders privately by shared drive, encrypted storage, removable
media, or a messenger file transfer. Send the generated handoff manifest with
them so the receiver can verify every file. Do not commit either the files or
the manifest's source packages.

## Quota recovery

Each role run writes `events.jsonl`, `last_message.json`, and either
`result.json` or `stopped_manifest.json` below its ignored runtime directory.
If the stopped manifest contains a Codex session identifier, resume it after
quota recovery:

```powershell
python tools/run_agent_cycle.py --experiment exp_010 --action step --execute `
  --worker-role D --resume-session <session-id>
```

Partially produced work is never represented as a completed run. Scientific,
contract, leakage, protected-file, dirty-worktree, and test-access failures are
reported as blocked and are not auto-repaired.
