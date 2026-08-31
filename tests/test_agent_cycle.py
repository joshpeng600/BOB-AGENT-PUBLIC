from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.run_agent_cycle import (
    CycleError,
    REQUIRED_CHECKS,
    artifact_inventory,
    assess_pr,
    build_codex_command,
    build_role_prompt,
    create_handoff_manifest,
    determine_receivers,
    experiment_comparison,
    generate_reports,
    is_terminal_state,
    next_experiment_id,
    normalize_receivers,
    parse_pr_number,
    select_target_experiment,
    validate_agent_result,
)


def safe_result(**overrides):
    value = {
        "status": "COMPLETED",
        "role": "B",
        "phase": "PACKAGE_AUDIT",
        "experiment_id": "exp_003",
        "summary": "approved role step completed",
        "commit_sha": "a" * 40,
        "pr_url": "https://github.com/example/repo/pull/54",
        "small_evidence_paths": ["coordination/inbox/B/result.md"],
        "large_artifact_paths": [],
        "next_receiver": "E",
        "formal_metrics_produced": False,
        "pr_25_evidence_used": False,
        "final_approval_created": False,
        "test_access": False,
    }
    value.update(overrides)
    return value


def successful_pr(files=None):
    checks = []
    for full_name in sorted(REQUIRED_CHECKS):
        workflow, name = full_name.split(" / ", 1)
        checks.append(
            {"workflowName": workflow, "name": name, "conclusion": "SUCCESS"}
        )
    return {
        "state": "OPEN",
        "mergeable": "MERGEABLE",
        "files": [{"path": path} for path in (files or ["tools/example.py"])],
        "statusCheckRollup": checks,
    }


class ReceiverTests(unittest.TestCase):
    def test_normalizes_composite_receivers(self):
        self.assertEqual(normalize_receivers("C_AND_D"), ["C", "D"])
        self.assertEqual(normalize_receivers("B/E"), ["B", "E"])
        self.assertEqual(normalize_receivers(["C", "D", "C"]), ["C", "D"])

    def test_rejects_unknown_receiver(self):
        with self.assertRaises(CycleError):
            normalize_receivers("A_AND_F")

    def test_terminal_state_selects_next_experiment_and_A(self):
        current = {"experiment_id": "exp_002", "status": "COMPLETED_REJECTED"}
        state = {"next_receiver": "E"}
        self.assertTrue(is_terminal_state(current))
        self.assertEqual(next_experiment_id("exp_002"), "exp_003")
        target = select_target_experiment(None, current, state)
        self.assertEqual(target, "exp_003")
        self.assertEqual(determine_receivers(target, current, state), ["A"])

    def test_active_experiment_cannot_be_skipped(self):
        current = {"experiment_id": "exp_003", "status": "IMPLEMENTING"}
        with self.assertRaises(CycleError):
            select_target_experiment("exp_004", current, {})


class ResultContractTests(unittest.TestCase):
    def test_accepts_safe_result(self):
        validate_agent_result(safe_result(), role="B", experiment_id="exp_003")

    def test_rejects_test_access(self):
        with self.assertRaisesRegex(CycleError, "test_access"):
            validate_agent_result(
                safe_result(test_access=True), role="B", experiment_id="exp_003"
            )

    def test_rejects_pr25_or_final_approval(self):
        for field in ("pr_25_evidence_used", "final_approval_created"):
            with self.subTest(field=field), self.assertRaises(CycleError):
                validate_agent_result(
                    safe_result(**{field: True}), role="B", experiment_id="exp_003"
                )

    def test_rejects_short_sha(self):
        with self.assertRaisesRegex(CycleError, "full lowercase SHA"):
            validate_agent_result(
                safe_result(commit_sha="abc123"), role="B", experiment_id="exp_003"
            )


class DispatchConstructionTests(unittest.TestCase):
    def test_codex_command_uses_reviewable_sandbox(self):
        command = build_codex_command(
            executable="codex",
            worktree=Path("worktree"),
            schema=Path("schema.json"),
            last_message=Path("last.json"),
        )
        self.assertIn("workspace-write", command)
        self.assertIn("--approve-for-me", command)
        self.assertIn("--output-schema", command)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", command)

    def test_resume_command_contains_session(self):
        command = build_codex_command(
            executable="codex",
            worktree=Path("worktree"),
            schema=Path("schema.json"),
            last_message=Path("last.json"),
            session_id="session-123",
        )
        self.assertEqual(command[1:4], ["exec", "resume", "session-123"])

    def test_prompt_keeps_formal_run_closed_without_both_conditions(self):
        prompt = build_role_prompt(
            role="B",
            experiment_id="exp_003",
            gate_status="ALLOWED",
            allow_real_valid=False,
        )
        self.assertIn("Do not run real data training", prompt)
        prompt = build_role_prompt(
            role="B",
            experiment_id="exp_003",
            gate_status="ALLOWED",
            allow_real_valid=True,
        )
        self.assertIn("explicitly permits B", prompt)


class PullRequestGateTests(unittest.TestCase):
    def test_allows_clean_pr_with_all_checks(self):
        ready, reasons = assess_pr(successful_pr())
        self.assertTrue(ready)
        self.assertEqual(reasons, [])

    def test_rejects_protected_file_change(self):
        ready, reasons = assess_pr(successful_pr(["starter/data.py"]))
        self.assertFalse(ready)
        self.assertTrue(any("protected paths" in reason for reason in reasons))

    def test_rejects_missing_check(self):
        pr = successful_pr()
        pr["statusCheckRollup"].pop()
        ready, reasons = assess_pr(pr)
        self.assertFalse(ready)
        self.assertTrue(any("MISSING" in reason for reason in reasons))

    def test_parses_pr_number(self):
        self.assertEqual(
            parse_pr_number("https://github.com/example/repo/pull/123"), 123
        )
        self.assertIsNone(parse_pr_number(None))


class ArtifactAndReportTests(unittest.TestCase):
    def test_artifact_manifest_hashes_bytes_without_modifying_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            package = root / "package"
            package.mkdir()
            artifact = package / "valid_predictions.csv"
            artifact.write_bytes(b"row_id,score\n0,0.5\n")
            before = artifact.read_bytes()
            inventory = artifact_inventory([package])
            self.assertEqual(len(inventory), 1)
            self.assertEqual(inventory[0]["relative_path"], "valid_predictions.csv")
            self.assertEqual(artifact.read_bytes(), before)

            manifest = create_handoff_manifest(
                root / "runtime",
                experiment_id="exp_003",
                recipient="E",
                artifact_paths=[package],
            )
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertTrue(payload["manual_private_transfer_required"])
            self.assertFalse(payload["git_upload_allowed"])
            self.assertFalse(payload["test_access"])

    def test_comparison_uses_decisions_only(self):
        rows = experiment_comparison(
            [
                {"record_type": "experiment_plan", "experiment_id": "exp_001"},
                {
                    "record_type": "experiment_decision",
                    "experiment_id": "exp_001",
                    "decision": "KEEP",
                    "baseline_primary": 0.60,
                    "candidate_primary": 0.61,
                    "primary_delta": 0.01,
                    "test_access": False,
                },
            ]
        )
        self.assertEqual([row["experiment_id"] for row in rows], ["exp_001"])

    def test_generates_status_comparison_and_demo_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            history = root / "coordination" / "experiment_history.jsonl"
            history.parent.mkdir(parents=True)
            history.write_text(
                json.dumps(
                    {
                        "record_type": "experiment_decision",
                        "experiment_id": "exp_002",
                        "decision": "REJECT",
                        "baseline_primary": 0.60,
                        "candidate_primary": 0.59,
                        "primary_delta": -0.01,
                        "test_access": False,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            runtime = root / "artifacts" / "agent_cycle" / "exp_003"
            report = generate_reports(
                root,
                runtime,
                target="exp_003",
                current_experiment={
                    "experiment_id": "exp_002",
                    "status": "COMPLETED_REJECTED",
                },
                current_state={
                    "next_receiver": "A",
                    "stage_gates": {
                        "REAL_VALID_RUN_ALLOWED": {"status": "CONSUMED_BLOCKED"}
                    },
                },
            )
            self.assertEqual(report["next_receivers"], ["A"])
            self.assertTrue((runtime / "cycle_state.json").exists())
            self.assertTrue((runtime / "status.md").exists())
            self.assertTrue((runtime / "demo_summary.json").exists())


if __name__ == "__main__":
    unittest.main()
