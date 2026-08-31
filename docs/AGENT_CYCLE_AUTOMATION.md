# Agent cycle automation

`tools/run_agent_cycle.py` is the safe entry point for asynchronous Track 2
cycles. It coordinates the five existing roles; it does not collapse their
write authority or independence into one role.

## What it automates

1. Reads `coordination/current_state.json` and
   `coordination/current_experiment.json`, then selects only the legal next
   receiver. A terminal `exp_002` plus `--experiment exp_003` routes first to A.
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

Runtime files are written below `artifacts/agent_cycle/<experiment>/`, which is
already excluded from Git.

## Safe defaults

The shortest command is read-only:

```powershell
python tools/run_agent_cycle.py --experiment exp_003
```

It shows the current legal receiver and creates the ignored status/demo files.
It does not invoke Codex or change GitHub.

To let the currently legal role perform one step:

```powershell
python tools/run_agent_cycle.py --experiment exp_003 --action step --execute
```

For five computers with different token-reset times, each member can run the
same command with their role. A non-matching worker exits safely and says which
role is currently needed:

```powershell
python tools/run_agent_cycle.py --experiment exp_003 --action step --execute --worker-role C
```

The process does not assume that A, B, C, D, and E are online together. Invoke
it again after the previous role's PR is merged and the local clone has the
latest main.

## PR and CI monitoring

Check a PR without merging it:

```powershell
python tools/run_agent_cycle.py --experiment exp_003 --action watch-pr --pr 54
```

Wait for the exact four checks and merge an ordinary safe PR:

```powershell
python tools/run_agent_cycle.py --experiment exp_003 --action watch-pr --pr 54 --timeout-seconds 1800 --auto-merge
```

The merge is refused if the PR touches `starter/`, `.gitattributes`,
`protected_manifest.json`, or `governance/protected_files.json`, is conflicted,
or lacks a required successful check.

Add `--wait-pr --auto-merge` to an executed role step to monitor the PR returned
by that role.

## Formal validation gate

Real validation remains double locked. The repository must record
`REAL_VALID_RUN_ALLOWED.status=ALLOWED`, the next receiver must be B, and the
operator must add the explicit flag:

```powershell
python tools/run_agent_cycle.py --experiment exp_003 --action step --execute --worker-role B --allow-real-valid
```

Without all three conditions the role prompt forbids real-data training and
formal validation metrics. No ordinary cycle command authorizes test access or
final approval.

## Large artifact handoff

Create a transfer manifest without copying or modifying the artifacts:

```powershell
python tools/run_agent_cycle.py --experiment exp_003 --action handoff --recipient E `
  --artifact-path C:\private\exp003_baseline `
  --artifact-path C:\private\exp003_candidate
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
python tools/run_agent_cycle.py --experiment exp_003 --action step --execute `
  --worker-role D --resume-session <session-id>
```

Partially produced work is never represented as a completed run. Scientific,
contract, leakage, protected-file, dirty-worktree, and test-access failures are
reported as blocked and are not auto-repaired.
