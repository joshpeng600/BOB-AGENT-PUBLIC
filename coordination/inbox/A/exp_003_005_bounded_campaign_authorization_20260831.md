# Bounded campaign authorization: exp_003 through exp_005

- Recorded by: A
- Approved against commit: `6fbd1ec2d7dcaf15852dc058946088d4fb8bf547`
- Human instruction: authorize A to avoid repeated per-round operator approval and run three autonomous Track 2 iterations.
- Authorized experiments: `exp_003`, `exp_004`, `exp_005`
- Maximum completed experiments: 3
- Maximum role dispatches: 30
- Data mode: `train_valid_only`
- Automatic public-validation gate: allowed only after A verifies every experiment-specific prerequisite
- Repeated human allow per experiment: not required
- Hidden test access: forbidden
- Final approval: forbidden

This is a bounded campaign authorization, not a standing permission. A must still
review the merged C, D, B, and E evidence and may record
`REAL_VALID_RUN_ALLOWED=ALLOWED` only when the repository gates for the active
experiment are satisfied. The campaign stops immediately if a protected-file,
data-leakage, dirty-worktree, test-access, role-ownership, timeout, or other
governance stop condition is detected. The configured consecutive-no-improvement
rule also remains binding and may stop the campaign before all three experiments
complete.

`PR25_EVIDENCE_USED=false`

`FINAL_APPROVAL_CREATED=false`

`test_access=false`
