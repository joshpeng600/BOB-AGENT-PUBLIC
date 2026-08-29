# Required `main` ruleset

Repository administrators must configure a GitHub branch ruleset for `main` with:

- require a pull request before merging;
- require at least one approval and dismiss stale approvals;
- require code-owner review for governance and protected-file changes if CODEOWNERS is later configured;
- require `protected-files / verify-protected-files`, `unit-tests / tests`, `prediction-contract / prediction-contract`, and `repository-contracts / contracts`;
- require branches to be up to date before merging;
- block force pushes, deletion, and bypasses (including administrators where supported).

The repository files describe and test this policy, but GitHub branch protection is the enforcement point that prevents direct pushes. A repository administrator must enable it before bootstrap can be declared complete.
